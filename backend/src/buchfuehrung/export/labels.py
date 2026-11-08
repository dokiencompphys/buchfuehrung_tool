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
        "balance": "Saldo",
        "reason": "Grund",
        "opening": "Anfangssaldo",
        "carry_over": "Übertrag aus {period}",
        "total": "Summe / Endsaldo",
        "result": "Überschuss (Einnahmen − Ausgaben)",
        "region": "Bundesland",
        "weekdays": "Mo,Di,Mi,Do,Fr,Sa,So",
    },
    "vi": {
        "title": "Sổ sách kế toán",
        "date": "Ngày",
        "income": "Thu nhập",
        "expense": "Chi phí",
        "balance": "Số dư",
        "reason": "Lý do",
        "opening": "Số dư đầu kỳ",
        "carry_over": "Chuyển từ {period}",
        "total": "Tổng / Số dư cuối kỳ",
        "result": "Chênh lệch (Thu − Chi)",
        "region": "Bang",
        "weekdays": "T2,T3,T4,T5,T6,T7,CN",
    },
}


def labels(lang: Lang) -> dict[str, str]:
    return LABELS.get(lang, LABELS["de"])
