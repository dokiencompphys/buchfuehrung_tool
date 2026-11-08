"""Kennzahlen über alle abgelegten Buchungsmonate.

Öffentliche Schnittstelle: `compute_metrics(ledgers, today) -> Metrics`.
"Umsatz" = Summe der Einnahmen. "Gewinn" = Einnahmen − Ausgaben.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from buchfuehrung.domain.ledger import ZERO, LedgerMonth


class MonthPoint(BaseModel):
    year: int
    month: int
    income: Decimal
    expense: Decimal
    balance: Decimal


class Comparison(BaseModel):
    current: MonthPoint
    previous: MonthPoint | None
    income_change: Decimal | None  # absolut
    income_change_pct: Decimal | None  # in Prozent


class Metrics(BaseModel):
    year: int
    months_recorded: int
    income_ytd: Decimal
    expense_ytd: Decimal
    balance_ytd: Decimal
    income_previous_year_same_period: Decimal | None
    avg_income_per_month: Decimal | None
    avg_income_per_open_day: Decimal | None
    best_month: MonthPoint | None
    worst_month: MonthPoint | None
    latest: Comparison | None
    same_month_last_year: MonthPoint | None
    series: list[MonthPoint]  # alle Monate des Jahres, chronologisch


def compute_metrics(ledgers: list[LedgerMonth], today: date, year: int | None = None) -> Metrics:
    year = year or today.year
    points = {(lg.year, lg.month): _point(lg) for lg in ledgers}
    this_year = sorted((p for p in points.values() if p.year == year), key=lambda p: p.month)

    income = sum((p.income for p in this_year), ZERO)
    expense = sum((p.expense for p in this_year), ZERO)

    months_so_far = {p.month for p in this_year}
    prev_year_same = [p for p in points.values() if p.year == year - 1 and p.month in months_so_far]

    open_days = [
        e
        for lg in ledgers
        if lg.year == year
        for e in lg.entries
        if e.closed is None and e.income is not None
    ]

    latest = _latest_comparison(points, this_year)
    same_month_last_year = points.get((year - 1, latest.current.month)) if latest else None

    return Metrics(
        year=year,
        months_recorded=len(this_year),
        income_ytd=income,
        expense_ytd=expense,
        balance_ytd=income - expense,
        income_previous_year_same_period=(
            sum((p.income for p in prev_year_same), ZERO) if prev_year_same else None
        ),
        avg_income_per_month=_q(income / len(this_year)) if this_year else None,
        avg_income_per_open_day=(
            _q(sum((e.income or ZERO for e in open_days), ZERO) / len(open_days))
            if open_days
            else None
        ),
        best_month=max(this_year, key=lambda p: p.income, default=None),
        worst_month=min(this_year, key=lambda p: p.income, default=None),
        latest=latest,
        same_month_last_year=same_month_last_year,
        series=this_year,
    )


def _point(lg: LedgerMonth) -> MonthPoint:
    t = lg.totals
    return MonthPoint(
        year=lg.year, month=lg.month, income=t.income, expense=t.expense, balance=t.balance
    )


def _latest_comparison(
    points: dict[tuple[int, int], MonthPoint], this_year: list[MonthPoint]
) -> Comparison | None:
    if not this_year:
        return None
    current = this_year[-1]
    prev_key = (current.year, current.month - 1) if current.month > 1 else (current.year - 1, 12)
    previous = points.get(prev_key)
    if previous is None:
        return Comparison(
            current=current, previous=None, income_change=None, income_change_pct=None
        )
    change = current.income - previous.income
    pct = _q(change / previous.income * 100) if previous.income else None
    return Comparison(
        current=current, previous=previous, income_change=change, income_change_pct=pct
    )


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))
