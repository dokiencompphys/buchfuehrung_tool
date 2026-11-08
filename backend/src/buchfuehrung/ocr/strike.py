"""Durchgestrichene Zahlen erkennen.

OCR-Modelle lesen eine durchgestrichene Zahl meist ganz normal. Hier wird im Bild
nachgesehen, ob eine Linie quer durch die mittlere Höhe der Textbox läuft – auch
leicht schräg, wie von Hand gezogen. Das Ergebnis ist nur ein Verdacht; der Nutzer
wird gefragt.
"""

from __future__ import annotations

import io

from PIL import Image, ImageFilter, UnidentifiedImageError

from buchfuehrung.ocr.engine import TextBox

# Anteil der Boxbreite, den eine Linie mindestens durchgehend überdecken muss.
# Ziffern selbst haben in der Mitte nur kurze waagerechte Stücke.
MIN_COVERAGE = 0.8
ANGLES = (-12, -8, -4, 0, 4, 8, 12)  # Grad; Handstriche sind selten ganz waagerecht
HEIGHT = 32  # Pixel, auf die jede Box vor der Prüfung skaliert wird


def mark_struck(image: bytes, boxes: list[TextBox]) -> list[TextBox]:
    """Boxen mit Ziffern, durch die eine Linie geht, bekommen `struck=True`."""
    try:
        gray = Image.open(io.BytesIO(image)).convert("L")
    except (UnidentifiedImageError, OSError):
        return boxes  # kein lesbares Bild (z. B. Demo-Engine in Tests)
    return [
        box.model_copy(update={"struck": True})
        if any(c.isdigit() for c in box.text) and is_struck(gray, box)
        else box
        for box in boxes
    ]


def is_struck(gray: Image.Image, box: TextBox) -> bool:
    x0, y0 = max(0, int(box.x0)), max(0, int(box.y0))
    x1, y1 = min(gray.width, int(box.x1)), min(gray.height, int(box.y1))
    if x1 - x0 < 8 or y1 - y0 < 6:
        return False
    crop = gray.crop((x0, y0, x1, y1))
    # Auf feste Höhe bringen: gleiche Regeln für kleine und große Fotos, und schnell
    width = max(8, round(crop.width * HEIGHT / crop.height))
    crop = crop.resize((width, HEIGHT))
    # Papier ist hell: „dunkel“ relativ zum Kontrast der Box bestimmen
    lo, hi = crop.getextrema()
    if hi - lo < 40:
        return False
    threshold = lo + (hi - lo) * 0.5
    ink = crop.point(lambda v: 0 if v < threshold else 255)
    ink = ink.filter(ImageFilter.MinFilter(3))  # kleine Lücken im Strich schließen
    return any(_has_line(ink.rotate(a, fillcolor=255), width) for a in ANGLES)


def _has_line(ink: Image.Image, box_width: int) -> bool:
    """Gibt es in der mittleren Höhe eine Zeile mit einem langen, durchgehenden Strich?"""
    w, h = ink.size
    for y in range(int(h * 0.3), int(h * 0.75) + 1):
        row = ink.crop((0, y, w, y + 1)).tobytes()
        if max(map(len, row.split(b"\xff"))) >= MIN_COVERAGE * box_width:
            return True
    return False
