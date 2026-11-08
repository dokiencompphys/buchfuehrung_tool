# Foto-Prüfung: Backend liefert Fakten, die App prüft live

Beim Foto-Lesen gibt das Backend neben dem Entwurf `PhotoChecks` zurück: was zusätzlich auf dem Foto steht (Anfangssaldo, Saldo je Tag, Summenzeile) und verdächtige Zellen (durchgestrichen, mehrere Zahlen, schlecht lesbar). Übernommen werden diese Werte nicht – Salden werden immer berechnet (ADR 0004). Die App vergleicht sie bei jeder Eingabe mit den Feldern (`app/src/lib/checks.ts`) und listet Abweichungen; korrigiert der Nutzer, verschwindet die Meldung, sonst bestätigt er sie mit „Stimmt so“. Speichern mit offenen Abweichungen fragt nach.

Die Saldo-Prüfung geht abschnittsweise von einem Saldo auf dem Foto zum nächsten. So wird die fehlerhafte Zeile eingegrenzt, statt dass ab dem ersten Fehler alle folgenden Zeilen auffallen.

**Verworfen**: Prüfen nur im Backend (Hinweise beim Lesen). Die Hinweise wären nach jeder Korrektur veraltet gewesen.

**Konsequenz**: Durchgestrichenes wird im Bild erkannt (`ocr/strike.py`), dafür müssen die Box-Koordinaten zum hochgeladenen Bild passen – Seiten-Entzerrung im OCR-Modell ist deshalb aus.
