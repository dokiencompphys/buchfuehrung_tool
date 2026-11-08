from datetime import date
from decimal import Decimal

import pytest

from buchfuehrung.ocr.engine import TextBox
from buchfuehrung.ocr.engines.fake import FakeEngine
from buchfuehrung.ocr.parsing import parse_amount
from buchfuehrung.ocr.reader import read_photo

FALLBACK = date(2026, 11, 8)


def row(y, *cells):
    return [TextBox(text=t, x0=x, y0=y, x1=x + 80, y1=y + 30) for x, t in cells]


def read(boxes, region="BY"):
    return read_photo(b"img", FakeEngine(boxes), region, FALLBACK)


def entry(reading, day):
    return next(e for e in reading.ledger.entries if e.day.day == day)


def test_reads_month_header_and_rows_into_columns():
    boxes = [
        *row(10, (20, "Oktober 2026")),
        *row(60, (20, "Datum"), (200, "Einnahmen"), (400, "Ausgaben")),
        *row(100, (20, "1."), (200, "120,50"), (400, "30,00")),
        *row(140, (20, "2."), (400, "15,20")),  # nur Ausgabe
    ]
    reading = read(boxes)
    assert (reading.ledger.year, reading.ledger.month) == (2026, 10)
    assert entry(reading, 1).income == Decimal("120.50")
    assert entry(reading, 1).expense == Decimal("30.00")
    assert entry(reading, 2).income is None
    assert entry(reading, 2).expense == Decimal("15.20")
    assert reading.recognized_days == 2
    assert reading.ledger.source == "photo"


def test_month_is_taken_from_row_dates_when_no_header():
    boxes = [
        *row(100, (20, "03.02.2025"), (200, "10,00"), (400, "1,00")),
        *row(140, (20, "04.02.2025"), (200, "20,00"), (400, "2,00")),
    ]
    reading = read(boxes)
    assert (reading.ledger.year, reading.ledger.month) == (2025, 2)
    assert {h.code for h in reading.hints} == {"columns_guessed"}


def test_falls_back_to_current_month_and_says_so():
    reading = read(row(100, (20, "5"), (200, "10,00")))
    assert (reading.ledger.year, reading.ledger.month) == (2026, 11)
    assert "month_not_found" in {h.code for h in reading.hints}


def test_closed_days_are_marked_but_keep_values():
    # 01.11.2026 = Allerheiligen (Bayern) – trotzdem wurde etwas eingenommen
    boxes = [
        *row(10, (20, "11/2026")),
        *row(60, (20, "Datum"), (200, "Einnahmen"), (400, "Ausgaben")),
        *row(100, (20, "1."), (200, "50,00")),
    ]
    first = entry(read(boxes), 1)
    assert first.closed is not None and first.closed.name == "Allerheiligen"
    assert first.income == Decimal("50.00")


def test_total_row_is_checked_against_rows():
    boxes = [
        *row(10, (20, "November 2026")),
        *row(60, (20, "Datum"), (200, "Einnahmen"), (400, "Ausgaben")),
        *row(100, (20, "2."), (200, "100,00"), (400, "10,00")),
        *row(140, (20, "3."), (200, "50,00"), (400, "5,00")),
        *row(180, (20, "Summe"), (200, "160,00"), (400, "15,00")),
    ]
    reading = read(boxes)
    mismatches = [h for h in reading.hints if h.code == "total_mismatch"]
    assert [m.params["column"] for m in mismatches] == ["income"]
    assert mismatches[0].params == {"column": "income", "photo": "160.00", "computed": "150.00"}


def test_days_beyond_month_end_are_dropped():
    boxes = [*row(10, (20, "Februar 2026")), *row(100, (20, "30."), (200, "5,00"))]
    reading = read(boxes)
    assert reading.recognized_days == 0
    assert "day_out_of_month" in {h.code for h in reading.hints}


def test_empty_photo_gives_blank_month():
    reading = read([])
    assert len(reading.ledger.entries) == 30
    assert "no_rows_found" in {h.code for h in reading.hints}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.234,50", "1234.50"),
        ("12,-", "12.00"),
        ("12.5", "12.50"),
        ("1.234", "1234.00"),
        ("€ 45,00", "45.00"),
        ("4O,00", "40.00"),  # OCR liest 0 als O
        ("Summe", None),
        ("", None),
    ],
)
def test_amount_parsing(text, expected):
    result = parse_amount(text)
    assert (str(result) if result is not None else None) == expected


def test_reason_column_is_read_and_photo_balance_is_ignored():
    boxes = [
        *row(10, (20, "November 2026")),
        *row(
            60, (20, "Datum"), (200, "Einnahmen"), (400, "Ausgaben"), (600, "Saldo"), (800, "Grund")
        ),
        *row(100, (20, "2."), (200, "100,00"), (600, "100,00")),
        *row(140, (20, "3."), (400, "25,00"), (600, "75,00"), (800, "Kasse Wechselgeld")),
    ]
    reading = read(boxes)
    assert entry(reading, 2).expense is None  # 100,00 unter "Saldo" ist keine Ausgabe
    assert entry(reading, 3).expense == Decimal("25.00")
    assert entry(reading, 3).reason == "Kasse Wechselgeld"


def test_amount_and_reason_in_one_box():
    boxes = [*row(10, (20, "11/2026")), *row(100, (20, "4."), (200, "12,50 Porto"))]
    e = entry(read(boxes), 4)
    assert e.income == Decimal("12.50")
    assert e.reason == "Porto"
