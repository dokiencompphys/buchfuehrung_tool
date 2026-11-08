# Beträge sind Decimal im Backend und Strings im JSON

Geldbeträge laufen nie als Fließkommazahl durch das System: im Backend `Decimal` mit zwei Nachkommastellen, im JSON als String (`"1234.50"`), in der App als Cent-Ganzzahl zum Rechnen. Das verhindert Rundungsfehler wie `0,1 + 0,2 = 0,30000000000000004` in Summen. Summen werden immer berechnet und nie gespeichert.
