"""Welche OCR-Engines gibt es, und welche sind installiert?

Neue Modelle: Adapter in `engines/` schreiben und hier in `_FACTORIES` eintragen.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from functools import cache

from pydantic import BaseModel

from buchfuehrung.ocr.engine import EngineUnavailable, OcrEngine
from buchfuehrung.ocr.engines.fake import FakeEngine
from buchfuehrung.ocr.engines.paddle import PaddleEngine
from buchfuehrung.ocr.engines.surya import SuryaEngine


class EngineInfo(BaseModel):
    id: str
    name: str
    installed: bool


_FACTORIES: dict[str, tuple[str, str | None, Callable[[], OcrEngine]]] = {
    # id: (Anzeigename, Python-Modul zur Installationsprüfung, Fabrik)
    "surya": ("Surya OCR", "surya", SuryaEngine),
    "paddle": ("PaddleOCR", "paddleocr", PaddleEngine),
    "fake": ("Demo (ohne Modell)", None, FakeEngine),
}


def available_engines() -> list[EngineInfo]:
    return [
        EngineInfo(id=eid, name=name, installed=_installed(module))
        for eid, (name, module, _) in _FACTORIES.items()
    ]


AUTO = "auto"


def resolve_engine_id(engine_id: str) -> str:
    """`auto` = erstes installiertes echtes Modell, sonst die Demo-Engine."""
    if engine_id != AUTO:
        return engine_id
    for eid, (_, module, _) in _FACTORIES.items():
        if module is not None and _installed(module):
            return eid
    return "fake"


@cache
def get_engine(engine_id: str) -> OcrEngine:
    """Engines werden einmal erzeugt und behalten ihre geladenen Modelle."""
    engine_id = resolve_engine_id(engine_id)
    if engine_id not in _FACTORIES:
        raise EngineUnavailable(f"Unbekannte OCR-Engine: {engine_id}")
    name, module, factory = _FACTORIES[engine_id]
    if not _installed(module):
        raise EngineUnavailable(f"{name} ist nicht installiert")
    return factory()


def _installed(module: str | None) -> bool:
    return module is None or importlib.util.find_spec(module) is not None
