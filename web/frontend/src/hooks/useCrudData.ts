import { useState, useEffect, useCallback } from 'react';
import { normalizeToArray } from '../api/client';

const API_KEY = 'test-api-key-12345';
const DEFAULT_TIMEOUT = 8000;

async function fetchWithTimeout(url: string, options?: RequestInit, timeout = DEFAULT_TIMEOUT): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export function useCrudData<T>(
  url: string,
  mapResponse: (data: any) => { items: T[]; total: number },
  fallbackData: T[],
  deps: any[] = [],
) {
  const [items, setItems] = useState<T[]>(fallbackData);
  const [total, setTotal] = useState(fallbackData.length);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(url, { headers: { 'X-API-Key': API_KEY } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      let mapped = mapResponse(data);
      // Guard against a mapper that trusted the envelope shape: if the backend
      // returned `{items:[]}`/`{data:[]}` but the mapper looked for a bare array
      // (or vice versa) it yields no rows and the page renders an empty table.
      if (!Array.isArray(mapped?.items) || mapped.items.length === 0) {
        const recovered = normalizeToArray<T>(data);
        if (recovered.length > 0) {
          mapped = { ...mapped, items: recovered, total: mapped?.total ?? recovered.length };
        }
      }
      if (mapped.items.length > 0) {
        setItems(mapped.items);
        setTotal(mapped.total);
        setUsingFallback(false);
      } else {
        setItems(fallbackData);
        setTotal(fallbackData.length);
        setUsingFallback(true);
      }
    } catch (err) {
      setItems(fallbackData);
      setTotal(fallbackData.length);
      setUsingFallback(true);
      setError(err instanceof Error ? err.message : 'Failed to fetch');
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchData(); }, [fetchData]);

  return { items, total, loading, error, usingFallback, refetch: fetchData, setItems, setError };
}
