import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '@/api/client';

export type AsyncState<T> = {
  data: T | null;
  error: 'offline' | string | null;
  loading: boolean;
  reload: () => void;
};

type Result<T> = { key: string; data: T | null; error: string | null };

/**
 * Lädt Daten, wenn ein Bildschirm sichtbar wird (auch beim Zurückkehren) und
 * wenn sich `deps` ändern. `reload` lädt sofort neu.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [tick, setTick] = useState(0);
  const [result, setResult] = useState<Result<T>>({ key: '', data: null, error: null });
  const key = JSON.stringify([...deps, tick]);

  useEffect(() => {
    let alive = true;
    fn()
      .then((data) => alive && setResult({ key, data, error: null }))
      .catch((e) =>
        alive &&
        setResult((prev) => ({
          key,
          data: prev.data,
          error: e instanceof ApiError && e.status === 0 ? 'offline' : String(e.message),
        })),
      );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  // Erstes Fokussieren überspringen – das lädt schon der Effekt oben
  const [focusedOnce, setFocusedOnce] = useState(false);
  useFocusEffect(
    useCallback(() => {
      if (focusedOnce) reload();
      else setFocusedOnce(true);
    }, [focusedOnce, reload]),
  );

  return { data: result.data, error: result.error, loading: result.key !== key, reload };
}
