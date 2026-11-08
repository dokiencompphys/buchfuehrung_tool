"""Adapter für PaddleOCR (https://github.com/PaddlePaddle/PaddleOCR).

Installation: `uv sync --extra paddle`. Unterstützt PaddleOCR 3.x (`predict`)
und 2.x (`ocr`).
"""

from __future__ import annotations

import io
from functools import cached_property
from typing import Any

from buchfuehrung.ocr.engine import EngineUnavailable, TextBox


class PaddleEngine:
    id = "paddle"

    def __init__(self, lang: str = "german") -> None:
        self._lang = lang

    @cached_property
    def _ocr(self) -> Any:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise EngineUnavailable("paddleocr ist nicht installiert") from exc
        try:
            return PaddleOCR(lang=self._lang, use_textline_orientation=True)
        except TypeError:  # 2.x
            return PaddleOCR(lang=self._lang, use_angle_cls=True, show_log=False)

    def recognize(self, image: bytes) -> list[TextBox]:
        import numpy as np
        from PIL import Image

        arr = np.array(Image.open(io.BytesIO(image)).convert("RGB"))
        if hasattr(self._ocr, "predict"):
            return list(_from_v3(self._ocr.predict(arr)))
        return list(_from_v2(self._ocr.ocr(arr)))


def _from_v3(results: Any):
    for res in results:
        data = res.json["res"] if hasattr(res, "json") else res
        for text, score, poly in zip(
            data["rec_texts"], data["rec_scores"], data["rec_polys"], strict=False
        ):
            yield _box(text, score, poly)


def _from_v2(results: Any):
    for page in results or []:
        for poly, (text, score) in page or []:
            yield _box(text, score, poly)


def _box(text: str, score: float, poly: Any) -> TextBox:
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return TextBox(text=text, x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys), confidence=score)
