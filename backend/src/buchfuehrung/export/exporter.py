"""Buchungsmonat → Datei (xlsx, ods, csv, pdf).

Öffentliche Schnittstelle: `export_ledger(ledger, fmt, lang) -> ExportFile`.
Spalten: Datum | Einnahmen | Ausgaben | Saldo | Grund. Über den Tagen steht
eine Zeile mit dem Anfangssaldo (bzw. Übertrag). Excel- und LibreOffice-Dateien
enthalten echte Formeln für Saldo und Summen, damit spätere Änderungen in der
Tabelle mitgerechnet werden. Ruhetage sind grau.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from buchfuehrung.domain.ledger import ClosedKind, DayEntry, LedgerMonth
from buchfuehrung.export.labels import Lang, labels

GREY = "D9D9D9"
HEADER_KEYS = ("date", "income", "expense", "balance", "reason")

# Zeilenaufbau der Tabellen (1-basiert, wie in Excel)
TITLE_ROW, HEADER_ROW, OPENING_ROW, FIRST_DAY_ROW = 1, 2, 3, 4


class ExportFormat(StrEnum):
    XLSX = "xlsx"
    ODS = "ods"
    CSV = "csv"
    PDF = "pdf"


_MEDIA_TYPES = {
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.ODS: "application/vnd.oasis.opendocument.spreadsheet",
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.PDF: "application/pdf",
}


@dataclass(frozen=True)
class ExportFile:
    filename: str
    media_type: str
    content: bytes


def export_ledger(ledger: LedgerMonth, fmt: ExportFormat, lang: Lang = "de") -> ExportFile:
    writer = {
        ExportFormat.XLSX: _xlsx,
        ExportFormat.ODS: _ods,
        ExportFormat.CSV: _csv,
        ExportFormat.PDF: _pdf,
    }[fmt]
    content = writer(ledger, labels(lang))
    return ExportFile(
        filename=f"buchfuehrung_{ledger.period}.{fmt.value}",
        media_type=_MEDIA_TYPES[fmt],
        content=content,
    )


# --- gemeinsame Helfer ------------------------------------------------------------------


def _day_label(entry: DayEntry, lb: dict[str, str]) -> str:
    weekday = lb["weekdays"].split(",")[entry.day.weekday()]
    label = f"{weekday} {entry.day:%d.%m.%Y}"
    if entry.closed is not None and entry.closed.kind == ClosedKind.HOLIDAY:
        label += f" · {entry.closed.name}"
    return label


def _opening_label(ledger: LedgerMonth, lb: dict[str, str]) -> str:
    carry = ledger.carry_over
    if ledger.opening_balance is None and carry is not None:
        return lb["carry_over"].format(period=f"{carry.month:02d}/{carry.year}")
    return lb["opening"]


def _title(ledger: LedgerMonth, lb: dict[str, str]) -> str:
    return f"{lb['title']} {ledger.month:02d}/{ledger.year} – {lb['region']} {ledger.region}"


def _de(value: Decimal) -> str:
    """Deutsches Zahlenformat: 1.234,50 (negativ mit Minus)."""
    text = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{text}" if value < 0 else text


def _de_or_empty(value: Decimal | None) -> str:
    return _de(value) if value is not None else ""


# --- Formate --------------------------------------------------------------------------


def _xlsx(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = ledger.period
    bold = Font(bold=True)
    ws.append([_title(ledger, lb)])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([lb[k] for k in HEADER_KEYS])
    ws.append([_opening_label(ledger, lb), None, None, ledger.totals.opening])
    for row in ws.iter_rows(min_row=HEADER_ROW, max_row=OPENING_ROW):
        for cell in row:
            cell.font = bold

    grey = PatternFill("solid", fgColor=GREY)
    for entry in ledger.entries:
        r = ws.max_row + 1
        ws.append(
            [
                _day_label(entry, lb),
                entry.income,
                entry.expense,
                f"=D{r - 1}+B{r}-C{r}",
                entry.reason or None,
            ]
        )
        if entry.closed is not None:
            for cell in ws[r]:
                cell.fill = grey
    last = ws.max_row

    total = last + 1
    ws.append(
        [
            lb["total"],
            f"=SUM(B{FIRST_DAY_ROW}:B{last})",
            f"=SUM(C{FIRST_DAY_ROW}:C{last})",
            f"=D{last}",
        ]
    )
    ws.append([lb["result"], f"=B{total}-C{total}"])
    for row in ws.iter_rows(min_row=total):
        for cell in row:
            cell.font = bold
    for row in ws.iter_rows(min_row=OPENING_ROW, min_col=2, max_col=4):
        for cell in row:
            cell.number_format = "#,##0.00 €;-#,##0.00 €"
    for col, width in zip("ABCDE", (30, 16, 16, 16, 40), strict=True):
        ws.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _ods(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TableCellProperties, TextProperties
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    grey = Style(name="closed", family="table-cell")
    grey.addElement(TableCellProperties(backgroundcolor=f"#{GREY}"))
    bold = Style(name="bold", family="table-cell")
    bold.addElement(TextProperties(fontweight="bold"))
    doc.automaticstyles.addElement(grey)
    doc.automaticstyles.addElement(bold)

    def cell(
        *,
        text: str | None = None,
        value: Decimal | None = None,
        formula: str | None = None,
        style: Style | None = None,
    ) -> TableCell:
        kwargs: dict[str, object] = {}
        if style is not None:
            kwargs["stylename"] = style
        if value is not None:
            kwargs.update(valuetype="float", value=str(value))
        elif text:
            kwargs["valuetype"] = "string"
        if formula is not None:
            kwargs["formula"] = formula
        c = TableCell(**kwargs)
        shown = _de(value) if value is not None else text
        if shown:
            c.addElement(P(text=shown))
        return c

    def add_row(table: Table, cells: list[TableCell]) -> None:
        row = TableRow()
        for c in cells:
            row.addElement(c)
        table.addElement(row)

    t = ledger.totals
    table = Table(name=ledger.period)
    add_row(table, [cell(text=_title(ledger, lb), style=bold)])
    add_row(table, [cell(text=lb[k], style=bold) for k in HEADER_KEYS])
    add_row(
        table,
        [
            cell(text=_opening_label(ledger, lb), style=bold),
            cell(),
            cell(),
            cell(value=t.opening, style=bold),
        ],
    )

    for i, (entry, balance) in enumerate(
        zip(ledger.entries, ledger.running_balances(), strict=True)
    ):
        r = FIRST_DAY_ROW + i
        style = grey if entry.closed is not None else None
        add_row(
            table,
            [
                cell(text=_day_label(entry, lb), style=style),
                cell(value=entry.income, style=style),
                cell(value=entry.expense, style=style),
                cell(value=balance, formula=f"of:=[.D{r - 1}]+[.B{r}]-[.C{r}]", style=style),
                cell(text=entry.reason, style=style),
            ],
        )
    last = FIRST_DAY_ROW + len(ledger.entries) - 1
    total = last + 1

    add_row(
        table,
        [
            cell(text=lb["total"], style=bold),
            cell(value=t.income, formula=f"of:=SUM([.B{FIRST_DAY_ROW}:.B{last}])", style=bold),
            cell(value=t.expense, formula=f"of:=SUM([.C{FIRST_DAY_ROW}:.C{last}])", style=bold),
            cell(value=t.closing, formula=f"of:=[.D{last}]", style=bold),
        ],
    )
    add_row(
        table,
        [
            cell(text=lb["result"], style=bold),
            cell(value=t.result, formula=f"of:=[.B{total}]-[.C{total}]", style=bold),
        ],
    )

    doc.spreadsheet.addElement(table)
    buf = io.BytesIO()
    doc.write(buf)
    return buf.getvalue()


def _csv(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    """Semikolon + Dezimalkomma + BOM: öffnet sich in deutschem Excel/LibreOffice korrekt."""
    t = ledger.totals
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow([lb[k] for k in HEADER_KEYS])
    w.writerow([_opening_label(ledger, lb), "", "", _de(t.opening), ""])
    for e, balance in zip(ledger.entries, ledger.running_balances(), strict=True):
        w.writerow(
            [
                f"{e.day:%d.%m.%Y}",
                _de_or_empty(e.income),
                _de_or_empty(e.expense),
                _de(balance),
                e.reason,
            ]
        )
    w.writerow([lb["total"], _de(t.income), _de(t.expense), _de(t.closing), ""])
    w.writerow([lb["result"], _de(t.result), "", "", ""])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _pdf(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    from fpdf import FPDF

    from buchfuehrung.export.fonts import unicode_font_path

    pdf = FPDF(format="A4", orientation="landscape")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    font_path = unicode_font_path()
    if font_path:
        pdf.add_font("body", "", font_path)
        pdf.add_font("body", "B", font_path)
        family = "body"
    else:  # Fallback ohne Unicode-Schrift: vietnamesische Zeichen gehen verloren
        family = "helvetica"

    def safe(s: str) -> str:
        return s if font_path else s.encode("latin-1", "replace").decode("latin-1")

    widths = (62, 34, 34, 36, 111)
    t = ledger.totals

    def row(values: tuple[str, ...], *, height: float = 6, fill: bool = False) -> None:
        for i, (w, value) in enumerate(zip(widths, values, strict=True)):
            align = "R" if i in (1, 2, 3) else "L"
            pdf.cell(w, height, safe(value), border=1, fill=fill, align=align)
        pdf.ln()

    pdf.set_font(family, "B", 14)
    pdf.cell(0, 9, safe(_title(ledger, lb)), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "B", 10)
    row(tuple(lb[k] for k in HEADER_KEYS), height=7)
    row((_opening_label(ledger, lb), "", "", _de(t.opening), ""))
    pdf.set_font(family, "", 10)
    pdf.set_fill_color(217, 217, 217)
    for e, balance in zip(ledger.entries, ledger.running_balances(), strict=True):
        row(
            (
                _day_label(e, lb),
                _de_or_empty(e.income),
                _de_or_empty(e.expense),
                _de(balance),
                e.reason,
            ),
            fill=e.closed is not None,
        )
    pdf.set_font(family, "B", 10)
    row((lb["total"], _de(t.income), _de(t.expense), _de(t.closing), ""), height=7)
    row((lb["result"], _de(t.result), "", "", ""), height=7)
    return bytes(pdf.output())
