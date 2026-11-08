"""Beschriftungen für Export-Dateien (Deutsch / Vietnamesisch)."""

from __future__ import annotations

from typing import Literal

Lang = Literal["de", "vi"]

LABELS: dict[str, dict[str, str]] = {
    "de": {
        "title": "Buchführung",
        "date": "Datum",
        "income": "Einnahmen",
        "expense": "Ausgaben",
        "note": "Bemerkung",
        "total": "Summe",
        "balance": "Saldo (Einnahmen − Ausgaben)",
        "sunday": "Sonntag",
        "region": "Bundesland",
        "weekdays": "Mo,Di,Mi,Do,Fr,Sa,So",
    },
    "vi": {
        "title": "Sổ sách kế toán",
        "date": "Ngày",
        "income": "Thu nhập",
        "expense": "Chi phí",
        "note": "Ghi chú",
        "total": "Tổng cộng",
        "balance": "Số dư (Thu − Chi)",
        "sunday": "Chủ nhật",
        "region": "Bang",
        "weekdays": "T2,T3,T4,T5,T6,T7,CN",
    },
}


def labels(lang: Lang) -> dict[str, str]:
    return LABELS.get(lang, LABELS["de"])
