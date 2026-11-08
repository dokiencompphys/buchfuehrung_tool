// Spiegelt die JSON-Form des Backends. Beträge kommen als Strings ("12.50"), nie als float.

export type Amount = string | null;

export type ClosedDay = { kind: 'sunday' | 'holiday'; name: string };

export type DayEntry = {
  day: string; // ISO-Datum "2026-11-02"
  income: Amount;
  expense: Amount;
  closed: ClosedDay | null;
  reason: string; // Grund
};

export type Totals = {
  income: string;
  expense: string;
  result: string; // Überschuss = Einnahmen − Ausgaben
  opening: string; // Anfangssaldo
  closing: string; // Endsaldo
};

/** Übertrag: Endsaldo des letzten früheren Monats in der Ablage. */
export type CarryOver = { amount: string; year: number; month: number };

export type LedgerMonth = {
  year: number;
  month: number;
  region: string;
  source: 'manual' | 'photo';
  photo_id: string | null;
  opening_balance: Amount; // manuell gesetzt; null = Übertrag verwenden
  carry_over: CarryOver | null; // vom Server gesetzt
  entries: DayEntry[];
  totals?: Totals;
};

export type Hint = { code: string; params: Record<string, string> };

export type SuspectCell = {
  day: number;
  field: 'income' | 'expense';
  reason: 'struck' | 'several' | 'unsure';
  read: string[];
  struck: string[];
};

/** Was auf dem Foto zum Gegenprüfen stand (Beträge als Strings wie überall). */
export type PhotoChecks = {
  opening: string | null;
  balances: Record<string, string>;
  total_income: string | null;
  total_expense: string | null;
  closing: string | null;
  suspects: SuspectCell[];
};

export type PhotoReading = { ledger: LedgerMonth; hints: Hint[]; recognized_days: number; checks: PhotoChecks };

export type Region = { code: string; name: string };

export type EngineInfo = { id: string; name: string; installed: boolean };

export type ArchiveItem = {
  year: number;
  month: number;
  region: string;
  source: 'manual' | 'photo';
  has_photo: boolean;
  opening_is_manual: boolean;
  totals: Totals;
  created_at: string;
  updated_at: string;
};

export type MonthPoint = {
  year: number;
  month: number;
  income: string;
  expense: string;
  result: string;
  closing: string;
};

export type Metrics = {
  year: number;
  months_recorded: number;
  income_ytd: string;
  expense_ytd: string;
  result_ytd: string;
  current_balance: string | null;
  current_balance_month: MonthPoint | null;
  income_previous_year_same_period: string | null;
  avg_income_per_month: string | null;
  avg_income_per_open_day: string | null;
  best_month: MonthPoint | null;
  worst_month: MonthPoint | null;
  latest: {
    current: MonthPoint;
    previous: MonthPoint | null;
    income_change: string | null;
    income_change_pct: string | null;
  } | null;
  same_month_last_year: MonthPoint | null;
  series: MonthPoint[];
};

export type ExportFormat = 'xlsx' | 'ods' | 'csv' | 'pdf';
