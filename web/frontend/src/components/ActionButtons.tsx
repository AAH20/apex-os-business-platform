import { useState, useRef, useEffect } from 'react';
import { Search, FileSpreadsheet, FileJson, ChevronDown, Trash2, Archive, RefreshCw } from 'lucide-react';

interface ActionButtonsProps {
  onSearch?: (query: string) => void;
  onExportCSV?: () => void;
  onExportJSON?: () => void;
  onBulkDelete?: () => void;
  onBulkArchive?: () => void;
  onBulkActivate?: () => void;
  onRefresh?: () => void;
  selectedCount?: number;
  searchPlaceholder?: string;
  showBulkActions?: boolean;
  hasBulkActions?: boolean;
}

export function ActionButtons({
  onSearch,
  onExportCSV,
  onExportJSON,
  onBulkDelete,
  onBulkArchive,
  onBulkActivate,
  onRefresh,
  selectedCount = 0,
  searchPlaceholder = 'Search...',
  showBulkActions = true,
  hasBulkActions = true,
}: ActionButtonsProps) {
  const [bulkDropdownOpen, setBulkDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setBulkDropdownOpen(false);
      }
    }
    if (bulkDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [bulkDropdownOpen]);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Search */}
      {onSearch && (
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            onChange={(e) => onSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]"
          />
        </div>
      )}

      {/* Export CSV */}
      {onExportCSV && (
        <button
          onClick={onExportCSV}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-100 text-sm transition-colors"
        >
          <FileSpreadsheet className="w-4 h-4" />
          CSV
        </button>
      )}

      {/* Export JSON */}
      {onExportJSON && (
        <button
          onClick={onExportJSON}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-100 text-sm transition-colors"
        >
          <FileJson className="w-4 h-4" />
          JSON
        </button>
      )}

      {/* Bulk Actions Dropdown */}
      {showBulkActions && hasBulkActions && selectedCount > 0 && (
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setBulkDropdownOpen(!bulkDropdownOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-100 text-sm transition-colors"
          >
            <ChevronDown className="w-4 h-4" />
            Bulk Actions ({selectedCount})
          </button>
          {bulkDropdownOpen && (
            <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-[60] min-w-[160px]">
              {onBulkDelete && (
                <button
                  onClick={() => { onBulkDelete(); setBulkDropdownOpen(false); }}
                  className="w-full text-left px-3 py-2 text-sm text-gray-100 hover:bg-gray-700 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Selected
                </button>
              )}
              {onBulkArchive && (
                <button
                  onClick={() => { onBulkArchive(); setBulkDropdownOpen(false); }}
                  className="w-full text-left px-3 py-2 text-sm text-gray-100 hover:bg-gray-700 flex items-center gap-2"
                >
                  <Archive className="w-4 h-4" />
                  Archive Selected
                </button>
              )}
              {onBulkActivate && (
                <button
                  onClick={() => { onBulkActivate(); setBulkDropdownOpen(false); }}
                  className="w-full text-left px-3 py-2 text-sm text-gray-100 hover:bg-gray-700 flex items-center gap-2"
                >
                  <Archive className="w-4 h-4" />
                  Activate Selected
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Refresh */}
      {onRefresh && (
        <button
          onClick={onRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-100 text-sm transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      )}
    </div>
  );
}
