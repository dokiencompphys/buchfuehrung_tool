"""Fake-Engine für Tests und für die Entwicklung ohne installiertes Modell.

Liefert vorgegebene Textboxen. Ohne Vorgabe: eine kleine Beispieltabelle,
damit der Foto-Ablauf in der App auch ohne OCR-Modell durchgespielt werden kann.
"""

from __future__ import annotations

from buchfuehrung.ocr.engine import TextBox


def _row(y: float, *cells: tuple[float, str]) -> list[TextBox]:
    return [TextBox(text=t, x0=x, y0=y, x1=x + 80, y1=y + 30) for x, t in cells]


DEMO_BOXES: list[TextBox] = [
    *_row(10, (20, "November 2026")),
    *_row(60, (20, "Datum"), (200, "Einnahmen"), (400, "Ausgaben")),
    *_row(100, (20, "02.11."), (200, "312,50"), (400, "45,00")),
    *_row(140, (20, "03.11."), (200, "287,00"), (400, "12,80")),
    *_row(180, (20, "04.11."), (200, "1.020,00")),
    *_row(220, (20, "05.11."), (200, "198,40"), (400, "230,00")),
]


class FakeEngine:
    id = "fake"

    def __init__(self, boxes: list[TextBox] | None = None) -> None:
        self._boxes = DEMO_BOXES if boxes is None else boxes

    def recognize(self, image: bytes) -> list[TextBox]:
        return list(self._boxes)
