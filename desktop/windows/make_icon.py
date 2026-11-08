"""Zeichnet das Desktop-Symbol: weißes € auf blauer Fläche (Hauptfarbe der App).

Aufruf: python make_icon.py <ziel.ico>
"""

import sys

from PIL import Image, ImageDraw, ImageFont

PRIMARY = (11, 79, 138)  # colors.primary in app/src/ui/theme.ts
SIZE = 256


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=48, fill=PRIMARY)
    # Zwei Tabellenlinien unten: „Buchführung“
    for y in (196, 214):
        d.rounded_rectangle((52, y, SIZE - 52, y + 8), radius=4, fill=(255, 255, 255, 170))
    d.text((SIZE / 2, 104), "€", font=_font(150), fill="white", anchor="mm")
    return img


if __name__ == "__main__":
    draw().save(sys.argv[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
