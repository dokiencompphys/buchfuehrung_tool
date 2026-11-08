"""Ablage: alle erstellten Buchungsmonate (SQLite) und die Originalfotos (Dateien).

Pro Monat/Jahr gibt es genau einen Buchungsmonat; erneutes Speichern ersetzt ihn.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from buchfuehrung.domain.ledger import LedgerMonth, Totals

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger_months (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (year, month)
);
"""


class ArchiveItem(BaseModel):
    year: int
    month: int
    region: str
    source: str
    has_photo: bool
    totals: Totals
    created_at: datetime
    updated_at: datetime


class Archive:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.photo_dir = data_dir / "photos"
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = data_dir / "buchfuehrung.sqlite3"
        with self._connect() as db:
            db.executescript(_SCHEMA)

    # --- Buchungsmonate -------------------------------------------------------------

    def save(self, ledger: LedgerMonth) -> tuple[LedgerMonth, bool]:
        """Speichert (oder ersetzt) einen Monat. Gibt zurück, ob er neu war."""
        now = _now()
        with self._connect() as db:
            existed = self._exists(db, ledger.year, ledger.month)
            db.execute(
                """
                INSERT INTO ledger_months (year, month, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (year, month) DO UPDATE SET data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (ledger.year, ledger.month, ledger.model_dump_json(), now, now),
            )
        return ledger, not existed

    def get(self, year: int, month: int) -> LedgerMonth | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT data FROM ledger_months WHERE year = ? AND month = ?", (year, month)
            ).fetchone()
        return LedgerMonth.model_validate_json(row[0]) if row else None

    def exists(self, year: int, month: int) -> bool:
        with self._connect() as db:
            return self._exists(db, year, month)

    def delete(self, year: int, month: int) -> bool:
        with self._connect() as db:
            cur = db.execute(
                "DELETE FROM ledger_months WHERE year = ? AND month = ?", (year, month)
            )
        return cur.rowcount > 0

    def all(self) -> list[LedgerMonth]:
        with self._connect() as db:
            rows = db.execute("SELECT data FROM ledger_months ORDER BY year, month").fetchall()
        return [LedgerMonth.model_validate_json(r[0]) for r in rows]

    def list_items(self) -> list[ArchiveItem]:
        """Neueste zuerst – so wie man in einem Ordner blättert."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT data, created_at, updated_at FROM ledger_months "
                "ORDER BY year DESC, month DESC"
            ).fetchall()
        items = []
        for data, created, updated in rows:
            ledger = LedgerMonth.model_validate_json(data)
            items.append(
                ArchiveItem(
                    year=ledger.year,
                    month=ledger.month,
                    region=ledger.region,
                    source=ledger.source,
                    has_photo=ledger.photo_id is not None,
                    totals=ledger.totals,
                    created_at=datetime.fromisoformat(created),
                    updated_at=datetime.fromisoformat(updated),
                )
            )
        return items

    # --- Fotos ----------------------------------------------------------------------

    def store_photo(self, content: bytes, suffix: str) -> str:
        suffix = suffix.lower() if suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
        photo_id = f"{uuid.uuid4().hex}{suffix}"
        (self.photo_dir / photo_id).write_bytes(content)
        return photo_id

    def photo_path(self, photo_id: str) -> Path | None:
        path = (self.photo_dir / photo_id).resolve()
        if path.parent != self.photo_dir.resolve() or not path.is_file():
            return None
        return path

    # --- intern ---------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._db_path)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _exists(db: sqlite3.Connection, year: int, month: int) -> bool:
        return (
            db.execute(
                "SELECT 1 FROM ledger_months WHERE year = ? AND month = ?", (year, month)
            ).fetchone()
            is not None
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()
