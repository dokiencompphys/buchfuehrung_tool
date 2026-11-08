# Glossar

**Buchungsmonat** (_LedgerMonth_): Die Buchführung eines Kalendermonats. Hat für jeden Tag genau eine Tageszeile. Pro Monat/Jahr gibt es höchstens einen.
_Vermeiden_: Blatt, Liste, Datei.

**Tageszeile** (_DayEntry_): Ein Tag im Buchungsmonat mit Einnahme, Ausgabe und Grund. Leer ist erlaubt.

**Einnahmen / Umsatz** (_income_): Geld, das an einem Tag hereinkam. „Umsatz“ meint in der Analyse immer die Summe der Einnahmen.

**Ausgaben** (_expense_): Geld, das an einem Tag ausgegeben wurde.

**Grund** (_reason_): Freitext pro Tageszeile: wofür das Geld ausgegeben (oder woher es eingenommen) wurde.
_Vermeiden_: Bemerkung, Notiz.

**Saldo** (_balance_): Der Kassenstand – wie viel Geld zu einem Zeitpunkt da ist. Der Saldo einer Tageszeile ist der Kassenstand am Ende dieses Tages. Kann negativ sein.
_Vermeiden_: „Saldo“ für Einnahmen minus Ausgaben – das ist der Überschuss.

**Anfangssaldo** (_opening_): Saldo am 1. eines Buchungsmonats, vor allen Buchungen. Entweder der Übertrag oder manuell eingetragen.

**Endsaldo** (_closing_): Saldo am Ende des Buchungsmonats = Anfangssaldo + Einnahmen − Ausgaben.

**Übertrag** (_carry over_): Endsaldo des letzten früheren Buchungsmonats in der Ablage. Wird zum Anfangssaldo, solange keiner manuell eingetragen ist.

**Aktueller Saldo**: Endsaldo des neuesten Buchungsmonats in der Ablage.

**Überschuss** (_result_): Einnahmen minus Ausgaben eines Zeitraums. Ein negativer Überschuss ist ein Fehlbetrag.
_Vermeiden_: Gewinn, Saldo.

**Ruhetag** (_ClosedDay_): Sonntag oder gesetzlicher Feiertag im gewählten Bundesland. Wird grau angezeigt, bleibt aber editierbar.

**Bundesland** (_region_): Bestimmt, welche Feiertage gelten. „DE“ = nur bundesweite Feiertage.

**Entwurf** (_draft_): Ein Buchungsmonat, der noch nicht in der Ablage liegt – leer erzeugt oder aus einem Foto gelesen.

**Foto-Lesung** (_PhotoReading_): Das Ergebnis der Texterkennung: ein Entwurf plus Hinweise. Immer nur ein Vorschlag.

**Hinweis** (_Hint_): Eine Meldung zur Foto-Lesung (z. B. „Summe weicht ab“), die der Nutzer prüfen soll.

**Ablage** (_Archive_): Alle erstellten Buchungsmonate samt Originalfotos.

**OCR-Engine**: Ein austauschbares Texterkennungs-Modell (Surya, PaddleOCR, Demo), das nur Textboxen liefert.
