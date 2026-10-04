import React, { useState, useEffect } from 'react';

// ─── Button ───────────────────────────────────────────────────────────────────
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: 'sm' | 'md' | 'lg';
}
const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 hover:bg-blue-700 text-white',
  secondary: 'bg-gray-700 hover:bg-gray-600 text-gray-100',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
  ghost: 'bg-transparent hover:bg-gray-800 text-gray-300',
};
const sizeStyles = { sm: 'px-2 py-1 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' };
export const Button: React.FC<ButtonProps> = ({ variant = 'primary', size = 'md', className = '', children, ...props }) => (
  <button className={`rounded font-medium transition-colors ${variantStyles[variant]} ${sizeStyles[size]} ${className}`} {...props}>
    {children}
  </button>
);

// ─── Input ────────────────────────────────────────────────────────────────────
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}
export const Input: React.FC<InputProps> = ({ label, error, className = '', ...props }) => (
  <div className="flex flex-col gap-1">
    {label && <label className="text-sm text-gray-300">{label}</label>}
    <input
      className={`rounded bg-gray-800 border border-gray-700 px-3 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 ${error ? 'border-red-500' : ''} ${className}`}
      {...props}
    />
    {error && <span className="text-xs text-red-400">{error}</span>}
  </div>
);

// ─── Select ───────────────────────────────────────────────────────────────────
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
}
export const Select: React.FC<SelectProps> = ({ label, options, className = '', ...props }) => (
  <div className="flex flex-col gap-1">
    {label && <label className="text-sm text-gray-300">{label}</label>}
    <select className={`rounded bg-gray-800 border border-gray-700 px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500 ${className}`} {...props}>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

// ─── Modal ────────────────────────────────────────────────────────────────────
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}
export const Modal: React.FC<ModalProps> = ({ open, onClose, title, children, className = '' }) => {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (open) window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className={`bg-gray-900 border border-gray-700 rounded-lg p-6 w-full max-w-md ${className}`} onClick={(e) => e.stopPropagation()}>
        {title && <h2 className="text-lg font-semibold text-gray-100 mb-4">{title}</h2>}
        {children}
      </div>
    </div>
  );
};

// ─── Table ────────────────────────────────────────────────────────────────────
interface TableProps<T> {
  columns: { key: string; header: string; render?: (row: T) => React.ReactNode }[];
  data: T[];
  keyExtractor: (row: T) => string | number;
  className?: string;
}
export function Table<T>({ columns, data, keyExtractor, className = '' }: TableProps<T>) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm text-gray-100">
        <thead className="bg-gray-800">
          <tr>{columns.map((c) => <th key={c.key} className="px-4 py-2 text-left font-medium text-gray-300">{c.header}</th>)}</tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={keyExtractor(row)} className="border-t border-gray-800 hover:bg-gray-800/50">
              {columns.map((c) => <td key={c.key} className="px-4 py-2">{c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Card ─────────────────────────────────────────────────────────────────────
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  children: React.ReactNode;
}
export const Card: React.FC<CardProps> = ({ title, children, className = '', ...props }) => (
  <div className={`bg-gray-900 border border-gray-800 rounded-lg p-4 ${className}`} {...props}>
    {title && <h3 className="text-base font-semibold text-gray-100 mb-3">{title}</h3>}
    {children}
  </div>
);

// ─── Badge ────────────────────────────────────────────────────────────────────
type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';
interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}
const badgeStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-700 text-gray-200',
  success: 'bg-green-900 text-green-200',
  warning: 'bg-yellow-900 text-yellow-200',
  error: 'bg-red-900 text-red-200',
  info: 'bg-blue-900 text-blue-200',
};
export const Badge: React.FC<BadgeProps> = ({ variant = 'default', children, className = '' }) => (
  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badgeStyles[variant]} ${className}`}>{children}</span>
);

// ─── Spinner ──────────────────────────────────────────────────────────────────
export const Spinner: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500 ${className}`} />
);

// ─── EmptyState ───────────────────────────────────────────────────────────────
interface EmptyStateProps {
  message?: string;
  action?: React.ReactNode;
  className?: string;
}
export const EmptyState: React.FC<EmptyStateProps> = ({ message = 'No data available', action, className = '' }) => (
  <div className={`flex flex-col items-center justify-center py-12 text-gray-400 ${className}`}>
    <p className="mb-4">{message}</p>
    {action}
  </div>
);

// ─── ErrorBanner ──────────────────────────────────────────────────────────────
interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
}
export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss, className = '' }) => (
  <div className={`flex items-center justify-between bg-red-900/30 border border-red-800 text-red-200 px-4 py-3 rounded ${className}`}>
    <span>{message}</span>
    {onDismiss && <button onClick={onDismiss} className="text-red-300 hover:text-red-100 ml-4">✕</button>}
  </div>
);

// ─── Pagination ───────────────────────────────────────────────────────────────
interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}
export const Pagination: React.FC<PaginationProps> = ({ page, totalPages, onPageChange, className = '' }) => (
  <div className={`flex items-center gap-2 ${className}`}>
    <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Prev</Button>
    <span className="text-sm text-gray-300">Page {page} of {totalPages}</span>
    <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</Button>
  </div>
);

// ─── Tabs ─────────────────────────────────────────────────────────────────────
interface TabsProps {
  tabs: { key: string; label: string; content: React.ReactNode }[];
  defaultTab?: string;
  className?: string;
}
export const Tabs: React.FC<TabsProps> = ({ tabs, defaultTab, className = '' }) => {
  const [active, setActive] = useState(defaultTab || tabs[0]?.key || '');
  return (
    <div className={className}>
      <div className="flex border-b border-gray-800 mb-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActive(t.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${active === t.key ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:text-gray-200'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div>{tabs.find((t) => t.key === active)?.content}</div>
    </div>
  );
};
