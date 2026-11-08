"""HTTP-Schnittstelle für die App. Dünne Schicht: validieren, an Module delegieren."""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from buchfuehrung.analytics.metrics import Metrics, compute_metrics
from buchfuehrung.calendars.closed_days import Region, UnknownRegion, regions
from buchfuehrung.config import Settings
from buchfuehrung.domain.factory import blank_month, refresh_closed_days
from buchfuehrung.domain.ledger import LedgerMonth
from buchfuehrung.export.exporter import ExportFormat, export_ledger
from buchfuehrung.export.labels import Lang
from buchfuehrung.ocr.engine import EngineUnavailable
from buchfuehrung.ocr.reader import PhotoReading, read_photo
from buchfuehrung.ocr.registry import (
    EngineInfo,
    available_engines,
    get_engine,
    resolve_engine_id,
)
from buchfuehrung.storage.archive import Archive, ArchiveItem

MAX_PHOTO_BYTES = 25 * 1024 * 1024


class EnginesResponse(BaseModel):
    default: str
    engines: list[EngineInfo]


class SaveResponse(BaseModel):
    ledger: LedgerMonth
    created: bool


class InfoResponse(BaseModel):
    data_dir: str
    months_stored: int


def create_app(
    settings: Settings | None = None,
    *,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    settings = settings or Settings.from_env()
    archive = Archive(settings.data_dir)

    app = FastAPI(title="Buchführung", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    def get_archive() -> Archive:
        return archive

    ArchiveDep = Annotated[Archive, Depends(get_archive)]

    @app.exception_handler(UnknownRegion)
    async def _unknown_region(_, exc: UnknownRegion):  # type: ignore[no-untyped-def]
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": str(exc)})

    # --- Stammdaten -----------------------------------------------------------------

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/info")
    def info(store: ArchiveDep) -> InfoResponse:
        return InfoResponse(data_dir=str(store.data_dir), months_stored=len(store.list_items()))

    @app.get("/api/regions")
    def list_regions() -> list[Region]:
        return regions()

    @app.get("/api/ocr/engines")
    def list_engines() -> EnginesResponse:
        return EnginesResponse(
            default=resolve_engine_id(settings.default_ocr_engine), engines=available_engines()
        )

    # --- Entwürfe (noch nicht abgelegt) ---------------------------------------------

    @app.get("/api/drafts/blank")
    def blank_draft(
        year: Annotated[int, Query(ge=2000, le=2100)],
        month: Annotated[int, Query(ge=1, le=12)],
        region: str,
    ) -> LedgerMonth:
        return blank_month(year, month, region)

    @app.post("/api/drafts/refresh")
    def refresh_draft(ledger: LedgerMonth) -> LedgerMonth:
        """Ruhetage neu setzen, z. B. nachdem das Bundesland geändert wurde."""
        return refresh_closed_days(ledger)

    @app.post("/api/drafts/photo")
    def photo_draft(
        store: ArchiveDep,
        photo: Annotated[UploadFile, File()],
        region: Annotated[str, Form()],
        engine: Annotated[str | None, Form()] = None,
    ) -> PhotoReading:
        content = photo.file.read(MAX_PHOTO_BYTES + 1)
        if len(content) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "Foto ist zu groß (max. 25 MB)")
        if not content:
            raise HTTPException(422, "Leere Datei")
        try:
            ocr = get_engine(engine or settings.default_ocr_engine)
        except EngineUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        reading = read_photo(content, ocr, region, fallback=today())
        photo_id = store.store_photo(content, Path(photo.filename or "").suffix)
        reading.ledger.photo_id = photo_id
        return reading

    # --- Ablage ---------------------------------------------------------------------

    @app.get("/api/months")
    def list_months(store: ArchiveDep) -> list[ArchiveItem]:
        return store.list_items()

    @app.get("/api/months/{year}/{month}")
    def get_month(year: int, month: int, store: ArchiveDep) -> LedgerMonth:
        return _require(store, year, month)

    @app.put("/api/months/{year}/{month}")
    def save_month(year: int, month: int, ledger: LedgerMonth, store: ArchiveDep) -> SaveResponse:
        if (ledger.year, ledger.month) != (year, month):
            raise HTTPException(422, "Monat/Jahr in Adresse und Daten stimmen nicht überein")
        saved, created = store.save(ledger)
        return SaveResponse(ledger=saved, created=created)

    @app.delete("/api/months/{year}/{month}", status_code=204)
    def delete_month(year: int, month: int, store: ArchiveDep) -> Response:
        if not store.delete(year, month):
            raise HTTPException(404, "Nicht gefunden")
        return Response(status_code=204)

    @app.get("/api/months/{year}/{month}/export")
    def export_month(
        year: int,
        month: int,
        store: ArchiveDep,
        format: ExportFormat = ExportFormat.XLSX,
        lang: Lang = "de",
    ) -> Response:
        file = export_ledger(_require(store, year, month), format, lang)
        return Response(
            content=file.content,
            media_type=file.media_type,
            headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
        )

    @app.get("/api/photos/{photo_id}")
    def get_photo(photo_id: str, store: ArchiveDep) -> FileResponse:
        path = store.photo_path(photo_id)
        if path is None:
            raise HTTPException(404, "Foto nicht gefunden")
        return FileResponse(path)

    # --- Analyse --------------------------------------------------------------------

    @app.get("/api/analytics")
    def analytics(store: ArchiveDep, year: int | None = None) -> Metrics:
        return compute_metrics(store.all(), today=today(), year=year)

    return app


def _require(store: Archive, year: int, month: int) -> LedgerMonth:
    ledger = store.get(year, month)
    if ledger is None:
        raise HTTPException(404, "Buchungsmonat nicht gefunden")
    return ledger
