"""Buchungsmonat → Datei (xlsx, ods, csv, pdf).

Öffentliche Schnittstelle: `export_ledger(ledger, fmt, lang) -> ExportFile`.
Excel- und LibreOffice-Dateien enthalten echte SUMME-Formeln, damit spätere
Änderungen in der Tabelle automatisch mitgerechnet werden. Ruhetage sind grau.
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
    return f"{weekday} {entry.day:%d.%m.%Y}"


def _note(entry: DayEntry, lb: dict[str, str]) -> str:
    parts = []
    if entry.closed is not None:
        parts.append(lb["sunday"] if entry.closed.kind == ClosedKind.SUNDAY else entry.closed.name)
    if entry.note:
        parts.append(entry.note)
    return " · ".join(parts)


def _title(ledger: LedgerMonth, lb: dict[str, str]) -> str:
    return f"{lb['title']} {ledger.month:02d}/{ledger.year} – {lb['region']} {ledger.region}"


def _de(value: Decimal) -> str:
    """Deutsches Zahlenformat: 1.234,50"""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --- Formate --------------------------------------------------------------------------


def _xlsx(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = ledger.period
    ws.append([_title(ledger, lb)])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([lb["date"], lb["income"], lb["expense"], lb["note"]])
    for cell in ws[2]:
        cell.font = Font(bold=True)

    grey = PatternFill("solid", fgColor=GREY)
    first = 3
    for entry in ledger.entries:
        ws.append([_day_label(entry, lb), entry.income, entry.expense, _note(entry, lb)])
        if entry.closed is not None:
            for cell in ws[ws.max_row]:
                cell.fill = grey
    last = ws.max_row

    ws.append([lb["total"], f"=SUM(B{first}:B{last})", f"=SUM(C{first}:C{last})"])
    ws.append([lb["balance"], f"=B{last + 1}-C{last + 1}"])
    for row in ws.iter_rows(min_row=last + 1):
        for cell in row:
            cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=first, min_col=2, max_col=3):
        for cell in row:
            cell.number_format = "#,##0.00 €"
    for col, width in zip("ABCD", (18, 16, 16, 34), strict=True):
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

    def text(value: str, style: Style | None = None) -> TableCell:
        cell = (
            TableCell(valuetype="string", stylename=style)
            if style
            else TableCell(valuetype="string")
        )
        cell.addElement(P(text=value))
        return cell

    def number(value: Decimal | None, style: Style | None = None) -> TableCell:
        if value is None:
            return TableCell(stylename=style) if style else TableCell()
        kwargs = {"valuetype": "float", "value": str(value)}
        cell = TableCell(stylename=style, **kwargs) if style else TableCell(**kwargs)
        cell.addElement(P(text=_de(value)))
        return cell

    def formula(expr: str, value: Decimal) -> TableCell:
        cell = TableCell(valuetype="float", value=str(value), formula=expr, stylename=bold)
        cell.addElement(P(text=_de(value)))
        return cell

    table = Table(name=ledger.period)
    for cells in (
        [text(_title(ledger, lb), bold)],
        [text(lb[k], bold) for k in ("date", "income", "expense", "note")],
    ):
        row = TableRow()
        for c in cells:
            row.addElement(c)
        table.addElement(row)

    first = 3
    for entry in ledger.entries:
        style = grey if entry.closed is not None else None
        row = TableRow()
        for cell in (
            text(_day_label(entry, lb), style),
            number(entry.income, style),
            number(entry.expense, style),
            text(_note(entry, lb), style),
        ):
            row.addElement(cell)
        table.addElement(row)
    last = first + len(ledger.entries) - 1
    t = ledger.totals

    total_row = TableRow()
    total_row.addElement(text(lb["total"], bold))
    total_row.addElement(formula(f"of:=SUM([.B{first}:.B{last}])", t.income))
    total_row.addElement(formula(f"of:=SUM([.C{first}:.C{last}])", t.expense))
    table.addElement(total_row)
    balance_row = TableRow()
    balance_row.addElement(text(lb["balance"], bold))
    balance_row.addElement(formula(f"of:=[.B{last + 1}]-[.C{last + 1}]", t.balance))
    table.addElement(balance_row)

    doc.spreadsheet.addElement(table)
    buf = io.BytesIO()
    doc.write(buf)
    return buf.getvalue()


def _csv(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    """Semikolon + Dezimalkomma + BOM: öffnet sich in deutschem Excel/LibreOffice korrekt."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow([lb["date"], lb["income"], lb["expense"], lb["note"]])
    for e in ledger.entries:
        w.writerow(
            [
                f"{e.day:%d.%m.%Y}",
                _de(e.income) if e.income is not None else "",
                _de(e.expense) if e.expense is not None else "",
                _note(e, lb),
            ]
        )
    t = ledger.totals
    w.writerow([lb["total"], _de(t.income), _de(t.expense), ""])
    w.writerow([lb["balance"], _de(t.balance), "", ""])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _pdf(ledger: LedgerMonth, lb: dict[str, str]) -> bytes:
    from fpdf import FPDF

    from buchfuehrung.export.fonts import unicode_font_path

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
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

    pdf.set_font(family, "B", 14)
    pdf.cell(0, 9, safe(_title(ledger, lb)), new_x="LMARGIN", new_y="NEXT")
    widths = (38, 32, 32, 88)
    pdf.set_font(family, "B", 10)
    for w, key in zip(widths, ("date", "income", "expense", "note"), strict=True):
        pdf.cell(w, 7, safe(lb[key]), border=1)
    pdf.ln()
    pdf.set_font(family, "", 10)
    for e in ledger.entries:
        fill = e.closed is not None
        pdf.set_fill_color(217, 217, 217)
        cells = (
            _day_label(e, lb),
            _de(e.income) if e.income is not None else "",
            _de(e.expense) if e.expense is not None else "",
            _note(e, lb),
        )
        for i, (w, value) in enumerate(zip(widths, cells, strict=True)):
            pdf.cell(w, 6.5, safe(value), border=1, fill=fill, align="R" if i in (1, 2) else "L")
        pdf.ln()
    t = ledger.totals
    pdf.set_font(family, "B", 10)
    pdf.cell(widths[0], 7, safe(lb["total"]), border=1)
    pdf.cell(widths[1], 7, _de(t.income), border=1, align="R")
    pdf.cell(widths[2], 7, _de(t.expense), border=1, align="R")
    pdf.ln()
    pdf.cell(widths[0] + widths[1] + widths[2], 7, f"{safe(lb['balance'])}: {_de(t.balance)}")
    return bytes(pdf.output())
