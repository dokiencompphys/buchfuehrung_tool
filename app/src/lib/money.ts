// Beträge: Eingabe im deutschen Format ("1.234,50"), intern als Cent-Ganzzahl, zum Backend als "1234.50".

/**
 * Nutzereingabe → API-String ("12.50") oder null bei leerem Feld. undefined = ungültig.
 * Mit `allowNegative` darf ein Minus vorne stehen (z. B. für den Anfangssaldo).
 */
export function parseInput(text: string, { allowNegative = false } = {}): string | null | undefined {
  let raw = text.replace(/[€\s]/g, '');
  let negative = false;
  if (allowNegative && /^[-−]/.test(raw)) {
    negative = true;
    raw = raw.slice(1);
  }
  raw = raw.replace(/[,.]?-+$/, ''); // '12,-' → '12'
  if (raw === '') return negative ? undefined : null;
  if (!/^[\d.,]+$/.test(raw)) return undefined;
  let normalized: string;
  if (raw.includes(',')) normalized = raw.replace(/\./g, '').replace(',', '.');
  else if ((raw.match(/\./g) ?? []).length === 1 && raw.split('.')[1].length !== 3) normalized = raw;
  else normalized = raw.replace(/\./g, '');
  if ((normalized.match(/\./g) ?? []).length > 1) return undefined;
  const value = Number(normalized);
  if (!Number.isFinite(value) || value < 0) return undefined;
  const fixed = (Math.round(value * 100) / 100).toFixed(2);
  return negative && Number(fixed) !== 0 ? `-${fixed}` : fixed;
}

/** API-String → Cent. */
export function toCents(amount: string | null | undefined): number {
  if (!amount) return 0;
  const [whole, frac = ''] = amount.split('.');
  const sign = whole.startsWith('-') ? -1 : 1;
  return sign * (Math.abs(Number(whole)) * 100 + Number(frac.padEnd(2, '0').slice(0, 2)));
}

/** Cent → "1.234,50" */
export function formatCents(cents: number): string {
  const sign = cents < 0 ? '−' : '';
  const abs = Math.abs(cents);
  const euros = Math.floor(abs / 100)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${sign}${euros},${(abs % 100).toString().padStart(2, '0')}`;
}

/** API-String → Anzeige im Eingabefeld ("" für leer). */
export function toInput(amount: string | null): string {
  return amount === null ? '' : formatCents(toCents(amount)).replace('−', '-');
}

export function formatEuro(amount: string | number | null | undefined): string {
  if (amount === null || amount === undefined) return '–';
  const cents = typeof amount === 'number' ? amount : toCents(amount);
  return `${formatCents(cents)} €`;
}

/** Saldo nach jedem Tag in Cent: Anfangssaldo + Einnahmen − Ausgaben, fortlaufend. */
export function runningBalances(openingCents: number, days: [string | null, string | null][]): number[] {
  let balance = openingCents;
  return days.map(([income, expense]) => {
    balance += toCents(income) - toCents(expense);
    return balance;
  });
}

export function sumCents(values: (string | null)[]): number {
  return values.reduce((acc, v) => acc + toCents(v), 0);
}
