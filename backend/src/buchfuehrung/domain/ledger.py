"""Buchungsmonat: das zentrale Domänenobjekt.

Ein Buchungsmonat hat für jeden Kalendertag genau eine Tageszeile.
Summen und Salden werden immer berechnet, nie gespeichert.

Saldo = Kassenstand. Anfangssaldo eines Monats ist immer der Übertrag aus dem
vorherigen Monat (`carry_over`, wird beim Lesen aus der Ablage gesetzt, siehe
`domain/balance.py`). Nur der allererste Monat hat keinen Übertrag; dort gilt der
eingetragene Startwert (`opening_balance`), sonst 0.
"""

from __future__ import annotations

import calendar as _cal
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, computed_field, model_validator

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
    # Grund: wofür das Geld ausgegeben (oder eingenommen) wurde. "note" = alter Name.
    reason: str = Field(default="", validation_alias=AliasChoices("reason", "note"))


class CarryOver(BaseModel):
    """Übertrag: Endsaldo des letzten früheren Monats in der Ablage."""

    amount: Decimal
    year: int
    month: int


class Totals(BaseModel):
    income: Decimal
    expense: Decimal
    result: Decimal  # Überschuss des Monats = Einnahmen − Ausgaben
    opening: Decimal  # Anfangssaldo
    closing: Decimal  # Endsaldo = Anfangssaldo + Überschuss


Source = Literal["manual", "photo"]


class LedgerMonth(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    region: str
    source: Source = "manual"
    photo_id: str | None = None
    opening_balance: Decimal | None = Field(default=None, decimal_places=2)
    carry_over: CarryOver | None = None
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

    @property
    def effective_opening(self) -> Decimal:
        if self.carry_over is not None:
            return self.carry_over.amount  # Kette darf nicht unterbrochen werden (ADR 0004)
        return self.opening_balance if self.opening_balance is not None else ZERO

    @computed_field  # type: ignore[prop-decorator]
    @property
    def totals(self) -> Totals:
        income = sum((e.income or ZERO for e in self.entries), ZERO)
        expense = sum((e.expense or ZERO for e in self.entries), ZERO)
        opening = self.effective_opening
        return Totals(
            income=income,
            expense=expense,
            result=income - expense,
            opening=opening,
            closing=opening + income - expense,
        )

    def running_balances(self) -> list[Decimal]:
        """Saldo am Ende jedes Tages, in der Reihenfolge der Tageszeilen."""
        balance = self.effective_opening
        result = []
        for e in self.entries:
            balance += (e.income or ZERO) - (e.expense or ZERO)
            result.append(balance)
        return result

    @property
    def period(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def days_of_month(year: int, month: int) -> list[date]:
    last = _cal.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, last + 1)]
