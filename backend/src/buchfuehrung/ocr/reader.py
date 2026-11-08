"""Foto → Entwurf eines Buchungsmonats plus Prüfdaten.

Öffentliche Schnittstelle: `read_photo(image, engine, region, fallback)`.
Intern: Textboxen zu Zeilen gruppieren, Spalten über die Kopfzeile zuordnen,
Beträge und Grund lesen, Monat/Jahr erkennen.

Was auf dem Foto zusätzlich steht – Anfangssaldo, Saldo pro Tag, Summenzeile – wird
NICHT übernommen (Salden werden immer berechnet), sondern als `PhotoChecks`
zurückgegeben. Damit prüft die App live, ob die gelesenen Zahlen aufgehen, und fragt
den Nutzer bei Abweichungen. Verdächtige Zellen (durchgestrichen, mehrere Zahlen,
schlecht lesbar) werden ebenfalls gemeldet. Alles bleibt ein Vorschlag.
"""

from __future__ import annotations

import calendar as _cal
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field

from buchfuehrung.domain.factory import blank_month
from buchfuehrung.domain.ledger import LedgerMonth
from buchfuehrung.ocr.engine import OcrEngine, TextBox
from buchfuehrung.ocr.parsing import (
    BALANCE_WORDS,
    DATE_WORDS,
    EXPENSE_WORDS,
    INCOME_WORDS,
    OPENING_WORDS,
    TOTAL_WORDS,
    find_period,
    matches_any,
    parse_amount,
    parse_day,
)
from buchfuehrung.ocr.strike import mark_struck

# Unter dieser Sicherheit des Modells gilt eine Zahl als „schlecht lesbar“
UNSURE_BELOW = 0.8

AmountField = Literal["income", "expense"]
SuspectReason = Literal["struck", "several", "unsure"]


class Hint(BaseModel):
    """Hinweis an den Nutzer. `code` wird in der App übersetzt."""

    code: str
    params: dict[str, str] = Field(default_factory=dict)


class SuspectCell(BaseModel):
    """Eine Zelle, bei der der Nutzer nachsehen soll."""

    day: int
    field: AmountField
    reason: SuspectReason
    read: list[Decimal]  # alle Zahlen in der Zelle, von links nach rechts
    struck: list[Decimal] = Field(default_factory=list)  # davon durchgestrichen


class PhotoChecks(BaseModel):
    """Was auf dem Foto zum Gegenprüfen steht (nicht übernommen, nur verglichen)."""

    opening: Decimal | None = None  # Anfangssaldo / Übertrag
    balances: dict[int, Decimal] = Field(default_factory=dict)  # Saldo-Spalte je Tag
    total_income: Decimal | None = None
    total_expense: Decimal | None = None
    closing: Decimal | None = None  # Saldo in der Summenzeile
    suspects: list[SuspectCell] = Field(default_factory=list)


class PhotoReading(BaseModel):
    ledger: LedgerMonth
    hints: list[Hint]
    recognized_days: int
    checks: PhotoChecks = Field(default_factory=PhotoChecks)


def read_photo(image: bytes, engine: OcrEngine, region: str, fallback: date) -> PhotoReading:
    boxes = [b for b in engine.recognize(image) if b.text.strip()]
    return read_boxes(mark_struck(image, boxes), region, fallback)


def read_boxes(boxes: list[TextBox], region: str, fallback: date) -> PhotoReading:
    hints: list[Hint] = []
    checks = PhotoChecks()
    rows = _group_rows(boxes)
    columns = _find_columns(rows)

    values: dict[int, tuple[Decimal | None, Decimal | None]] = {}
    reasons: dict[int, str] = {}
    suspects: dict[int, list[SuspectCell]] = {}
    row_dates: list[tuple[int | None, int | None]] = []

    for row in rows:
        if not values and any(matches_any(b.text, OPENING_WORDS) for b in row):
            checks.opening = _read_cells(row, columns).single_amount()
            continue
        if any(matches_any(b.text, TOTAL_WORDS) for b in row):
            cells = _read_cells(row, columns)
            checks.total_income, checks.total_expense = cells.amounts
            checks.closing = cells.balance
            continue
        parsed_day = parse_day(row[0].text)
        if parsed_day is None:
            continue
        day, mo, yr = parsed_day
        cells = _read_cells(row[1:], columns)
        income, expense = cells.amounts
        if income is None and expense is None and not cells.reason and not cells.suspects:
            continue
        if day in values:
            hints.append(Hint(code="duplicate_day", params={"day": str(day)}))
        values[day] = (income, expense)
        if cells.reason:
            reasons[day] = cells.reason
        if cells.balance is not None:
            checks.balances[day] = cells.balance
        suspects[day] = [s.model_copy(update={"day": day}) for s in cells.suspects]
        row_dates.append((mo, yr))

    month, year = _decide_period(boxes, row_dates, fallback, hints)
    last_day = _cal.monthrange(year, month)[1]
    for day in [d for d in values if d > last_day]:
        hints.append(Hint(code="day_out_of_month", params={"day": str(day)}))
        del values[day]
        reasons.pop(day, None)
        suspects.pop(day, None)
        checks.balances.pop(day, None)
    checks.suspects = [s for day in sorted(suspects) for s in suspects[day]]

    if not values:
        hints.append(Hint(code="no_rows_found"))
    if columns is None and values:
        hints.append(Hint(code="columns_guessed"))

    # Der Anfangssaldo vom Foto ist nur im ersten Monat der Ablage ein Vorschlag;
    # sonst gilt ohnehin der Übertrag (ADR 0004).
    ledger = blank_month(
        year,
        month,
        region,
        source="photo",
        values=values,
        reasons=reasons,
        opening_balance=checks.opening,
    )
    return PhotoReading(ledger=ledger, hints=hints, recognized_days=len(values), checks=checks)


# --- intern -------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Columns:
    """x-Mitten der Spalten aus der Kopfzeile."""

    income: float
    expense: float
    balance: float | None = None


@dataclass(frozen=True)
class _Number:
    x: float
    value: Decimal
    box: TextBox


@dataclass
class _Cells:
    amounts: tuple[Decimal | None, Decimal | None]
    balance: Decimal | None
    reason: str
    suspects: list[SuspectCell] = field(default_factory=list)
    numbers: list[_Number] = field(default_factory=list)

    def single_amount(self) -> Decimal | None:
        """Für Zeilen mit nur einem Betrag (Übertrag): Saldo-Spalte, sonst die letzte Zahl."""
        if self.balance is not None:
            return self.balance
        live = [n.value for n in self.numbers if not n.box.struck]
        return live[-1] if live else None


def _group_rows(boxes: list[TextBox]) -> list[list[TextBox]]:
    """Boxen mit ähnlicher vertikaler Mitte bilden eine Tabellenzeile."""
    if not boxes:
        return []
    tolerance = median(b.height for b in boxes) * 0.6
    rows: list[list[TextBox]] = []
    for box in sorted(boxes, key=lambda b: b.cy):
        if rows and abs(box.cy - median(b.cy for b in rows[-1])) <= tolerance:
            rows[-1].append(box)
        else:
            rows.append([box])
    return [sorted(r, key=lambda b: b.x0) for r in rows]


def _find_columns(rows: list[list[TextBox]]) -> _Columns | None:
    for row in rows:
        income = _header_x(row, INCOME_WORDS)
        expense = _header_x(row, EXPENSE_WORDS)
        balance = _header_x(row, BALANCE_WORDS)
        if income is not None and expense is not None:
            return _Columns(income, expense, balance)
        if income is not None and any(matches_any(b.text, DATE_WORDS) for b in row):
            return _Columns(income, income + 2 * max(b.x1 - b.x0 for b in row), balance)
    return None


def _header_x(row: list[TextBox], words: tuple[str, ...]) -> float | None:
    return next((b.cx for b in row if matches_any(b.text, words)), None)


def _read_cells(cells: list[TextBox], columns: _Columns | None) -> _Cells:
    """Beträge den Spalten zuordnen, restlichen Text als Grund sammeln."""
    numbers: list[_Number] = []
    words: list[str] = []
    for box in cells:
        value = parse_amount(box.text)
        if value is not None:
            numbers.append(_Number(box.cx, value, box))
            continue
        # Box mit Betrag und Text zusammen, z. B. "12,50 Brot"
        for token in box.text.split():
            if (v := parse_amount(token)) is not None:
                numbers.append(_Number(box.cx, v, box))
            elif any(c.isalpha() for c in token):
                words.append(token)

    groups: dict[str, list[_Number]] = {"income": [], "expense": [], "balance": []}
    if columns is None:
        # Reihenfolge: Einnahme, Ausgabe, dann Saldo
        for target, number in zip(("income", "expense", "balance"), numbers, strict=False):
            groups[target].append(number)
    else:
        targets = {"income": columns.income, "expense": columns.expense}
        if columns.balance is not None:
            targets["balance"] = columns.balance
        for number in numbers:
            groups[min(targets, key=lambda k: abs(targets[k] - number.x))].append(number)

    chosen: dict[str, Decimal | None] = {}
    suspects: list[SuspectCell] = []
    for name, group in groups.items():
        live = [n for n in group if not n.box.struck]
        # Mehrere Zahlen: die rechte ist meist die Korrektur
        chosen[name] = live[-1].value if live else None
        if name != "balance" and (reason := _suspect_reason(group, live)) is not None:
            suspects.append(
                SuspectCell(
                    day=0,  # setzt die aufrufende Zeile
                    field="income" if name == "income" else "expense",
                    reason=reason,
                    read=[n.value for n in group],
                    struck=[n.value for n in group if n.box.struck],
                )
            )
    return _Cells(
        amounts=(chosen["income"], chosen["expense"]),
        balance=chosen["balance"],
        reason=" ".join(words),
        suspects=suspects,
        numbers=numbers,
    )


def _suspect_reason(group: list[_Number], live: list[_Number]) -> SuspectReason | None:
    if len(live) < len(group):
        return "struck"
    if len(live) > 1:
        return "several"
    if any(n.box.confidence < UNSURE_BELOW for n in live):
        return "unsure"
    return None


def _decide_period(
    boxes: list[TextBox],
    row_dates: list[tuple[int | None, int | None]],
    fallback: date,
    hints: list[Hint],
) -> tuple[int, int]:
    month, year = find_period([b.text for b in sorted(boxes, key=lambda b: b.cy)])
    if month is None:
        months = Counter(m for m, _ in row_dates if m is not None)
        month = months.most_common(1)[0][0] if months else None
    if year is None:
        years = Counter(y for _, y in row_dates if y is not None)
        year = years.most_common(1)[0][0] if years else None
    if month is None:
        hints.append(Hint(code="month_not_found"))
        month = fallback.month
    if year is None:
        year = fallback.year
    return month, year
