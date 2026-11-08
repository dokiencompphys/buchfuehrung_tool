"""Foto → Entwurf eines Buchungsmonats.

Öffentliche Schnittstelle: `read_photo(image, engine, region, fallback)`.
Intern: Textboxen zu Zeilen gruppieren, Spalten über die Kopfzeile zuordnen,
Beträge und Grund lesen, Monat/Jahr erkennen und mit der Summenzeile gegenprüfen.
Eine Saldo-Spalte auf dem Foto wird erkannt und ignoriert – der Saldo wird immer
berechnet. Das Ergebnis ist nur ein Vorschlag, alle Felder bleiben editierbar.
"""

from __future__ import annotations

import calendar as _cal
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median

from pydantic import BaseModel, Field

from buchfuehrung.domain.factory import blank_month
from buchfuehrung.domain.ledger import LedgerMonth
from buchfuehrung.ocr.engine import OcrEngine, TextBox
from buchfuehrung.ocr.parsing import (
    BALANCE_WORDS,
    DATE_WORDS,
    EXPENSE_WORDS,
    INCOME_WORDS,
    TOTAL_WORDS,
    find_period,
    matches_any,
    parse_amount,
    parse_day,
)


class Hint(BaseModel):
    """Hinweis an den Nutzer. `code` wird in der App übersetzt."""

    code: str
    params: dict[str, str] = Field(default_factory=dict)


class PhotoReading(BaseModel):
    ledger: LedgerMonth
    hints: list[Hint]
    recognized_days: int


def read_photo(image: bytes, engine: OcrEngine, region: str, fallback: date) -> PhotoReading:
    boxes = [b for b in engine.recognize(image) if b.text.strip()]
    return read_boxes(boxes, region, fallback)


def read_boxes(boxes: list[TextBox], region: str, fallback: date) -> PhotoReading:
    hints: list[Hint] = []
    rows = _group_rows(boxes)
    columns = _find_columns(rows)

    values: dict[int, tuple[Decimal | None, Decimal | None]] = {}
    reasons: dict[int, str] = {}
    row_dates: list[tuple[int | None, int | None]] = []
    photo_totals: tuple[Decimal | None, Decimal | None] | None = None

    for row in rows:
        if any(matches_any(b.text, TOTAL_WORDS) for b in row):
            photo_totals = _read_cells(row, columns).amounts
            continue
        parsed_day = parse_day(row[0].text)
        if parsed_day is None:
            continue
        day, mo, yr = parsed_day
        cells = _read_cells(row[1:], columns)
        income, expense = cells.amounts
        if income is None and expense is None and not cells.reason:
            continue
        if day in values:
            hints.append(Hint(code="duplicate_day", params={"day": str(day)}))
        values[day] = (income, expense)
        if cells.reason:
            reasons[day] = cells.reason
        row_dates.append((mo, yr))

    month, year = _decide_period(boxes, row_dates, fallback, hints)
    last_day = _cal.monthrange(year, month)[1]
    for day in [d for d in values if d > last_day]:
        hints.append(Hint(code="day_out_of_month", params={"day": str(day)}))
        del values[day]
        reasons.pop(day, None)

    if not values:
        hints.append(Hint(code="no_rows_found"))
    if columns is None and values:
        hints.append(Hint(code="columns_guessed"))

    ledger = blank_month(year, month, region, source="photo", values=values, reasons=reasons)
    if photo_totals is not None:
        _check_totals(ledger, photo_totals, hints)
    return PhotoReading(ledger=ledger, hints=hints, recognized_days=len(values))


# --- intern -------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Columns:
    """x-Mitten der Spalten aus der Kopfzeile."""

    income: float
    expense: float
    balance: float | None = None


@dataclass(frozen=True)
class _Cells:
    amounts: tuple[Decimal | None, Decimal | None]
    reason: str


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
    numbers: list[tuple[float, Decimal]] = []
    words: list[str] = []
    for box in cells:
        value = parse_amount(box.text)
        if value is not None:
            numbers.append((box.cx, value))
            continue
        # Box mit Betrag und Text zusammen, z. B. "12,50 Brot"
        for token in box.text.split():
            if (v := parse_amount(token)) is not None:
                numbers.append((box.cx, v))
            elif any(c.isalpha() for c in token):
                words.append(token)

    income: Decimal | None = None
    expense: Decimal | None = None
    if columns is None:
        # Reihenfolge: Einnahme, Ausgabe; eine dritte Zahl ist meist der Saldo
        income = numbers[0][1] if numbers else None
        expense = numbers[1][1] if len(numbers) > 1 else None
    else:
        targets = {"income": columns.income, "expense": columns.expense}
        if columns.balance is not None:
            targets["balance"] = columns.balance
        for x, value in numbers:
            nearest = min(targets, key=lambda k: abs(targets[k] - x))
            if nearest == "income" and income is None:
                income = value
            elif nearest == "expense" and expense is None:
                expense = value
            # Saldo vom Foto wird ignoriert – er wird berechnet
    return _Cells(amounts=(income, expense), reason=" ".join(words))


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


def _check_totals(
    ledger: LedgerMonth,
    photo: tuple[Decimal | None, Decimal | None],
    hints: list[Hint],
) -> None:
    computed = (ledger.totals.income, ledger.totals.expense)
    for label, written, calc in zip(("income", "expense"), photo, computed, strict=True):
        if written is not None and written != calc:
            hints.append(
                Hint(
                    code="total_mismatch",
                    params={"column": label, "photo": str(written), "computed": str(calc)},
                )
            )
