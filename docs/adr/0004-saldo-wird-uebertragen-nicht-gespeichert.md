# Der Anfangssaldo wird beim Lesen übertragen, nicht gespeichert

Jeder Buchungsmonat übernimmt als Anfangssaldo den Endsaldo des letzten früheren Monats in der Ablage. Dieser Übertrag wird bei jedem Lesen neu berechnet (`domain/balance.py`) und nie gespeichert. Gespeichert wird nur ein manuell eingetragener Anfangssaldo – beim ersten Monat oder als Korrektur nach einem Kassensturz. So ziehen alle späteren Monate und der aktuelle Saldo automatisch mit, wenn ein früherer Monat geändert wird, und es gibt keine veralteten Salden in der Datenbank.

**Konsequenz**: Ein manueller Anfangssaldo unterbricht die Kette bewusst. Ändert man danach einen früheren Monat, ändert sich dieser Monat nicht mit. Fehlende Monate werden übersprungen: Der Übertrag kommt dann vom letzten vorhandenen Monat.
