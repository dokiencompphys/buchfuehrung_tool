"""Sucht eine Unicode-Schrift für PDFs (nötig für vietnamesische Zeichen)."""

from __future__ import annotations

import os
from pathlib import Path

_CANDIDATES = (
    os.environ.get("BUCH_PDF_FONT", ""),
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


def unicode_font_path() -> str | None:
    for candidate in _CANDIDATES:
        if candidate and Path(candidate).is_file():
            return candidate
    return None
