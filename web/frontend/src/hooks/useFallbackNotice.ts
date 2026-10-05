import { useState, useCallback, useRef } from 'react';

const FALLBACK_NOTICE = 'Showing bundled sample data — could not reach the API.';

export interface FallbackNotice {
  /** Message to render, or `null` when nothing should be shown. */
  notice: string | null;
  /** True while fallback rows are displayed (suppresses any visible banner). */
  usingFallback: boolean;
  /**
   * Call from a fetch failure. Silent on the first (automatic) failure; only
   * starts showing a notice after the user has explicitly retried and that retry
   * has also failed `retriesBeforeNotice` times in a row.
   */
  noteFailure: (err?: unknown) => void;
  /** Call when a fetch succeeds — clears any pending notice/failure count. */
  noteSuccess: () => void;
  /** True when a click on the strip's "Retry" should re-trigger the fetch. */
  canRetry: boolean;
  /** Mark that the user explicitly asked to retry, then re-run the fetch. */
  requestRetry: () => void;
  /** Hide a visible notice without clearing the fallback state. */
  dismissNotice: () => void;
}

export interface FallbackNoticeOptions {
  message?: string;
  /** Consecutive explicit-retry failures required before showing the notice. */
  retriesBeforeNotice?: number;
}

/**
 * Silent-fallback controller.
 *
 * A list that falls back to bundled records on a failed fetch is still a working
 * page, so it must not announce itself on every load: a red "API unavailable —
 * showing sample data" banner on all six CRUD screens made the app look broken.
 *
 * Behavior: the first automatic failure sets `usingFallback` and renders nothing.
 * The notice appears only once the user has clicked "Retry" and that retry has
 * itself failed twice — at which point the failure is persistent and worth
 * surfacing. Any success clears the state.
 */
export function useFallbackNotice(options: FallbackNoticeOptions = {}): FallbackNotice {
  const { message = FALLBACK_NOTICE, retriesBeforeNotice = 2 } = options;

  const [usingFallback, setUsingFallback] = useState(false);
  const [consecutiveRetryFailures, setConsecutiveRetryFailures] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const retryRequested = useRef(false);

  const noteSuccess = useCallback(() => {
    retryRequested.current = false;
    setConsecutiveRetryFailures(0);
    setUsingFallback(false);
    setDismissed(false);
  }, []);

  const noteFailure = useCallback(() => {
    setUsingFallback(true);
    if (retryRequested.current) {
      setConsecutiveRetryFailures((n) => n + 1);
    }
  }, []);

  const canRetry = usingFallback;

  const requestRetry = useCallback(() => {
    retryRequested.current = true;
    setDismissed(false);
  }, []);

  const dismissNotice = useCallback(() => setDismissed(true), []);

  const notice =
    !dismissed && usingFallback && retryRequested.current && consecutiveRetryFailures >= retriesBeforeNotice
      ? message
      : null;

  return { notice, usingFallback, noteFailure, noteSuccess, canRetry, requestRetry, dismissNotice };
}

export default useFallbackNotice;
