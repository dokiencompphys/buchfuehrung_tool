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
from buchfuehrung.domain.ledger import CarryOver, LedgerMonth
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
from buchfuehrung.photos import UnreadablePhoto, prepare_photo
from buchfuehrung.storage.archive import AlreadyStored, Archive, ArchiveItem

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

    @app.exception_handler(AlreadyStored)
    async def _already_stored(_, exc: AlreadyStored):  # type: ignore[no-untyped-def]
        from fastapi.responses import JSONResponse

        # 409: Die App fragt nach und sendet dann mit ?replace=true erneut
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "year": exc.year, "month": exc.month},
        )

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
        store: ArchiveDep,
        year: Annotated[int, Query(ge=2000, le=2100)],
        month: Annotated[int, Query(ge=1, le=12)],
        region: str,
    ) -> LedgerMonth:
        return _with_carry_over(store, blank_month(year, month, region))

    @app.post("/api/drafts/refresh")
    def refresh_draft(ledger: LedgerMonth, store: ArchiveDep) -> LedgerMonth:
        """Ruhetage und Übertrag neu setzen, z. B. nachdem das Bundesland geändert wurde."""
        return _with_carry_over(store, refresh_closed_days(ledger))

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
        try:
            image = prepare_photo(content)  # z. B. iPhone-HEIC → aufrechtes JPEG
        except UnreadablePhoto as exc:
            raise HTTPException(
                415, "Bildformat nicht erkannt. Bitte ein Foto (JPG, PNG oder HEIC) wählen."
            ) from exc
        reading = read_photo(image, ocr, region, fallback=today())
        photo_id = store.store_photo(image, ".jpg")
        ledger = _with_carry_over(store, reading.ledger)
        return reading.model_copy(
            update={"ledger": ledger.model_copy(update={"photo_id": photo_id})}
        )

    # --- Ablage ---------------------------------------------------------------------

    @app.get("/api/months")
    def list_months(store: ArchiveDep) -> list[ArchiveItem]:
        return store.list_items()

    @app.get("/api/months/{year}/{month}")
    def get_month(year: int, month: int, store: ArchiveDep) -> LedgerMonth:
        return _require(store, year, month)

    @app.put("/api/months/{year}/{month}")
    def save_month(
        year: int, month: int, ledger: LedgerMonth, store: ArchiveDep, replace: bool = False
    ) -> SaveResponse:
        """Legt einen Monat ab. Einen vorhandenen ersetzt nur `?replace=true`, sonst 409."""
        if (ledger.year, ledger.month) != (year, month):
            raise HTTPException(422, "Monat/Jahr in Adresse und Daten stimmen nicht überein")
        if store.carry_over_for(year, month) is not None:
            # Nicht der erste Monat: Anfangssaldo ist der Übertrag, ein eigener Wert gilt nicht
            ledger = ledger.model_copy(update={"opening_balance": None})
        saved, created = store.save(ledger, replace=replace)
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

    @app.get("/api/balance")
    def current_balance(store: ArchiveDep) -> CarryOver | None:
        """Aktueller Saldo (Endsaldo des neuesten Monats) oder null, wenn die Ablage leer ist."""
        return store.current_balance()

    # --- Analyse --------------------------------------------------------------------

    @app.get("/api/analytics")
    def analytics(store: ArchiveDep, year: int | None = None) -> Metrics:
        return compute_metrics(store.all(), today=today(), year=year)

    # Zuletzt, damit /api/... immer Vorrang hat
    if settings.web_dir is not None:
        _serve_web_app(app, settings.web_dir)

    return app


def _serve_web_app(app: FastAPI, web_dir: Path) -> None:
    """Liefert die gebaute Web-App aus. Unbekannte Pfade (z. B. /editor) bekommen
    index.html, weil die App ihre Bildschirme selbst auswählt."""
    root = web_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"Keine gebaute App in {root} – zuerst `npm run build:web`")

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Nicht gefunden")
        file = (root / path).resolve()
        if file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        return FileResponse(index)


def _with_carry_over(store: Archive, ledger: LedgerMonth) -> LedgerMonth:
    carry = store.carry_over_for(ledger.year, ledger.month)
    return ledger.model_copy(update={"carry_over": carry})


def _require(store: Archive, year: int, month: int) -> LedgerMonth:
    ledger = store.get(year, month)
    if ledger is None:
        raise HTTPException(404, "Buchungsmonat nicht gefunden")
    return ledger
