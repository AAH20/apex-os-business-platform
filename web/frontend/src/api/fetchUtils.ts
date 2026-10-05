// Centralized fetch utility with retry logic, X-API-Key, timeout, and error handling.
// All pages should use this instead of raw fetch() to avoid "Failed to fetch" errors.

const API_KEY = 'test-api-key-12345';
const DEFAULT_TIMEOUT = 10000;
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000;

export class FetchError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.name = 'FetchError';
    this.status = status;
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout = DEFAULT_TIMEOUT,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        ...options.headers,
      },
    });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch with automatic retry on network errors and 5xx responses.
 * Returns parsed JSON or throws FetchError with user-friendly message.
 */
export async function fetchWithRetry<T = unknown>(
  url: string,
  options: RequestInit = {},
  retries = MAX_RETRIES,
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetchWithTimeout(url, options);

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        let message = `Server error (${res.status})`;
        try {
          const json = JSON.parse(text);
          if (json.detail) message = json.detail;
          else if (json.message) message = json.message;
        } catch { /* ignore */ }
        throw new FetchError(message, res.status);
      }

      const text = await res.text();
      if (!text) return undefined as T;
      return JSON.parse(text) as T;
    } catch (err) {
      if (err instanceof FetchError && err.status < 500 && err.status > 0) {
        throw err; // Don't retry client errors (4xx)
      }
      lastError = err instanceof Error ? err : new Error('Unknown error');
      if (attempt < retries) {
        await delay(RETRY_DELAY * (attempt + 1));
      }
    }
  }

  if (lastError) {
    if (lastError.name === 'AbortError') {
      throw new FetchError('Request timed out — server may be unreachable', 0);
    }
    throw new FetchError(
      lastError.message || 'Network error — check your connection',
      0,
    );
  }
  throw new FetchError('Request failed after retries', 0);
}

/**
 * Simple fetch with X-API-Key and timeout, no retry.
 * Throws FetchError with user-friendly message.
 */
export async function apiFetch<T = unknown>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  return fetchWithRetry<T>(url, options, 0);
}

export { API_KEY };
