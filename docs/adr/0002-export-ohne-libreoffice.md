# Export-Dateien werden direkt erzeugt, ohne installiertes LibreOffice

LibreOffice hat zwar eine Schnittstelle (`soffice --headless --convert-to …` und die UNO-API), das würde aber eine LibreOffice-Installation auf dem Server voraussetzen. Stattdessen schreiben wir `.xlsx` (openpyxl), `.ods` (odfpy), `.csv` und `.pdf` (fpdf2) direkt in Python. Excel- und ODS-Dateien enthalten echte SUMME-Formeln, damit spätere Änderungen in der Tabelle mitgerechnet werden.
