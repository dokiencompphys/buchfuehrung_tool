import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { de, type Dictionary } from '@/i18n/de';
import { vi } from '@/i18n/vi';

export type Lang = 'de' | 'vi';

export type Settings = {
  lang: Lang;
  region: string; // Bundesland-Kürzel, z. B. "BY"
  engine: string | null; // null = Standard des Servers
};

const DEFAULTS: Settings = { lang: 'de', region: 'BE', engine: null };
const STORAGE_KEY = 'buchfuehrung.settings.v1';
const DICTIONARIES: Record<Lang, Dictionary> = { de, vi };

type Ctx = {
  settings: Settings;
  update: (patch: Partial<Settings>) => void;
  t: Dictionary;
  /** Platzhalter wie {n} ersetzen */
  fmt: (text: string, params?: Record<string, string | number>) => string;
};

const SettingsContext = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => raw && setSettings({ ...DEFAULTS, ...JSON.parse(raw) }))
      .catch(() => {});
  }, []);

  const update = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  const value = useMemo<Ctx>(
    () => ({
      settings,
      update,
      t: DICTIONARIES[settings.lang],
      fmt: (text, params = {}) =>
        text.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? `{${key}}`)),
    }),
    [settings, update],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Ctx {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings außerhalb von SettingsProvider');
  return ctx;
}
