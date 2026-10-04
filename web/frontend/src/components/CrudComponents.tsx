import React, { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Column<T> {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
  accessor?: (row: T) => string | number;
}

export interface CrudTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
}

export interface CrudModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export interface FormField {
  name: string;
  label: string;
  type?: 'text' | 'email' | 'number' | 'select' | 'textarea';
  required?: boolean;
  options?: { value: string; label: string }[];
  placeholder?: string;
  validate?: (value: any) => string | null;
}

export interface CrudFormProps {
  fields: FormField[];
  initialValues?: Record<string, any>;
  onSubmit: (values: Record<string, any>) => void;
  onCancel?: () => void;
  submitLabel?: string;
  cancelLabel?: string;
}

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}

export interface EmptyStateProps {
  icon?: React.ReactNode;
  message: string;
  description?: string;
  action?: React.ReactNode;
}

export interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
  retry?: () => void;
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalItems?: number;
  itemsPerPage?: number;
}

// ─── LoadingSpinner ─────────────────────────────────────────────────────────

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', message }) => {
  const sizes = { sm: 'h-4 w-4 border-2', md: 'h-8 w-8 border-3', lg: 'h-12 w-12 border-4' };
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className={`${sizes[size]} animate-spin rounded-full border-gray-700 border-t-blue-500`} />
      {message && <p className="mt-3 text-sm text-gray-400">{message}</p>}
    </div>
  );
};

// ─── EmptyState ─────────────────────────────────────────────────────────────

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, message, description, action }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4">
    {icon && <div className="text-gray-600 mb-4">{icon}</div>}
    <h3 className="text-lg font-medium text-gray-100 mb-1">{message}</h3>
    {description && <p className="text-sm text-gray-400 text-center max-w-sm mb-4">{description}</p>}
    {action && <div>{action}</div>}
  </div>
);

// ─── ErrorBanner ────────────────────────────────────────────────────────────

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss, retry }) => (
  <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-start justify-between">
    <div className="flex items-start gap-3">
      <svg className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
      <div>
        <p className="text-sm text-red-200">{message}</p>
        {retry && <button onClick={retry} className="mt-2 text-sm text-red-300 hover:text-red-100 underline">Try again</button>}
      </div>
    </div>
    {onDismiss && (
      <button onClick={onDismiss} className="text-red-400 hover:text-red-200 ml-4">
        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
    )}
  </div>
);

// ─── Pagination ─────────────────────────────────────────────────────────────

export const Pagination: React.FC<PaginationProps> = ({ currentPage, totalPages, onPageChange, totalItems, itemsPerPage = 10 }) => {
  const getPages = (): (number | string)[] => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages: (number | string)[] = [1];
    if (currentPage > 3) pages.push('…');
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) pages.push(i);
    if (currentPage < totalPages - 2) pages.push('…');
    pages.push(totalPages);
    return pages;
  };
  const start = (currentPage - 1) * itemsPerPage + 1;
  const end = Math.min(currentPage * itemsPerPage, totalItems ?? 0);
  return (
    <div className="flex items-center justify-between border-t border-gray-700 bg-gray-800 px-4 py-3">
      <div className="text-sm text-gray-400">{totalItems !== undefined && `Showing ${start}-${end} of ${totalItems}`}</div>
      <div className="flex items-center gap-1">
        <button onClick={() => onPageChange(currentPage - 1)} disabled={currentPage <= 1} className="px-3 py-1 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed">Prev</button>
        {getPages().map((p, i) => typeof p === 'string' ? (
          <span key={`e${i}`} className="px-2 text-gray-500">…</span>
        ) : (
          <button key={p} onClick={() => onPageChange(p)} className={`px-3 py-1 text-sm rounded ${p === currentPage ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>{p}</button>
        ))}
        <button onClick={() => onPageChange(currentPage + 1)} disabled={currentPage >= totalPages} className="px-3 py-1 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed">Next</button>
      </div>
    </div>
  );
};

// ─── CrudTable ──────────────────────────────────────────────────────────────

export function CrudTable<T>({ columns, data, keyExtractor, onRowClick, loading = false, emptyMessage = 'No data found' }: CrudTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const perPage = 10;

  const handleSort = (col: Column<T>) => {
    if (col.sortable === false) return;
    if (sortKey === col.key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortKey(col.key); setSortDir('asc'); }
  };

  const sorted = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return 0;
    const aVal = col.accessor ? col.accessor(a) : (a as any)[sortKey];
    const bVal = col.accessor ? col.accessor(b) : (b as any)[sortKey];
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const totalPages = Math.max(1, Math.ceil(sorted.length / perPage));
  const paged = sorted.slice((page - 1) * perPage, page * perPage);

  if (loading) return <LoadingSpinner message="Loading data…" />;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 border-b border-gray-700">
              {columns.map((col) => (
                <th key={col.key} onClick={() => handleSort(col)} className={`px-4 py-3 text-left font-medium text-gray-400 ${col.sortable !== false ? 'cursor-pointer hover:text-gray-200' : ''}`}>
                  <span className="flex items-center gap-1">{col.header}{sortKey === col.key && <span>{sortDir === 'asc' ? '↑' : '↓'}</span>}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr><td colSpan={columns.length}><EmptyState message={emptyMessage} /></td></tr>
            ) : (
              paged.map((row) => (
                <tr key={keyExtractor(row)} onClick={() => onRowClick?.(row)} className={`border-b border-gray-700 last:border-0 hover:bg-gray-700/50 ${onRowClick ? 'cursor-pointer' : ''}`}>
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-gray-100">
                      {col.render ? col.render(row) : String(col.accessor ? col.accessor(row) : (row as any)[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {sorted.length > perPage && (
        <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} totalItems={sorted.length} itemsPerPage={perPage} />
      )}
    </div>
  );
}

// ─── CrudModal ──────────────────────────────────────────────────────────────

export const CrudModal: React.FC<CrudModalProps> = ({ isOpen, onClose, title, children, footer }) => {
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200">
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="px-6 py-4 overflow-y-auto flex-1">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">{footer}</div>}
      </div>
    </div>
  );
};

// ─── CrudForm ───────────────────────────────────────────────────────────────

export const CrudForm: React.FC<CrudFormProps> = ({ fields, initialValues = {}, onSubmit, onCancel, submitLabel = 'Save', cancelLabel = 'Cancel' }) => {
  const [values, setValues] = useState<Record<string, any>>(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};
    for (const field of fields) {
      const val = values[field.name];
      if (field.required && (val === undefined || val === '' || val === null)) {
        newErrors[field.name] = `${field.label} is required`;
      } else if (field.validate && val) {
        const err = field.validate(val);
        if (err) newErrors[field.name] = err;
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [fields, values]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try { await onSubmit(values); } finally { setSubmitting(false); }
  };

  const handleChange = (name: string, value: any) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => { const n = { ...prev }; delete n[name]; return n; });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {fields.map((field) => (
        <div key={field.name}>
          <label htmlFor={field.name} className="block text-sm font-medium text-gray-300 mb-1">
            {field.label}{field.required && <span className="text-red-400 ml-1">*</span>}
          </label>
          {field.type === 'select' ? (
            <select id={field.name} value={values[field.name] ?? ''} onChange={(e) => handleChange(field.name, e.target.value)} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500">
              <option value="">Select…</option>
              {field.options?.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          ) : field.type === 'textarea' ? (
            <textarea id={field.name} value={values[field.name] ?? ''} onChange={(e) => handleChange(field.name, e.target.value)} placeholder={field.placeholder} rows={3} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500" />
          ) : (
            <input id={field.name} type={field.type ?? 'text'} value={values[field.name] ?? ''} onChange={(e) => handleChange(field.name, e.target.value)} placeholder={field.placeholder} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500" />
          )}
          {errors[field.name] && <p className="mt-1 text-sm text-red-400">{errors[field.name]}</p>}
        </div>
      ))}
      <div className="flex justify-end gap-3 pt-2">
        {onCancel && <button type="button" onClick={onCancel} className="px-4 py-2 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600">{cancelLabel}</button>}
        <button type="submit" disabled={submitting} className="px-4 py-2 text-sm rounded bg-blue-600 text-gray-900 hover:bg-blue-500 disabled:opacity-50">{submitting ? 'Saving…' : submitLabel}</button>
      </div>
    </form>
  );
};
