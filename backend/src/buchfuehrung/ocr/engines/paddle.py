"""Adapter für PaddleOCR (https://github.com/PaddlePaddle/PaddleOCR).

Installation: `uv sync --extra paddle`. Unterstützt PaddleOCR 3.x (`predict`)
und 2.x (`ocr`).
"""

from __future__ import annotations

import io
import os
from functools import cached_property
from typing import Any

from buchfuehrung.ocr.engine import EngineUnavailable, TextBox
from buchfuehrung.ocr.parsing import parse_amount


class PaddleEngine:
    id = "paddle"

    def __init__(self, lang: str = "german") -> None:
        self._lang = lang

    @cached_property
    def _ocr(self) -> Any:
        # Modelle liegen nach dem ersten Download lokal; die Online-Prüfung bremst nur den Start.
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise EngineUnavailable("paddleocr ist nicht installiert") from exc
        try:
            return PaddleOCR(
                lang=self._lang,
                use_textline_orientation=True,
                # Keine eigene Seiten-Drehung/Entzerrung: Die Koordinaten müssen zum Foto
                # passen (Prüfung auf Durchgestrichenes); gedreht wird schon in photos.py.
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                # Mit PaddlePaddle 3.3 bricht die oneDNN-Beschleunigung auf der CPU mit
                # „ConvertPirAttribute2RuntimeAttribute not support“ ab.
                enable_mkldnn=False,
            )
        except TypeError:  # 2.x
            return PaddleOCR(lang=self._lang, use_angle_cls=True, show_log=False)

    def recognize(self, image: bytes) -> list[TextBox]:
        import numpy as np
        from PIL import Image

        arr = np.array(Image.open(io.BytesIO(image)).convert("RGB"))
        if hasattr(self._ocr, "predict"):
            return list(_from_v3(self._ocr.predict(arr, return_word_box=True)))
        return list(_from_v2(self._ocr.ocr(arr)))


def _from_v3(results: Any):
    for res in results:
        data = res.json["res"] if hasattr(res, "json") else res
        words = data.get("text_word") or [None] * len(data["rec_texts"])
        word_boxes = data.get("text_word_boxes") or [None] * len(data["rec_texts"])
        lines = zip(data["rec_texts"], data["rec_scores"], data["rec_polys"], strict=False)
        for (text, score, poly), parts, part_boxes in zip(lines, words, word_boxes, strict=False):
            line = _box(text, score, poly)
            if parts and part_boxes and _several_amounts(text):
                yield from _split_at_spaces(line, parts, part_boxes)
            else:
                yield line


def _from_v2(results: Any):
    for page in results or []:
        for poly, (text, score) in page or []:
            yield _box(text, score, poly)


def _box(text: str, score: float, poly: Any) -> TextBox:
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return TextBox(text=text, x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys), confidence=score)


def _several_amounts(text: str) -> bool:
    """Paddle fasst nah beieinander stehende Zahlen zu einer Zeile zusammen (z. B. Ausgabe und
    Saldo). Dann brauchen wir jede Zahl einzeln mit ihrer Position."""
    return sum(parse_amount(token) is not None for token in text.split()) >= 2


def _split_at_spaces(line: TextBox, parts: list[str], boxes: list[Any]) -> list[TextBox]:
    """Wortteile von Paddle (z. B. '12' ',' '50' ' ' '15' …) zu Wörtern mit eigener Box."""
    out: list[TextBox] = []
    text, xs0, xs1 = "", [], []

    def flush() -> None:
        if text.strip():
            out.append(
                line.model_copy(update={"text": text.strip(), "x0": min(xs0), "x1": max(xs1)})
            )

    for part, box in zip(parts, boxes, strict=False):
        if part.isspace():
            flush()
            text, xs0, xs1 = "", [], []
            continue
        text += part
        xs0.append(float(box[0]))
        xs1.append(float(box[2]))
    flush()
    return out or [line]
