// Prüft einen vom Foto gelesenen Monat gegen das, was zusätzlich auf dem Foto steht
// (Anfangssaldo, Saldo pro Tag, Summenzeile) und meldet verdächtige Zellen.
// Läuft bei jeder Eingabe neu: Korrigiert der Nutzer einen Betrag, verschwindet die Meldung.
// Alle Beträge in Cent.

export type Field = 'income' | 'expense';
export type SuspectReason = 'struck' | 'several' | 'unsure';

export type PhotoFacts = {
  opening: number | null;
  balances: Record<number, number>; // Tag des Monats → Saldo auf dem Foto
  totalIncome: number | null;
  totalExpense: number | null;
  closing: number | null;
  suspects: { day: number; field: Field; reason: SuspectReason; read: number[]; struck: number[] }[];
};

export type DayValues = { day: number; income: number; expense: number };

export type Issue =
  | { id: string; kind: 'opening'; photo: number; used: number }
  | { id: string; kind: 'balance'; from: number; to: number; photo: number; computed: number }
  | { id: string; kind: 'closing'; photo: number; computed: number }
  | { id: string; kind: 'total'; field: Field; photo: number; computed: number }
  | { id: string; kind: 'suspect'; day: number; field: Field; reason: SuspectReason; read: number[]; struck: number[] };

/**
 * Abweichungen zwischen Foto und eingegebenen Werten.
 *
 * Saldo-Prüfung abschnittsweise: Von einem Saldo auf dem Foto zum nächsten müssen die
 * Beträge dazwischen genau aufgehen. So wird die fehlerhafte Zeile eingegrenzt, statt
 * dass ab dem ersten Fehler alle folgenden Zeilen rot werden.
 */
export function findIssues(photo: PhotoFacts, days: DayValues[], openingCents: number): Issue[] {
  const issues: Issue[] = [];

  if (photo.opening !== null && photo.opening !== openingCents) {
    issues.push({ id: 'opening', kind: 'opening', photo: photo.opening, used: openingCents });
  }

  // Abschnitt beginnt beim Anfangssaldo des Fotos (falls vorhanden), sonst beim verwendeten
  let anchor = photo.opening ?? openingCents;
  let sum = 0;
  let from = days[0]?.day ?? 1;
  for (const d of days) {
    sum += d.income - d.expense;
    const written = photo.balances[d.day];
    if (written === undefined) continue;
    if (anchor + sum !== written) {
      issues.push({ id: `balance:${d.day}`, kind: 'balance', from, to: d.day, photo: written, computed: anchor + sum });
    }
    anchor = written;
    sum = 0;
    from = d.day + 1;
  }
  if (photo.closing !== null && anchor + sum !== photo.closing) {
    issues.push({ id: 'closing', kind: 'closing', photo: photo.closing, computed: anchor + sum });
  }

  const totals: Record<Field, number> = {
    income: days.reduce((s, d) => s + d.income, 0),
    expense: days.reduce((s, d) => s + d.expense, 0),
  };
  for (const [field, written] of [
    ['income', photo.totalIncome],
    ['expense', photo.totalExpense],
  ] as const) {
    if (written !== null && written !== totals[field]) {
      issues.push({ id: `total:${field}`, kind: 'total', field, photo: written, computed: totals[field] });
    }
  }

  for (const s of photo.suspects) {
    issues.push({ id: `suspect:${s.day}:${s.field}`, kind: 'suspect', ...s });
  }
  return issues;
}

/** Tage, die zu einer Meldung gehören (zum Hervorheben in der Tabelle). */
export function daysOf(issue: Issue): number[] {
  switch (issue.kind) {
    case 'balance':
      return Array.from({ length: issue.to - issue.from + 1 }, (_, i) => issue.from + i);
    case 'suspect':
      return [issue.day];
    default:
      return [];
  }
}
