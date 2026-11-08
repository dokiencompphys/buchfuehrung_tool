"""Leere Buchungsmonate erzeugen – mit eingetragenen Ruhetagen."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from buchfuehrung.calendars.closed_days import closed_days
from buchfuehrung.domain.ledger import DayEntry, LedgerMonth, Source, days_of_month


def blank_month(
    year: int,
    month: int,
    region: str,
    *,
    source: Source = "manual",
    values: Mapping[int, tuple[Decimal | None, Decimal | None]] | None = None,
    reasons: Mapping[int, str] | None = None,
    opening_balance: Decimal | None = None,
) -> LedgerMonth:
    """Ein Buchungsmonat mit einer Zeile pro Tag.

    `values` ordnet optional einem Tag (1–31) vorbelegte (Einnahme, Ausgabe) zu,
    `reasons` den Grund, z. B. aus einem Foto. Ruhetage werden markiert, aber nicht geleert.
    """
    closed = closed_days(year, month, region)
    values = values or {}
    reasons = reasons or {}
    entries: list[DayEntry] = []
    for day in days_of_month(year, month):
        income, expense = values.get(day.day, (None, None))
        entries.append(
            DayEntry(
                day=day,
                income=income,
                expense=expense,
                closed=closed.get(day),
                reason=reasons.get(day.day, ""),
            )
        )
    return LedgerMonth(
        year=year,
        month=month,
        region=region,
        source=source,
        opening_balance=opening_balance,
        entries=entries,
    )


def refresh_closed_days(ledger: LedgerMonth) -> LedgerMonth:
    """Ruhetage neu berechnen (z. B. nach Wechsel des Bundeslands). Werte bleiben erhalten."""
    closed = closed_days(ledger.year, ledger.month, ledger.region)
    entries = [e.model_copy(update={"closed": closed.get(e.day)}) for e in ledger.entries]
    return ledger.model_copy(update={"entries": entries})
