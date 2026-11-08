// Hält den aktuellen Entwurf zwischen "Foto lesen" und dem Tabellen-Editor.
import { createContext, type ReactNode, useContext, useState } from 'react';

import type { Hint, LedgerMonth } from '@/api/types';

export type Draft = {
  ledger: LedgerMonth;
  hints: Hint[];
  recognizedDays: number | null; // null = nicht vom Foto
  editingExisting: boolean;
};

type Ctx = { draft: Draft | null; setDraft: (d: Draft | null) => void };

const DraftContext = createContext<Ctx | null>(null);

export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<Draft | null>(null);
  return <DraftContext.Provider value={{ draft, setDraft }}>{children}</DraftContext.Provider>;
}

export function useDraft(): Ctx {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error('useDraft außerhalb von DraftProvider');
  return ctx;
}
