# OCR-Engines liefern nur Textboxen, die Tabellenlogik liegt bei uns

Surya, PaddleOCR und künftige Modelle haben jeweils eigene Tabellen-Funktionen mit sehr unterschiedlicher Ausgabe. Damit Modelle austauschbar bleiben, implementiert jeder Adapter nur `recognize(image) -> list[TextBox]`; Zeilen gruppieren, Spalten über die Kopfzeile zuordnen, Beträge parsen und den Monat erkennen passiert einmal in `ocr/reader.py`. So ist ein neues Modell ein ~40-Zeilen-Adapter, und die Lese-Logik ist ohne Modell (über die Fake-Engine) testbar.

**Konsequenz**: Modell-eigene Tabellenerkennung (z. B. Surya `TableRecPredictor`) wird bewusst nicht genutzt. Falls die einfache Zeilen-/Spaltenlogik bei echten Fotos nicht reicht, ist das der Ort für eine neue Entscheidung.
