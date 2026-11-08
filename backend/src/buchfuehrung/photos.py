"""Handyfotos in ein Bild bringen, das jedes OCR-Modell und jeder Browser lesen kann.

iPhones speichern Fotos standardmäßig als HEIC und legen die Drehung nur als EXIF-Angabe
ab. Hier wird jedes hochgeladene Bild einmal vereinheitlicht: richtig gedreht, RGB, nicht
größer als nötig, als JPEG. Die OCR-Adapter wandeln dieses JPEG dann in das Eingabeformat
ihres Modells um (siehe `ocr/engines/`).
"""

import io

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()  # HEIC/HEIF für Pillow lesbar machen

# Längste Seite in Pixeln. Eine Monatsseite ist damit gut lesbar; größere Fotos
# (iPhone: bis 8064 px) kosten nur Rechenzeit.
MAX_SIDE = 3000
JPEG_QUALITY = 90


class UnreadablePhoto(ValueError):
    """Die Datei ist kein Bild, das wir lesen können."""


def prepare_photo(raw: bytes) -> bytes:
    """Beliebiges Foto (JPEG, PNG, HEIC, WebP, …) → aufrecht gedrehtes RGB-JPEG."""
    try:
        with Image.open(io.BytesIO(raw)) as original:
            img = ImageOps.exif_transpose(original)
            img = _on_white(img)
            img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise UnreadablePhoto("Bildformat nicht erkannt") from exc

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY)
    return out.getvalue()


def _on_white(img: Image.Image) -> Image.Image:
    """Durchsichtige Flächen (z. B. Bildschirmfotos als PNG) weiß statt schwarz machen."""
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")
