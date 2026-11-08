import io
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from buchfuehrung.domain.factory import blank_month
from buchfuehrung.export.exporter import ExportFormat, export_ledger


@pytest.fixture
def ledger():
    return blank_month(
        2026,
        11,
        "BY",
        values={2: (Decimal("100.00"), Decimal("20.50")), 3: (Decimal("1250.00"), None)},
    )


def test_xlsx_has_sum_formulas_and_grey_closed_days(ledger):
    file = export_ledger(ledger, ExportFormat.XLSX)
    assert file.filename == "buchfuehrung_2026-11.xlsx"
    ws = load_workbook(io.BytesIO(file.content)).active
    # Zeile 1 Titel, 2 Kopf, 3..32 Tage, 33 Summe, 34 Saldo
    assert ws["B4"].value == 100
    assert ws["B33"].value == "=SUM(B3:B32)"
    assert ws["C33"].value == "=SUM(C3:C32)"
    assert ws["B34"].value == "=B33-C33"
    assert ws["A3"].fill.fgColor.rgb.endswith("D9D9D9")  # 01.11. Allerheiligen
    assert ws["D3"].value == "Allerheiligen"
    assert ws["A4"].fill.fgColor.rgb in (None, "00000000")  # 02.11. Werktag


def test_csv_uses_german_number_format(ledger):
    text = export_ledger(ledger, ExportFormat.CSV).content.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "Datum;Einnahmen;Ausgaben;Bemerkung"
    assert lines[2] == "02.11.2026;100,00;20,50;"
    assert lines[-2] == "Summe;1.350,00;20,50;"
    assert lines[-1].startswith("Saldo") and "1.329,50" in lines[-1]


def test_vietnamese_headers(ledger):
    text = export_ledger(ledger, ExportFormat.CSV, "vi").content.decode("utf-8-sig")
    assert text.splitlines()[0] == "Ngày;Thu nhập;Chi phí;Ghi chú"


def test_ods_and_pdf_are_valid_files(ledger):
    ods = export_ledger(ledger, ExportFormat.ODS).content
    assert ods[:2] == b"PK" and b"application/vnd.oasis.opendocument.spreadsheet" in ods
    pdf = export_ledger(ledger, ExportFormat.PDF, "vi").content
    assert pdf.startswith(b"%PDF")
