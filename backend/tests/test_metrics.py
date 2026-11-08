from datetime import date
from decimal import Decimal as D

from buchfuehrung.analytics.metrics import compute_metrics
from buchfuehrung.domain.factory import blank_month

TODAY = date(2026, 11, 8)


def month(year, m, income, expense=D("0")):
    # Alles auf den 2. des Monats buchen
    return blank_month(year, m, "BE", values={2: (D(income), D(expense))})


def test_year_to_date_and_month_over_month():
    ledgers = [
        month(2025, 9, "800"),
        month(2026, 8, "1000", "200"),
        month(2026, 9, "1500", "300"),
        month(2026, 10, "1200", "100"),
    ]
    m = compute_metrics(ledgers, TODAY)
    assert m.months_recorded == 3
    assert m.income_ytd == D("3700.00")
    assert m.expense_ytd == D("600.00")
    assert m.balance_ytd == D("3100.00")
    assert m.avg_income_per_month == D("1233.33")
    assert (m.best_month.month, m.worst_month.month) == (9, 8)
    # Oktober gegenüber September: −300 € = −20 %
    assert m.latest.current.month == 10
    assert m.latest.income_change == D("-300.00")
    assert m.latest.income_change_pct == D("-20.00")
    # Vorjahr, gleiche Monate (Aug–Okt 2025): nur September erfasst
    assert m.income_previous_year_same_period == D("800.00")
    assert [p.month for p in m.series] == [8, 9, 10]


def test_previous_month_across_year_boundary():
    m = compute_metrics([month(2025, 12, "500"), month(2026, 1, "750")], TODAY)
    assert m.latest.previous.month == 12
    assert m.latest.income_change_pct == D("50.00")


def test_no_data():
    m = compute_metrics([], TODAY)
    assert m.months_recorded == 0
    assert m.income_ytd == D("0.00")
    assert m.latest is None and m.avg_income_per_month is None
