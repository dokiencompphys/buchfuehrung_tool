"""Adapter für Surya OCR (https://github.com/datalab-to/surya).

Installation: `uv sync --extra surya`. Modelle werden beim ersten Aufruf geladen.
Unterstützt die neue API (FoundationPredictor, ab 0.15) und die ältere.
"""

from __future__ import annotations

import io
from functools import cached_property
from typing import Any

from buchfuehrung.ocr.engine import EngineUnavailable, TextBox


class SuryaEngine:
    id = "surya"

    @cached_property
    def _predictors(self) -> tuple[Any, Any]:
        try:
            from surya.detection import DetectionPredictor
            from surya.recognition import RecognitionPredictor
        except ImportError as exc:
            raise EngineUnavailable("surya-ocr ist nicht installiert") from exc
        try:
            from surya.foundation import FoundationPredictor

            recognition = RecognitionPredictor(FoundationPredictor())
        except ImportError:
            recognition = RecognitionPredictor()
        return DetectionPredictor(), recognition

    def recognize(self, image: bytes) -> list[TextBox]:
        from PIL import Image

        detection, recognition = self._predictors
        img = Image.open(io.BytesIO(image)).convert("RGB")
        try:
            result = recognition([img], det_predictor=detection)[0]
        except TypeError:  # ältere API mit Sprachliste
            result = recognition([img], [["de"]], detection)[0]
        return [
            TextBox(
                text=line.text,
                x0=line.bbox[0],
                y0=line.bbox[1],
                x1=line.bbox[2],
                y1=line.bbox[3],
                confidence=float(getattr(line, "confidence", 1.0) or 0.0),
            )
            for line in result.text_lines
        ]
