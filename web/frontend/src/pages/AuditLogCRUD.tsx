import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface AuditLog {
  id: string;
  action: string;
  entity: string;
  entityId: string;
  userId: string;
  timestamp: string;
  details?: string;
}

interface Filters {
  search: string;
  action: string;
  entity: string;
  page: number;
  limit: number;
}

const API_BASE = "/api/audit-logs";

const emptyForm = { action: "", entity: "", entityId: "", userId: "", details: "" };

const AuditLogCRUD: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({ search: "", action: "", entity: "", page: 1, limit: 10 });
  const { sortedData: sortedLogs, requestSort, getSortIndicator } = useSort(logs);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(filters.page),
        limit: String(filters.limit),
        ...(filters.search && { search: filters.search }),
        ...(filters.action && { action: filters.action }),
        ...(filters.entity && { entity: filters.entity }),
      });
      const res = await fetch(`${API_BASE}?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLogs(data.items || data.logs || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      setError(e.message || "Failed to fetch logs");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm(emptyForm);
      setEditingId(null);
      setShowForm(false);
      fetchLogs();
    } catch (e: any) {
      setError(e.message || "Save failed");
    }
  };

  const handleEdit = (log: AuditLog) => {
    setForm({ action: log.action, entity: log.entity, entityId: log.entityId, userId: log.userId, details: log.details || "" });
    setEditingId(log.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchLogs();
    } catch (e: any) {
      setError(e.message || "Delete failed");
    }
  };

  const totalPages = Math.ceil(total / filters.limit);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(logs as unknown as Record<string, unknown>[], "auditlog_export.csv"), onDelete: () => { if (logs.length > 0) setShowDeleteConfirm(logs[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Audit Logs</h1>
        <button onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm); }} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"> title="Ctrl+N"+ New Log</button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-900/50 text-red-200 rounded">{error}</div>}

      <div className="flex gap-3 mb-4 flex-wrap">
        <input placeholder="Search..." value={filters.search} onChange={e => setFilters(f => ({ ...f, search: e.target.value, page: 1 }))} className="border rounded px-3 py-2 flex-1 min-w-[200px]"  ref={searchRef}/>
        <select value={filters.action} onChange={e => setFilters(f => ({ ...f, action: e.target.value, page: 1 }))} className="border rounded px-3 py-2">
          <option value="">All Actions</option>
          <option value="CREATE">Create</option>
          <option value="UPDATE">Update</option>
          <option value="DELETE">Delete</option>
        </select>
        <select value={filters.entity} onChange={e => setFilters(f => ({ ...f, entity: e.target.value, page: 1 }))} className="border rounded px-3 py-2">
          <option value="">All Entities</option>
          <option value="User">User</option>
          <option value="Order">Order</option>
          <option value="Product">Product</option>
        </select>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-4 border rounded bg-gray-900">
          <h2 className="text-lg font-semibold mb-3">{editingId ? "Edit Log" : "New Log"}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input required placeholder="Action" value={form.action} onChange={e => setForm(f => ({ ...f, action: e.target.value }))} className="border rounded px-3 py-2" />
            <input required placeholder="Entity" value={form.entity} onChange={e => setForm(f => ({ ...f, entity: e.target.value }))} className="border rounded px-3 py-2" />
            <input required placeholder="Entity ID" value={form.entityId} onChange={e => setForm(f => ({ ...f, entityId: e.target.value }))} className="border rounded px-3 py-2" />
            <input required placeholder="User ID" value={form.userId} onChange={e => setForm(f => ({ ...f, userId: e.target.value }))} className="border rounded px-3 py-2" />
            <textarea placeholder="Details" value={form.details} onChange={e => setForm(f => ({ ...f, details: e.target.value }))} className="border rounded px-3 py-2 md:col-span-2" rows={2} />
          </div>
          <div className="mt-3 flex gap-2">
            <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">{editingId ? "Update" : "Create"}</button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm); }} className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-400"> title="Escape to close" Cancel</button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto border rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('timestamp')}>Timestamp{getSortIndicator('timestamp')}</th>
              <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('action')}>Action{getSortIndicator('action')}</th>
              <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('entity')}>Entity{getSortIndicator('entity')}</th>
              <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('entityId')}>Entity ID{getSortIndicator('entityId')}</th>
              <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('userId')}>User{getSortIndicator('userId')}</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-3 py-4 text-center text-gray-400">Loading...</td></tr>
            ) : sortedLogs.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-4 text-center text-gray-400">No logs found</td></tr>
            ) : (
              sortedLogs.map(log => (
                <tr key={log.id} className="border-t hover:bg-gray-900">
                  <td className="px-3 py-2">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="px-3 py-2"><span className="px-2 py-0.5 bg-blue-900/50 text-blue-200 rounded text-xs">{log.action}</span></td>
                  <td className="px-3 py-2">{log.entity}</td>
                  <td className="px-3 py-2">{log.entityId}</td>
                  <td className="px-3 py-2">{log.userId}</td>
                  <td className="px-3 py-2 flex gap-2">
                    <button onClick={() => handleEdit(log)} className="text-blue-600 hover:underline">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(log.id)} className="text-red-600 hover:underline"> title="Delete key to delete" Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex justify-between items-center">
        <span className="text-sm text-gray-400">Total: {total} logs</span>
        <div className="flex gap-2">
          <button disabled={filters.page <= 1} onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
          <span className="px-3 py-1">Page {filters.page} of {totalPages || 1}</span>
          <button disabled={filters.page >= totalPages} onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded shadow-lg max-w-sm w-full">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this audit log? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-400"> title="Escape to close" Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogCRUD;
