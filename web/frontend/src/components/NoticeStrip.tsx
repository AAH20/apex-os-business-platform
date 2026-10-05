import React from 'react';

export interface NoticeStripProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

/**
 * Low-key informational strip for a degraded-but-usable state — e.g. a list that
 * fell back to bundled records because the API was unreachable. Deliberately not
 * the red error treatment: the page still renders rows, so it must not read as a
 * failure (red banners dominated screenshots and looked broken).
 */
export const NoticeStrip: React.FC<NoticeStripProps> = ({ message, onRetry, onDismiss }) => (
  <div
    role="status"
    className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded border border-amber-800/50 bg-amber-950/25 px-3 py-1.5 text-xs text-amber-200/90"
  >
    <span className="flex items-center gap-1.5">
      <svg className="h-3.5 w-3.5 flex-shrink-0 text-amber-400/80" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-4a1 1 0 011 1v3a1 1 0 11-2 0V7a1 1 0 011-1zm-1 8a1 1 0 100 2 1 1 0 000-2z"
          clipRule="evenodd"
        />
      </svg>
      {message}
    </span>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="font-medium text-amber-300/90 underline-offset-2 hover:text-amber-200 hover:underline"
      >
        Retry
      </button>
    )}
    {onDismiss && (
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notice"
        className="ml-auto text-amber-300/60 hover:text-amber-200"
      >
        &times;
      </button>
    )}
  </div>
);

export default NoticeStrip;
