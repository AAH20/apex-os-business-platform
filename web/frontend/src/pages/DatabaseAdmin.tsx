import { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Column {
  name: string;
  type: string;
  nullable?: boolean;
  primaryKey?: boolean;
}

interface TableSchema {
  name: string;
  columns: Column[];
}

type ApiResponse<T> = T[] | { items: T[] } | { data: T[] };

interface BulkOperation {
  type: 'delete' | 'update' | 'insert';
  table: string;
  ids?: string[];
  data?: Record<string, unknown>;
}

// ─── API Response Normalizer ─────────────────────────────────────────────────
function normalizeResponse<T>(response: ApiResponse<T>): T[] {
  if (Array.isArray(response)) return response;
  if ('items' in response && Array.isArray(response.items)) return response.items;
  if ('data' in response && Array.isArray(response.data)) return response.data;
  return [];
}

// ─── API Client ──────────────────────────────────────────────────────────────
const API_BASE = '/api/all';

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── CSV / JSON Export ───────────────────────────────────────────────────────
function exportCSV(columns: string[], rows: Record<string, unknown>[]): void {
  const escape = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const csv = [
    columns.join(','),
    ...rows.map((r) => columns.map((c) => escape(r[c])).join(',')),
  ].join('\n');
  downloadFile(csv, 'export.csv', 'text/csv');
}

function exportJSON(data: unknown): void {
  downloadFile(JSON.stringify(data, null, 2), 'export.json', 'application/json');
}

function downloadFile(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Components ───────────────────────────────────────────────────────────────
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
      <span className="ml-3 text-gray-400">Loading…</span>
    </div>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="mb-4 flex items-center justify-between rounded-lg border border-red-800 bg-red-950/50 px-4 py-3 text-red-300" role="alert" aria-live="assertive">
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="ml-4 rounded bg-red-800 px-3 py-1 text-sm hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          aria-label="Retry loading table data"
        >
          Retry
        </button>
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-12 text-center text-gray-500" aria-live="polite">
      <p className="text-lg">{message}</p>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function DatabaseAdmin() {
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [schema, setSchema] = useState<TableSchema | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkOp, setBulkOp] = useState<BulkOperation['type']>('delete');

  // Load table list
  const loadTables = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<string>>('/tables');
      setTables(normalizeResponse(res));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load tables');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTables();
  }, [loadTables]);

  // Load schema + rows for selected table
  const loadTable = useCallback(async (table: string) => {
    if (!table) return;
    setLoading(true);
    setError(null);
    setSelectedIds(new Set());
    try {
      const [schemaRes, dataRes] = await Promise.all([
        apiFetch<TableSchema>(`/tables/${table}/schema`),
        apiFetch<ApiResponse<Record<string, unknown>>>(`/tables/${table}/rows`),
      ]);
      setSchema(schemaRes);
      const normalized = normalizeResponse(dataRes);
      setRows(normalized);
      setColumns(normalized.length > 0 ? Object.keys(normalized[0]) : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load table data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTable(selectedTable);
  }, [selectedTable, loadTable]);

  // Bulk operations
  const executeBulk = async () => {
    if (selectedIds.size === 0) return;
    setLoading(true);
    setError(null);
    try {
      await apiFetch('/bulk', {
        method: 'POST',
        body: JSON.stringify({
          type: bulkOp,
          table: selectedTable,
          ids: [...selectedIds],
        } satisfies BulkOperation),
      });
      setSelectedIds(new Set());
      await loadTable(selectedTable);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Bulk operation failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const allSelected = rows.length > 0 && selectedIds.size === rows.length;

  return (
    <div className="min-h-screen bg-gray-900 p-6 text-gray-100">
      <h1 className="mb-6 text-2xl font-bold">Database Admin</h1>

      {error && <ErrorBanner message={error} onRetry={() => loadTable(selectedTable)} />}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Sidebar — Table List */}
        <div className="rounded-lg bg-gray-800 p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
            Tables
          </h2>
          {loading && tables.length === 0 ? (
            <LoadingSpinner />
          ) : tables.length === 0 ? (
            <EmptyState message="No tables found" />
          ) : (
            <ul className="space-y-1" aria-label="Database tables">
              {tables.map((t) => (
                <li key={t}>
                  <button
                    onClick={() => setSelectedTable(t)}
                    className={`w-full rounded px-3 py-2 text-left text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${
                      selectedTable === t
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-300 hover:bg-gray-700'
                    }`}
                    aria-label={`Select table ${t}`}
                    aria-pressed={selectedTable === t}
                  >
                    {t}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Main Content */}
        <div className="space-y-6 lg:col-span-3">
          {!selectedTable ? (
            <div className="rounded-lg bg-gray-800 p-6">
              <EmptyState message="Select a table from the sidebar to view its data" />
            </div>
          ) : loading ? (
            <div className="rounded-lg bg-gray-800 p-6">
              <LoadingSpinner />
            </div>
          ) : (
            <>
              {/* Schema Viewer */}
              {schema && (
                <div className="rounded-lg bg-gray-800 p-4">
                  <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
                    Schema — {schema.name}
                  </h2>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm" role="table">
                      <thead>
                        <tr className="border-b border-gray-700 text-left text-gray-400">
                          <th className="pb-2 pr-4">Column</th>
                          <th className="pb-2 pr-4">Type</th>
                          <th className="pb-2 pr-4">Nullable</th>
                          <th className="pb-2">PK</th>
                        </tr>
                      </thead>
                      <tbody>
                        {schema.columns.map((col) => (
                          <tr key={col.name} className="border-b border-gray-700/50">
                            <td className="py-2 pr-4 font-mono text-gray-200">{col.name}</td>
                            <td className="py-2 pr-4 text-gray-400">{col.type}</td>
                            <td className="py-2 pr-4 text-gray-400">
                              {col.nullable ? 'Yes' : 'No'}
                            </td>
                            <td className="py-2 text-gray-400">
                              {col.primaryKey ? '🔑' : ''}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Data Table + Toolbar */}
              <div className="rounded-lg bg-gray-800 p-4">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
                    Data — {selectedTable} ({rows.length} rows)
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={() => exportCSV(columns, rows)}
                      disabled={rows.length === 0}
                      className="rounded bg-gray-700 px-3 py-1.5 text-sm text-gray-200 hover:bg-gray-600 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                      aria-label="Export data as CSV"
                    >
                      Export CSV
                    </button>
                    <button
                      onClick={() => exportJSON(rows)}
                      disabled={rows.length === 0}
                      className="rounded bg-gray-700 px-3 py-1.5 text-sm text-gray-200 hover:bg-gray-600 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                      aria-label="Export data as JSON"
                    >
                      Export JSON
                    </button>
                  </div>
                </div>

                {rows.length === 0 ? (
                  <EmptyState message="No rows in this table" />
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm" role="table">
                        <thead>
                          <tr className="border-b border-gray-700 text-left text-gray-400">
                            <th className="pb-2 pr-4">
                              <input
                                type="checkbox"
                                checked={allSelected}
                                onChange={() =>
                                  setSelectedIds(
                                    allSelected
                                      ? new Set()
                                      : new Set(rows.map((r) => String(r.id ?? r._id))),
                                  )
                                }
                                className="rounded border-gray-600 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                                aria-label="Select all rows"
                              />
                            </th>
                            {columns.map((c) => (
                              <th key={c} className="pb-2 pr-4">
                                {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((row, i) => {
                            const id = String(row.id ?? row._id ?? i);
                            return (
                              <tr
                                key={id}
                                className="border-b border-gray-700/50 hover:bg-gray-700/30"
                              >
                                <td className="py-2 pr-4">
                                  <input
                                    type="checkbox"
                                    checked={selectedIds.has(id)}
                                    onChange={() => toggleSelect(id)}
                                    className="rounded border-gray-600 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                                    aria-label={`Select row ${id}`}
                                  />
                                </td>
                                {columns.map((c) => (
                                  <td key={c} className="py-2 pr-4 text-gray-300">
                                    {String(row[c] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* Bulk Operations */}
                    <div className="mt-4 flex items-center gap-3 border-t border-gray-700 pt-4">
                      <select
                        value={bulkOp}
                        onChange={(e) => setBulkOp(e.target.value as BulkOperation['type'])}
                        className="rounded bg-gray-700 px-3 py-1.5 text-sm text-gray-200 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label="Bulk operation type"
                      >
                        <option value="delete">Delete</option>
                        <option value="update">Update</option>
                        <option value="insert">Insert</option>
                      </select>
                      <button
                        onClick={executeBulk}
                        disabled={selectedIds.size === 0}
                        className="rounded bg-red-700 px-3 py-1.5 text-sm text-white hover:bg-red-600 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label={`Apply ${bulkOp} to ${selectedIds.size} selected rows`}
                      >
                        Apply to {selectedIds.size} selected
                      </button>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
