import { useCallback, useEffect, useState } from 'react';

/**
 * Завантажує дані з API й повертає стан запиту.
 *
 * @param {() => Promise<any>} load функція запиту; перезапускається при зміні `deps`
 * @param {any[]} deps залежності, за якими запит повторюється
 * @returns {{data: any, error: Error|null, loading: boolean, reload: () => void}}
 */
export function useApi(load, deps) {
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify([...deps, attempt]);
  const [result, setResult] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    let active = true;
    load()
      .then((data) => active && setResult({ key, data, error: null }))
      .catch((error) => active && setResult({ key, data: null, error }));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);
  const loading = result.key !== key;
  return { data: result.data, error: loading ? null : result.error, loading, reload };
}
