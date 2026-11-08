"""Konfiguration über Umgebungsvariablen (alle optional)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    default_ocr_engine: str
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.environ.get("BUCH_DATA_DIR", Path.cwd() / "data")).resolve(),
            default_ocr_engine=os.environ.get("BUCH_OCR_ENGINE", "auto"),
            cors_origins=tuple(
                o.strip() for o in os.environ.get("BUCH_CORS_ORIGINS", "*").split(",") if o.strip()
            ),
        )
