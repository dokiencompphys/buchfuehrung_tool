// Spiegelt die JSON-Form des Backends. Beträge kommen als Strings ("12.50"), nie als float.

export type Amount = string | null;

export type ClosedDay = { kind: 'sunday' | 'holiday'; name: string };

export type DayEntry = {
  day: string; // ISO-Datum "2026-11-02"
  income: Amount;
  expense: Amount;
  closed: ClosedDay | null;
  note: string;
};

export type Totals = { income: string; expense: string; balance: string };

export type LedgerMonth = {
  year: number;
  month: number;
  region: string;
  source: 'manual' | 'photo';
  photo_id: string | null;
  entries: DayEntry[];
  totals?: Totals;
};

export type Hint = { code: string; params: Record<string, string> };

export type PhotoReading = { ledger: LedgerMonth; hints: Hint[]; recognized_days: number };

export type Region = { code: string; name: string };

export type EngineInfo = { id: string; name: string; installed: boolean };

export type ArchiveItem = {
  year: number;
  month: number;
  region: string;
  source: 'manual' | 'photo';
  has_photo: boolean;
  totals: Totals;
  created_at: string;
  updated_at: string;
};

export type MonthPoint = {
  year: number;
  month: number;
  income: string;
  expense: string;
  balance: string;
};

export type Metrics = {
  year: number;
  months_recorded: number;
  income_ytd: string;
  expense_ytd: string;
  balance_ytd: string;
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
