# Buchführung

Monats-Buchführung (Einnahmen/Ausgaben pro Tag) per Foto oder von Hand erfassen, mit Feiertagen je Bundesland, Export nach Excel/LibreOffice/CSV/PDF, Ablage und Analyse. Sprache: Deutsch oder Vietnamesisch.

```
app/       Expo (React Native) – läuft auf Handy, Tablet und im Browser
backend/   Python/FastAPI – Feiertage, OCR, Export, Ablage (SQLite), Kennzahlen
docs/adr/  Architektur-Entscheidungen
GLOSSARY.md  Fachbegriffe
```

## Starten

Voraussetzungen: [uv](https://docs.astral.sh/uv/) und Node.js.

**Backend** (Terminal 1):

```bash
cd backend
uv sync --extra paddle   # ohne --extra wird PaddleOCR wieder entfernt
uv run uvicorn buchfuehrung.main:app --host 0.0.0.0 --port 8000
```

**App** (Terminal 2):

```bash
cd app
npm install
npm run web
```

Im Browser öffnet sich `http://localhost:8081`. Für das Handy die App **Expo Go** installieren, `npx expo start` ausführen und den QR-Code scannen. Dann muss die App das Backend im WLAN finden – vorher setzen:

```bash
EXPO_PUBLIC_API_URL=http://<IP-des-PCs>:8000 npx expo start
```

## Texterkennung (OCR)

Ohne installiertes Modell nutzt das Backend eine **Demo-Engine**, damit der Foto-Ablauf ausprobiert werden kann. Echte Modelle sind optional:

```bash
cd backend
uv sync --extra surya     # Surya OCR
uv sync --extra paddle    # PaddleOCR
```

PaddleOCR (~800 MB Python-Pakete) lädt beim ersten Foto rund 180 MB Modelle nach `~/.paddlex` und braucht auf der CPU etwa 10–15 s pro Foto. `uv sync` ohne `--extra` deinstalliert ein Modell wieder.

Die Engine wählt man in der App unter ⚙ Einstellungen oder per `BUCH_OCR_ENGINE=surya|paddle|fake|auto`. Ein neues Modell = ein Adapter in `backend/src/buchfuehrung/ocr/engines/` plus ein Eintrag in `ocr/registry.py` (siehe ADR 0001).

## Einstellungen (Backend, Umgebungsvariablen)

| Variable | Standard | Bedeutung |
|---|---|---|
| `BUCH_DATA_DIR` | `backend/data` | Ablageort für Datenbank und Fotos |
| `BUCH_OCR_ENGINE` | `auto` | Erstes installiertes Modell, sonst Demo |
| `BUCH_CORS_ORIGINS` | `*` | Erlaubte App-Adressen |
| `BUCH_PDF_FONT` | Arial/DejaVu | Unicode-Schrift für PDFs (Vietnamesisch) |

## Tests

```bash
cd backend && uv run pytest && uv run ruff check src tests
cd app && npm test && npm run typecheck && npx expo lint
```
