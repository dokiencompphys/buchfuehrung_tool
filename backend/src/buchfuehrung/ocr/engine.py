"""Seam für OCR-Modelle.

Jedes Modell (Surya, PaddleOCR, …) liefert nur Textboxen mit Position.
Die Tabellenlogik liegt NICHT im Adapter, sondern in `reader.py` – so bleiben
die Adapter dünn und die Modelle austauschbar.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class TextBox(BaseModel):
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float = 1.0
    # Wird nicht von der Engine gesetzt, sondern danach im Bild geprüft (ocr/strike.py)
    struck: bool = False

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


class OcrEngine(Protocol):
    id: str

    def recognize(self, image: bytes) -> list[TextBox]:
        """Alle erkannten Textzeilen eines Bildes, in Pixelkoordinaten."""
        ...


class EngineUnavailable(RuntimeError):
    """Modell ist nicht installiert oder konnte nicht geladen werden."""
