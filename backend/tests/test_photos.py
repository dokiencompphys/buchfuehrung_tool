"""Fotos werden vor der Texterkennung vereinheitlicht (iPhone-HEIC, EXIF-Drehung, Größe)."""

import io

import pytest
from PIL import Image

from buchfuehrung.photos import MAX_SIDE, UnreadablePhoto, prepare_photo


def encode(img: Image.Image, fmt: str, **kwargs) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def decode(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def test_heic_from_iphone_becomes_jpeg():
    heic = encode(Image.new("RGB", (640, 480), (200, 30, 30)), "HEIF")
    out = decode(prepare_photo(heic))
    assert out.format == "JPEG"
    assert out.mode == "RGB"
    assert out.size == (640, 480)


def test_photo_is_turned_upright_by_exif_orientation():
    # Links schwarz, rechts weiß, gespeichert „liegend“ mit EXIF-Drehung 6
    # (= zum Anzeigen 90° im Uhrzeigersinn drehen). Danach ist Schwarz oben.
    img = Image.new("RGB", (400, 200), "white")
    img.paste((0, 0, 0), (0, 0, 200, 200))
    exif = Image.Exif()
    exif[0x0112] = 6
    out = decode(prepare_photo(encode(img, "JPEG", exif=exif)))
    assert out.size == (200, 400)
    assert out.getpixel((100, 50))[0] < 50  # oben schwarz
    assert out.getpixel((100, 350))[0] > 200  # unten weiß


def test_large_photo_is_scaled_down_keeping_proportions():
    big = encode(Image.new("RGB", (8064, 6048), "white"), "JPEG")  # 48-MP-iPhone
    out = decode(prepare_photo(big))
    assert out.size == (MAX_SIDE, 2250)  # 6048 * 3000 / 8064


def test_transparent_screenshot_gets_white_background():
    png = encode(Image.new("RGBA", (50, 50), (0, 0, 0, 0)), "PNG")
    out = decode(prepare_photo(png))
    assert out.getpixel((25, 25)) == (255, 255, 255)


@pytest.mark.parametrize("data", [b"", b"kein Bild", b"%PDF-1.7"])
def test_unreadable_file_is_reported(data):
    with pytest.raises(UnreadablePhoto):
        prepare_photo(data)
