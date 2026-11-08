"""Buchungsmonat: das zentrale Domänenobjekt.

Ein Buchungsmonat hat für jeden Kalendertag genau eine Tageszeile.
Summen werden immer berechnet, nie gespeichert.
"""

from __future__ import annotations

import calendar as _cal
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

ZERO = Decimal("0.00")


class ClosedKind(StrEnum):
    SUNDAY = "sunday"
    HOLIDAY = "holiday"


class ClosedDay(BaseModel):
    """Ruhetag: Sonntag oder gesetzlicher Feiertag. Werte bleiben trotzdem editierbar."""

    kind: ClosedKind
    name: str = ""


class DayEntry(BaseModel):
    day: date
    income: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    expense: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    closed: ClosedDay | None = None
    note: str = ""


class Totals(BaseModel):
    income: Decimal
    expense: Decimal
    balance: Decimal


Source = Literal["manual", "photo"]


class LedgerMonth(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    region: str
    source: Source = "manual"
    photo_id: str | None = None
    entries: list[DayEntry]

    @model_validator(mode="after")
    def _one_entry_per_day(self) -> LedgerMonth:
        expected = days_of_month(self.year, self.month)
        got = [e.day for e in self.entries]
        if sorted(got) != expected:
            raise ValueError(
                f"Buchungsmonat {self.month:02d}/{self.year} braucht genau eine Zeile pro Tag"
            )
        self.entries.sort(key=lambda e: e.day)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def totals(self) -> Totals:
        income = sum((e.income or ZERO for e in self.entries), ZERO)
        expense = sum((e.expense or ZERO for e in self.entries), ZERO)
        return Totals(income=income, expense=expense, balance=income - expense)

    @property
    def period(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def days_of_month(year: int, month: int) -> list[date]:
    last = _cal.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, last + 1)]
