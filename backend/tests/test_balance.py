"""Saldo: laufend pro Tag und über Monatsgrenzen (Übertrag)."""

from decimal import Decimal as D

from buchfuehrung.domain.balance import carry_over_before, link_months
from buchfuehrung.domain.factory import blank_month


def month(m, income="0", expense="0", opening=None, year=2026):
    return blank_month(year, m, "BE", values={2: (D(income), D(expense))}, opening_balance=opening)


def test_running_balance_per_day():
    lg = blank_month(
        2026,
        11,
        "BE",
        values={2: (D("100.00"), D("30.00")), 5: (None, D("200.00"))},
        opening_balance=D("50.00"),
    )
    balances = lg.running_balances()
    assert balances[0] == D("50.00")  # 1.: nichts gebucht
    assert balances[1] == D("120.00")  # 2.: 50 + 100 − 30
    assert balances[4] == D("-80.00")  # 5.: 120 − 200 (darf negativ werden)
    assert balances[-1] == D("-80.00")
    assert lg.totals.closing == D("-80.00")
    assert lg.totals.result == D("-130.00")


def test_first_month_without_opening_starts_at_zero():
    assert month(1, "10").totals.opening == D("0.00")


def test_each_month_carries_over_the_previous_closing_balance():
    linked = link_months(
        [month(10, "300", "100"), month(9, "0", "0", opening=D("1000")), month(11, "50")]
    )
    assert [(lg.month, lg.totals.opening, lg.totals.closing) for lg in linked] == [
        (9, D("1000"), D("1000")),
        (10, D("1000"), D("1200")),
        (11, D("1200"), D("1250")),
    ]
    assert linked[2].carry_over.month == 10


def test_manual_opening_balance_restarts_the_chain():
    # Kassensturz im November: tatsächlich nur 900 € in der Kasse
    linked = link_months(
        [month(10, "500", opening=D("100")), month(11, "50", opening=D("900")), month(12, "10")]
    )
    assert linked[1].totals.opening == D("900")
    assert linked[2].totals.opening == D("950")


def test_gap_months_carry_from_the_last_recorded_month():
    linked = link_months([month(3, "100", opening=D("0")), month(7, "20")])
    assert linked[1].carry_over.month == 3
    assert linked[1].totals.opening == D("100")


def test_carry_over_for_a_new_month():
    linked = link_months([month(9, "100", opening=D("0")), month(12, "5")])
    carry = carry_over_before(linked, 2026, 10)
    assert (carry.month, carry.amount) == (9, D("100"))
    assert carry_over_before(linked, 2026, 9) is None
