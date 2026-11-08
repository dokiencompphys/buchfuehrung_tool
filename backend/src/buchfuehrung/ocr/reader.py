"""Foto → Entwurf eines Buchungsmonats.

Öffentliche Schnittstelle: `read_photo(image, engine, region, fallback)`.
Intern: Textboxen zu Zeilen gruppieren, Spalten über die Kopfzeile zuordnen,
Beträge parsen, Monat/Jahr erkennen und mit der Summenzeile gegenprüfen.
Das Ergebnis ist immer nur ein Vorschlag – alle Felder bleiben editierbar.
"""

from __future__ import annotations

import calendar as _cal
from collections import Counter
from datetime import date
from decimal import Decimal
from statistics import median

from pydantic import BaseModel, Field

from buchfuehrung.domain.factory import blank_month
from buchfuehrung.domain.ledger import LedgerMonth
from buchfuehrung.ocr.engine import OcrEngine, TextBox
from buchfuehrung.ocr.parsing import (
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
    row_dates: list[tuple[int | None, int | None]] = []
    photo_totals: tuple[Decimal | None, Decimal | None] | None = None

    for row in rows:
        if any(matches_any(b.text, TOTAL_WORDS) for b in row):
            photo_totals = _amounts(row, columns)
            continue
        parsed_day = parse_day(row[0].text)
        if parsed_day is None:
            continue
        day, mo, yr = parsed_day
        income, expense = _amounts(row[1:], columns)
        if income is None and expense is None:
            continue
        if day in values:
            hints.append(Hint(code="duplicate_day", params={"day": str(day)}))
        values[day] = (income, expense)
        row_dates.append((mo, yr))

    month, year = _decide_period(boxes, row_dates, fallback, hints)
    last_day = _cal.monthrange(year, month)[1]
    for day in [d for d in values if d > last_day]:
        hints.append(Hint(code="day_out_of_month", params={"day": str(day)}))
        del values[day]

    if not values:
        hints.append(Hint(code="no_rows_found"))
    if columns is None and values:
        hints.append(Hint(code="columns_guessed"))

    ledger = blank_month(year, month, region, source="photo", values=values)
    if photo_totals is not None:
        _check_totals(ledger, photo_totals, hints)
    return PhotoReading(ledger=ledger, hints=hints, recognized_days=len(values))


# --- intern -------------------------------------------------------------------------------


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


def _find_columns(rows: list[list[TextBox]]) -> tuple[float, float] | None:
    """x-Mitte der Spalten Einnahmen/Ausgaben aus der Kopfzeile."""
    for row in rows:
        income = next((b.cx for b in row if matches_any(b.text, INCOME_WORDS)), None)
        expense = next((b.cx for b in row if matches_any(b.text, EXPENSE_WORDS)), None)
        if income is not None and expense is not None:
            return income, expense
        if income is not None and any(matches_any(b.text, DATE_WORDS) for b in row):
            return income, income + 2 * max(b.x1 - b.x0 for b in row)
    return None


def _amounts(
    cells: list[TextBox], columns: tuple[float, float] | None
) -> tuple[Decimal | None, Decimal | None]:
    income: Decimal | None = None
    expense: Decimal | None = None
    numbers = [(b, v) for b in cells if (v := parse_amount(b.text)) is not None]
    if columns is None:
        if numbers:
            income = numbers[0][1]
        if len(numbers) > 1:
            expense = numbers[1][1]
        return income, expense
    income_x, expense_x = columns
    for box, value in numbers:
        if abs(box.cx - income_x) <= abs(box.cx - expense_x):
            income = value if income is None else income
        else:
            expense = value if expense is None else expense
    return income, expense


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
