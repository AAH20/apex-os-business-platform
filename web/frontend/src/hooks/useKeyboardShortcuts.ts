import { useEffect, useRef } from 'react'

export interface ShortcutHandlers {
  onNew?: () => void;
  onSearch?: () => void;
  onExport?: () => void;
  onDelete?: () => void;
  onClose?: () => void;
  searchRef?: React.RefObject<HTMLInputElement | null>;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  const { onNew, onSearch, onExport, onDelete, onClose, searchRef } = handlers;

  const onNewRef = useRef(onNew);
  const onSearchRef = useRef(onSearch);
  const onExportRef = useRef(onExport);
  const onDeleteRef = useRef(onDelete);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onNewRef.current = onNew;
    onSearchRef.current = onSearch;
    onExportRef.current = onExport;
    onDeleteRef.current = onDelete;
    onCloseRef.current = onClose;
  }, [onNew, onSearch, onExport, onDelete, onClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT';

      if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        onNewRef.current?.();
        return;
      }

      if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        if (searchRef?.current) {
          searchRef.current.focus();
          searchRef.current.select();
        } else {
          onSearchRef.current?.();
        }
        return;
      }

      if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        onExportRef.current?.();
        return;
      }

      if (e.key === 'Delete' && !isInput) {
        e.preventDefault();
        onDeleteRef.current?.();
        return;
      }

      if (e.key === 'Escape') {
        onCloseRef.current?.();
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [searchRef]);
}

export function exportToCSV(data: Record<string, unknown>[], filename: string) {
  if (!data.length) return;
  const headers = Object.keys(data[0]);
  const csv = [
    headers.join(','),
    ...data.map(row => headers.map(h => {
      const val = row[h];
      const str = val == null ? '' : String(val);
      return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str.replace(/"/g, '""')}"` : str;
    }).join(','))
  ].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
