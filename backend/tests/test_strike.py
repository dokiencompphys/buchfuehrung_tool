"""Durchgestrichene Zahlen werden im Bild erkannt (gezeichnet wie von Hand)."""

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from buchfuehrung.ocr.engine import TextBox
from buchfuehrung.ocr.strike import mark_struck


def draw_number(text, line=None, width=3):
    """Zahl zeichnen, optional mit Linie: "strike", "slanted", "underline"."""
    img = Image.new("RGB", (420, 120), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 30), text, font=ImageFont.load_default(size=44), fill="black")
    x0, y0, x1, y1 = d.textbbox((40, 30), text, font=ImageFont.load_default(size=44))
    cy = (y0 + y1) / 2
    if line == "strike":
        d.line((x0 - 4, cy, x1 + 4, cy), fill="black", width=width)
    elif line == "slanted":
        d.line((x0 - 4, cy + 7, x1 + 4, cy - 7), fill="black", width=width)
    elif line == "underline":
        d.line((x0, y1 + 3, x1, y1 + 3), fill="black", width=width)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    # Box so, wie ein OCR-Modell sie liefern würde: etwas Rand um alles Dunkle
    box = TextBox(text=text, x0=x0 - 6, y0=y0 - 6, x1=x1 + 6, y1=y1 + 8)
    return buf.getvalue(), box


def struck(text, line=None, width=3):
    image, box = draw_number(text, line, width)
    [marked] = mark_struck(image, [box])
    return marked.struck


@pytest.mark.parametrize("text", ["12,50", "1.234,00", "77,77", "-4,80", "480,00", "11,11 €"])
def test_plain_numbers_are_not_struck(text):
    assert not struck(text)


@pytest.mark.parametrize("text", ["12,50", "1.234,00", "77,77", "4,80"])
@pytest.mark.parametrize("line", ["strike", "slanted"])
def test_struck_numbers_are_found(text, line):
    assert struck(text, line)


def test_thin_pen_stroke_is_found():
    assert struck("250,00", "strike", width=2)


def test_underline_is_not_a_strike():
    assert not struck("250,00", "underline")


def test_boxes_without_digits_are_left_alone():
    image, box = draw_number("Porto", "strike")
    [marked] = mark_struck(image, [box.model_copy(update={"text": "Porto"})])
    assert not marked.struck


def test_unreadable_image_leaves_boxes_unchanged():
    box = TextBox(text="12,50", x0=0, y0=0, x1=10, y1=10)
    assert mark_struck(b"kein Bild", [box]) == [box]
