"""Text-Erkennung für Beträge, Tage und den Monat – tolerant gegenüber OCR-Fehlern."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# Typische OCR-Verwechslungen in Zahlen
_OCR_DIGIT_FIXES = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "|": "1", "S": "5"})

_MONTHS: dict[str, int] = {
    # Deutsch
    "januar": 1, "jan": 1, "jänner": 1, "februar": 2, "feb": 2, "märz": 3, "maerz": 3,
    "mär": 3, "mrz": 3, "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6, "juli": 7,
    "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "oktober": 10,
    "okt": 10, "november": 11, "nov": 11, "dezember": 12, "dez": 12,
}  # fmt: skip

_DAY_RE = re.compile(r"^(\d{1,2})\.?(?:(\d{1,2})\.?(?:(\d{2}|\d{4}))?)?$")
_AMOUNT_CHARS_RE = re.compile(r"[€\s]|eur|euro", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_NUMERIC_PERIOD_RE = re.compile(r"\b(\d{1,2})\s*[./-]\s*(20\d{2})\b")
_VI_PERIOD_RE = re.compile(r"th[áa]ng\s*(\d{1,2})", re.IGNORECASE)

INCOME_WORDS = ("einnahme", "einnahmen", "ein", "thu", "thu nhập", "doanh thu")
EXPENSE_WORDS = ("ausgabe", "ausgaben", "aus", "chi", "chi phí")
DATE_WORDS = ("datum", "tag", "ngày")
BALANCE_WORDS = ("saldo", "bestand", "kassenstand", "kasse", "số dư", "so du", "tồn quỹ")
REASON_WORDS = (
    "grund", "zweck", "bemerkung", "beschreibung", "verwendung", "text",
    "lý do", "ly do", "ghi chú", "ghi chu", "nội dung", "noi dung",
)  # fmt: skip
TOTAL_WORDS = ("summe", "gesamt", "total", "tổng", "tong")


def parse_amount(text: str) -> Decimal | None:
    """'1.234,50' → 1234.50, '12,-' → 12.00, '12.5' → 12.50. Sonst None."""
    raw = _AMOUNT_CHARS_RE.sub("", text.strip())
    raw = re.sub(r"[,.]?-+$", "", raw)  # '12,-' → '12'
    if not raw:
        return None
    raw = raw.translate(_OCR_DIGIT_FIXES)
    if not re.fullmatch(r"[\d.,]+", raw) or not any(c.isdigit() for c in raw):
        return None
    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") == 1 and len(raw.split(".")[1]) != 3:
        normalized = raw  # Dezimalpunkt: 12.5 oder 12.50
    else:
        normalized = raw.replace(".", "")  # Tausenderpunkt: 1.234
    if normalized.count(".") > 1:
        return None
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None
    return value.quantize(Decimal("0.01"))


def parse_day(text: str) -> tuple[int, int | None, int | None] | None:
    """'3', '03.', '03.11.', '3.11.26', '03.11.2026' → (Tag, Monat?, Jahr?)."""
    m = _DAY_RE.match(text.strip().replace(" ", ""))
    if not m:
        return None
    day = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else None
    year = int(m.group(3)) if m.group(3) else None
    if year is not None and year < 100:
        year += 2000
    if not 1 <= day <= 31 or (month is not None and not 1 <= month <= 12):
        return None
    return day, month, year


def find_period(texts: list[str]) -> tuple[int | None, int | None]:
    """Monat und Jahr aus Überschriften wie 'November 2026', '11/2026', 'Tháng 11 năm 2026'."""
    month: int | None = None
    year: int | None = None
    for text in texts:
        lower = text.lower()
        if m := _NUMERIC_PERIOD_RE.search(lower):
            mo = int(m.group(1))
            if 1 <= mo <= 12:
                return mo, int(m.group(2))
        if month is None:
            if m := _VI_PERIOD_RE.search(lower):
                mo = int(m.group(1))
                month = mo if 1 <= mo <= 12 else None
            else:
                for word in re.findall(r"[a-zäöü]+", lower):
                    if word in _MONTHS and len(word) >= 3:
                        month = _MONTHS[word]
                        break
        if year is None and (m := _YEAR_RE.search(lower)):
            year = int(m.group(1))
    return month, year


def matches_any(text: str, words: tuple[str, ...]) -> bool:
    lower = text.lower().strip(" :.")
    return any(lower == w or lower.startswith(w) for w in words if len(w) > 3) or lower in words
