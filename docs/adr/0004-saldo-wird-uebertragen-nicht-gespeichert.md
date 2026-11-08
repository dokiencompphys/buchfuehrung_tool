# Der Anfangssaldo wird beim Lesen übertragen, nicht gespeichert

Jeder Buchungsmonat übernimmt als Anfangssaldo den Endsaldo des letzten früheren Monats in der Ablage. Dieser Übertrag wird bei jedem Lesen neu berechnet (`domain/balance.py`) und nie gespeichert. So ziehen alle späteren Monate und der aktuelle Saldo automatisch mit, wenn ein früherer Monat geändert wird, und es gibt keine veralteten Salden in der Datenbank.

Einen Anfangssaldo eintragen kann man **nur im ersten Monat** der Ablage. In allen späteren Monaten gilt immer der Übertrag, auch wenn ein eigener Wert mitgeschickt wird (die API verwirft ihn). Die Kette Endsaldo → Anfangssaldo ist damit lückenlos.

**Geändert**: Anfangs konnte ein manueller Anfangssaldo die Kette unterbrechen (z. B. nach einem Kassensturz). Der Nutzer wollte ausdrücklich durchgehende Konsistenz; eine Kassendifferenz wird jetzt als Einnahme oder Ausgabe mit Grund gebucht.

**Konsequenz**: Wird ein Monat vor dem bisher ersten nachgetragen, wird dieser zum ersten Monat und sein Startwert gilt; der Startwert des bisherigen ersten Monats wird ignoriert. Fehlende Monate werden übersprungen: Der Übertrag kommt dann vom letzten vorhandenen Monat.
