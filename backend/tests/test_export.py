import io
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from buchfuehrung.domain.factory import blank_month
from buchfuehrung.domain.ledger import CarryOver
from buchfuehrung.export.exporter import ExportFormat, export_ledger


@pytest.fixture
def ledger():
    lg = blank_month(
        2026,
        11,
        "BY",
        values={2: (Decimal("100.00"), Decimal("20.50")), 3: (Decimal("1250.00"), None)},
        reasons={2: "Brot und Milch"},
    )
    # Übertrag aus Oktober: 500,00 €
    return lg.model_copy(
        update={"carry_over": CarryOver(amount=Decimal("500.00"), year=2026, month=10)}
    )


def test_xlsx_has_balance_column_with_formulas(ledger):
    file = export_ledger(ledger, ExportFormat.XLSX)
    assert file.filename == "buchfuehrung_2026-11.xlsx"
    ws = load_workbook(io.BytesIO(file.content)).active
    # Zeile 1 Titel, 2 Kopf, 3 Übertrag, 4..33 Tage, 34 Summe/Endsaldo, 35 Überschuss
    assert [c.value for c in ws[2]] == ["Datum", "Einnahmen", "Ausgaben", "Saldo", "Grund"]
    assert ws["A3"].value == "Übertrag aus 10/2026"
    assert ws["D3"].value == 500
    assert ws["B5"].value == 100
    assert ws["D5"].value == "=D4+B5-C5"
    assert ws["E5"].value == "Brot und Milch"
    assert ws["B34"].value == "=SUM(B4:B33)"
    assert ws["D34"].value == "=D33"
    assert ws["B35"].value == "=B34-C34"
    assert ws["A4"].fill.fgColor.rgb.endswith("D9D9D9")  # 01.11. Allerheiligen
    assert ws["A4"].value == "So 01.11.2026 · Allerheiligen"
    assert ws["A5"].fill.fgColor.rgb in (None, "00000000")  # 02.11. Werktag


def test_csv_shows_running_balance_and_reason(ledger):
    text = export_ledger(ledger, ExportFormat.CSV).content.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "Datum;Einnahmen;Ausgaben;Saldo;Grund"
    assert lines[1] == "Übertrag aus 10/2026;;;500,00;"
    assert lines[2] == "01.11.2026;;;500,00;"
    assert lines[3] == "02.11.2026;100,00;20,50;579,50;Brot und Milch"
    assert lines[4] == "03.11.2026;1.250,00;;1.829,50;"
    assert lines[-2] == "Summe / Endsaldo;1.350,00;20,50;1.829,50;"
    assert lines[-1] == "Überschuss (Einnahmen − Ausgaben);1.329,50;;;"


def test_manual_opening_balance_wins_over_carry_over(ledger):
    manual = ledger.model_copy(update={"opening_balance": Decimal("-50.00")})
    lines = export_ledger(manual, ExportFormat.CSV).content.decode("utf-8-sig").splitlines()
    assert lines[1] == "Anfangssaldo;;;-50,00;"
    assert lines[-2].endswith(";1.279,50;")


def test_vietnamese_headers(ledger):
    text = export_ledger(ledger, ExportFormat.CSV, "vi").content.decode("utf-8-sig")
    assert text.splitlines()[0] == "Ngày;Thu nhập;Chi phí;Số dư;Lý do"


def test_ods_and_pdf_are_valid_files(ledger):
    ods = export_ledger(ledger, ExportFormat.ODS).content
    assert ods[:2] == b"PK" and b"application/vnd.oasis.opendocument.spreadsheet" in ods
    pdf = export_ledger(ledger, ExportFormat.PDF, "vi").content
    assert pdf.startswith(b"%PDF")
