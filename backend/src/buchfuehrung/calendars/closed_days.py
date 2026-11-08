"""Ruhetage (Sonntage + gesetzliche Feiertage) je Bundesland.

Öffentliche Schnittstelle: `regions()` und `closed_days(year, month, region)`.
Die Feiertagsdaten kommen aus dem `holidays`-Paket (offline, keine API nötig).
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import holidays
from pydantic import BaseModel

from buchfuehrung.domain.ledger import ClosedDay, ClosedKind, days_of_month

NATIONWIDE = "DE"

_REGION_NAMES: dict[str, str] = {
    NATIONWIDE: "Nur bundesweite Feiertage",
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}


class Region(BaseModel):
    code: str
    name: str


class UnknownRegion(ValueError):
    pass


def regions() -> list[Region]:
    return [Region(code=c, name=n) for c, n in _REGION_NAMES.items()]


def closed_days(year: int, month: int, region: str) -> dict[date, ClosedDay]:
    """Alle Ruhetage eines Monats. Feiertage haben Vorrang vor Sonntagen."""
    calendar = _holiday_calendar(region, year)
    result: dict[date, ClosedDay] = {}
    for day in days_of_month(year, month):
        if day in calendar:
            result[day] = ClosedDay(kind=ClosedKind.HOLIDAY, name=calendar[day])
        elif day.weekday() == 6:
            result[day] = ClosedDay(kind=ClosedKind.SUNDAY)
    return result


@lru_cache(maxsize=64)
def _holiday_calendar(region: str, year: int) -> holidays.HolidayBase:
    if region not in _REGION_NAMES:
        raise UnknownRegion(f"Unbekanntes Bundesland: {region}")
    subdiv = None if region == NATIONWIDE else region
    return holidays.Germany(subdiv=subdiv, years=year, language="de")
