"""PaddleOCR-Adapter: Ergebnisformat von PaddleOCR 3.x → Textboxen (ohne echtes Modell)."""

import io
from types import SimpleNamespace

from PIL import Image

from buchfuehrung.ocr.engines.paddle import PaddleEngine


class FakePaddle:
    """Liefert, was PaddleOCR 3.x mit return_word_box=True zurückgibt."""

    def __init__(self, result):
        self.result = result

    def predict(self, image, return_word_box=False):
        assert return_word_box
        return [SimpleNamespace(json={"res": self.result})]  # Ergebnisobjekt mit .json


def png():
    buf = io.BytesIO()
    Image.new("RGB", (100, 50), "white").save(buf, format="PNG")
    return buf.getvalue()


def engine(result):
    e = PaddleEngine()
    e._ocr = FakePaddle(result)  # cached_property lässt sich überschreiben
    return e


def poly(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def test_merged_amounts_are_split_into_boxes_with_their_own_position():
    # Paddle fasst Ausgabe-Korrektur und Saldo zu einer Zeile zusammen
    result = {
        "rec_texts": ["15,00 1.085,00", "Porto"],
        "rec_scores": [0.97, 0.99],
        "rec_polys": [poly(660, 345, 934, 386), poly(1057, 351, 1173, 395)],
        "text_word": [["15", ",", "00", " ", "1.085", ",", "00"], ["Porto"]],
        "text_word_boxes": [
            [
                [668, 345, 688, 386],
                [702, 345, 709, 386],
                [716, 345, 743, 386],
                [763, 345, 770, 386],
                [784, 345, 873, 386],
                [880, 345, 886, 386],
                [893, 345, 921, 386],
            ],
            [[1057, 351, 1173, 395]],
        ],
    }
    boxes = engine(result).recognize(png())
    assert [(b.text, b.x0, b.x1) for b in boxes] == [
        ("15,00", 668, 743),
        ("1.085,00", 784, 921),
        ("Porto", 1057, 1173),
    ]
    assert boxes[0].confidence == 0.97


def test_text_with_one_amount_stays_one_box():
    result = {
        "rec_texts": ["12,50 Porto"],
        "rec_scores": [0.9],
        "rec_polys": [poly(10, 10, 200, 40)],
        "text_word": [["12", ",", "50", " ", "Porto"]],
        "text_word_boxes": [
            [
                [10, 10, 30, 40],
                [31, 10, 35, 40],
                [36, 10, 60, 40],
                [61, 10, 70, 40],
                [80, 10, 200, 40],
            ]
        ],
    }
    [box] = engine(result).recognize(png())
    assert (box.text, box.x0, box.x1) == ("12,50 Porto", 10, 200)
