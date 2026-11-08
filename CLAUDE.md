# Buchführung – Hinweise für Agenten

Monats-Buchführung für einen älteren Nutzer: große Schrift, große Tippflächen, klare Sprache. UI-Texte immer in **beiden** Sprachen pflegen (`app/src/i18n/de.ts` und `vi.ts`; TypeScript erzwingt gleiche Schlüssel).

## Aufbau

- `backend/src/buchfuehrung/` – jedes Paket ist ein Modul mit kleiner öffentlicher Schnittstelle:
  - `domain/` – `LedgerMonth`, `DayEntry`; `factory.blank_month()` erzeugt Monate mit Ruhetagen
  - `calendars/` – `closed_days(year, month, region)`, `regions()`
  - `ocr/` – `reader.read_photo(image, engine, region, fallback)` → Entwurf + `PhotoChecks` (Saldo/Summen vom Foto, verdächtige Zellen); Engines hinter `engine.OcrEngine` (Seam mit Surya, Paddle, Fake); `strike.py` erkennt Durchgestrichenes im Bild
  - `photos.py` – `prepare_photo(raw)`: jedes Upload (auch iPhone-HEIC) → aufrechtes RGB-JPEG, vor OCR und Ablage
  - `export/` – `export_ledger(ledger, fmt, lang)`
  - `storage/` – `Archive` (SQLite + Fotos); `save(…, replace=False)` ersetzt einen vorhandenen Monat nur ausdrücklich
  - `analytics/` – `compute_metrics(ledgers, today)`
  - `api/app.py` – dünne HTTP-Schicht, `create_app(settings, today=…)`
- `app/src/app/` – Bildschirme (Expo Router); alles andere außerhalb von `src/app/`.
- `app/src/lib/checks.ts` – Live-Prüfung des Foto-Entwurfs (ADR 0005); `app/src/editor/` – Tabelle (drei Layouts nach Breite) und Prüfliste.
- `desktop/windows/` – Start per Doppelklick: `install.ps1` baut die App (`npm run build:web` → `app/dist`) und legt die Verknüpfung an; `Buchfuehrung.ps1` startet das Backend mit `BUCH_WEB_DIR` und öffnet ein Edge-App-Fenster. Nach App-Änderungen `install.ps1` erneut ausführen.
- Die App hat eigene Hinweise in `app/AGENTS.md` (Expo-Doku der passenden SDK-Version lesen, Pakete mit `npx expo install`).

## Regeln

- Begriffe aus `GLOSSARY.md` verwenden. Entscheidungen in `docs/adr/` respektieren.
- Geld nie als float: Backend `Decimal`, JSON-String, App rechnet in Cent (ADR 0003).
- Tests an den öffentlichen Schnittstellen der Module, nicht an Interna. Erwartungswerte unabhängig nachrechnen (z. B. Feiertage aus dem Kalender, nicht aus dem Code).
- Vor „fertig“: `cd backend && uv run pytest && uv run ruff check src tests` sowie `cd app && npm test && npm run typecheck && npx expo lint`.

## Agent skills

Aus [mattpocock/skills](https://github.com/mattpocock/skills) (MIT) übernommen, in `.claude/skills/`:

- `codebase-design` – Vokabular für tiefe Module, Seams, Adapter
- `domain-modeling` – `GLOSSARY.md` und ADRs pflegen (Format: kurz, nur bei echten Trade-offs)
- `tdd` – Red → Green an vereinbarten Seams
- `diagnosing-bugs` – strukturierte Fehlersuche
- `grill-me` / `grilling` – Anforderungen durch gezielte Fragen schärfen
