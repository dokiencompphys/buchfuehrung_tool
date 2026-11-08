import { Platform } from 'react-native';

import type {
  ArchiveItem,
  CarryOver,
  EngineInfo,
  ExportFormat,
  LedgerMonth,
  Metrics,
  PhotoReading,
  Region,
} from './types';

// Adresse des Backends. Auf dem Handy: IP des PCs im WLAN, z. B. http://192.168.178.20:8000
// Die gebaute Web-App (Desktop-Start) wird vom Backend selbst ausgeliefert → gleiche Adresse.
const SAME_ORIGIN = Platform.OS === 'web' && !__DEV__;
export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? (SAME_ORIGIN ? '' : 'http://localhost:8000')
).replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, 'offline');
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export type PickedPhoto = { uri: string; name: string; mimeType: string; webFile?: Blob };

export const api = {
  info: () => request<{ data_dir: string; months_stored: number }>('/api/info'),
  regions: () => request<Region[]>('/api/regions'),
  engines: () => request<{ default: string; engines: EngineInfo[] }>('/api/ocr/engines'),

  blankDraft: (year: number, month: number, region: string) =>
    request<LedgerMonth>(`/api/drafts/blank?year=${year}&month=${month}&region=${region}`),
  refreshDraft: (ledger: LedgerMonth) => request<LedgerMonth>('/api/drafts/refresh', json('POST', ledger)),
  photoDraft: (photo: PickedPhoto, region: string, engine?: string) => {
    const form = new FormData();
    if (Platform.OS === 'web' && photo.webFile) {
      form.append('photo', photo.webFile, photo.name);
    } else {
      // React Native akzeptiert dieses Objekt als Datei-Teil
      form.append('photo', { uri: photo.uri, name: photo.name, type: photo.mimeType } as unknown as Blob);
    }
    form.append('region', region);
    if (engine) form.append('engine', engine);
    return request<PhotoReading>('/api/drafts/photo', { method: 'POST', body: form });
  },

  months: () => request<ArchiveItem[]>('/api/months'),
  month: (year: number, month: number) => request<LedgerMonth>(`/api/months/${year}/${month}`),
  /** Ein vorhandener Monat wird nur mit `replace` ersetzt, sonst ApiError 409. */
  saveMonth: (ledger: LedgerMonth, { replace = false } = {}) =>
    request<{ ledger: LedgerMonth; created: boolean }>(
      `/api/months/${ledger.year}/${ledger.month}${replace ? '?replace=true' : ''}`,
      json('PUT', ledger),
    ),
  deleteMonth: (year: number, month: number) =>
    request<void>(`/api/months/${year}/${month}`, { method: 'DELETE' }),
  /** Der abgelegte Monat oder null, wenn es für Monat/Jahr noch keinen gibt. */
  stored: async (year: number, month: number): Promise<LedgerMonth | null> => {
    try {
      return await api.month(year, month);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },

  exportUrl: (year: number, month: number, format: ExportFormat, lang: string) =>
    `${API_URL}/api/months/${year}/${month}/export?format=${format}&lang=${lang}`,
  photoUrl: (photoId: string) => `${API_URL}/api/photos/${photoId}`,

  balance: () => request<CarryOver | null>('/api/balance'),

  analytics: (year?: number) => request<Metrics>(`/api/analytics${year ? `?year=${year}` : ''}`),
};
