from datetime import date

import pytest

from buchfuehrung.calendars.closed_days import UnknownRegion, closed_days, regions
from buchfuehrung.domain.ledger import ClosedKind


def test_sundays_are_closed_days():
    # November 2026: Sonntage sind der 1., 8., 15., 22. und 29.
    closed = closed_days(2026, 11, "BE")
    sundays = sorted(d.day for d, c in closed.items() if c.kind == ClosedKind.SUNDAY)
    assert sundays == [1, 8, 15, 22, 29]


def test_holiday_wins_over_sunday():
    # Allerheiligen 01.11.2026 fällt auf einen Sonntag und ist in Bayern Feiertag
    closed = closed_days(2026, 11, "BY")[date(2026, 11, 1)]
    assert closed.kind == ClosedKind.HOLIDAY
    assert closed.name == "Allerheiligen"


def test_holidays_depend_on_state():
    # Buß- und Bettag (18.11.2026) gibt es nur in Sachsen
    assert date(2026, 11, 18) in closed_days(2026, 11, "SN")
    assert date(2026, 11, 18) not in closed_days(2026, 11, "BY")
    # Fronleichnam (04.06.2026) in Bayern, nicht in Berlin
    assert date(2026, 6, 4) in closed_days(2026, 6, "BY")
    assert date(2026, 6, 4) not in closed_days(2026, 6, "BE")


def test_unknown_region_is_rejected():
    with pytest.raises(UnknownRegion):
        closed_days(2026, 1, "XX")


def test_all_sixteen_states_are_offered():
    codes = {r.code for r in regions()}
    assert len(codes - {"DE"}) == 16
