"""Salden über Monatsgrenzen: jeder Monat übernimmt den Endsaldo des vorherigen.

Öffentliche Schnittstelle: `link_months(ledgers)` und `carry_over_before(linked, year, month)`.
Übertrag kommt immer vom letzten früheren Monat in der Ablage – auch wenn
dazwischen Monate fehlen. Einen Anfangssaldo eintragen kann man nur im ersten
Monat der Ablage; in allen späteren gilt immer der Übertrag (ADR 0004).
"""

from __future__ import annotations

from collections.abc import Iterable

from buchfuehrung.domain.ledger import CarryOver, LedgerMonth


def link_months(ledgers: Iterable[LedgerMonth]) -> list[LedgerMonth]:
    """Chronologisch sortiert, jeder Monat mit gesetztem Übertrag."""
    linked: list[LedgerMonth] = []
    for ledger in sorted(ledgers, key=lambda lg: (lg.year, lg.month)):
        linked.append(ledger.model_copy(update={"carry_over": _carry_from(linked)}))
    return linked


def carry_over_before(linked: list[LedgerMonth], year: int, month: int) -> CarryOver | None:
    """Übertrag für einen (neuen oder bestehenden) Monat aus bereits verketteten Monaten."""
    return _carry_from([lg for lg in linked if (lg.year, lg.month) < (year, month)])


def _carry_from(earlier: list[LedgerMonth]) -> CarryOver | None:
    if not earlier:
        return None
    last = earlier[-1]
    return CarryOver(amount=last.totals.closing, year=last.year, month=last.month)
