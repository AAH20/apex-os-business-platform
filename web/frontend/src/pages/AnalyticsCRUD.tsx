import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface AnalyticsEntry {
  id: string;
  name: string;
  category: string;
  value: number;
  date: string;
  notes?: string;
}

interface FormState {
  name: string;
  category: string;
  value: string;
  date: string;
  notes: string;
}

const emptyForm: FormState = { name: "", category: "", value: "", date: "", notes: "" };

const AnalyticsCRUD: React.FC = () => {
  const [entries, setEntries] = useState<AnalyticsEntry[]>([]);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const perPage = 10;
  const { sortedData: sortedEntries, requestSort, getSortIndicator } = useSort(entries);

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(perPage),
        ...(search && { search }),
        ...(filterCategory && { category: filterCategory }),
      });
      const res = await fetch(`/api/analytics?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`Failed to fetch: HTTP ${res.status}`);
      const data = await res.json();
      setEntries(data.items || []);
      setTotalPages(Math.max(1, Math.ceil((data.total || 0) / perPage)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch analytics");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterCategory]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const payload = {
      name: form.name,
      category: form.category,
      value: parseFloat(form.value) || 0,
      date: form.date,
      notes: form.notes,
    };
    try {
      const url = editingId ? `/api/analytics/${editingId}` : "/api/analytics";
      const method = editingId ? "PATCH" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Save failed: HTTP ${res.status}`);
      setForm(emptyForm);
      setEditingId(null);
      fetchEntries();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (entry: AnalyticsEntry) => {
    setEditingId(entry.id);
    setForm({
      name: entry.name,
      category: entry.category,
      value: String(entry.value),
      date: entry.date,
      notes: entry.notes || "",
    });
  };

  const handleDelete = async (id: string) => {
    setError("");
    try {
      const res = await fetch(`/api/analytics/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`Delete failed: HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchEntries();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleCancel = () => {
    setForm(emptyForm);
    setEditingId(null);
  };

  const categories = Array.from(new Set(entries.map((e) => e.category).filter(Boolean)));

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(entries as unknown as Record<string, unknown>[], "analytics_export.csv"), onDelete: () => { if (entries.length > 0) setShowDeleteConfirm(entries[0].id); }, onClose: handleCancel });

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Analytics Management</h1>
      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="bg-gray-800 shadow rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-300">
          {editingId ? "Edit Analytics Entry" : "Create Analytics Entry"}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input type="text" placeholder="Name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input type="text" placeholder="Category *" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required className="border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input type="number" step="0.01" placeholder="Value *" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} required className="border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required className="border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <textarea placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className="w-full border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
        <div className="flex gap-3">
          <button type="submit" disabled={submitting} className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
            {submitting ? "Saving..." : editingId ? "Update" : "Create"}
          </button>
          {editingId && (
            <button type="button" onClick={handleCancel} className="bg-gray-700 text-gray-300 px-5 py-2 rounded hover:bg-gray-500 transition"> title="Escape to close" Cancel
            </button>
          )}
        </div>
      </form>
      <div className="flex flex-col sm:flex-row gap-3">
        <input type="text" placeholder="Search analytics..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="flex-1 border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"  ref={searchRef}/>
        <select value={filterCategory} onChange={(e) => { setFilterCategory(e.target.value); setPage(1); }} className="border border-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
      </div>
      <div className="bg-gray-800 shadow rounded-lg overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('category')}>Category{getSortIndicator('category')}</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('value')}>Value{getSortIndicator('value')}</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('date')}>Date{getSortIndicator('date')}</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedEntries.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No analytics entries found</td></tr>
            ) : (
              sortedEntries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-sm text-gray-100">{entry.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{entry.category}</td>
                  <td className="px-4 py-3 text-sm text-gray-100 font-medium">{entry.value}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{entry.date}</td>
                  <td className="px-4 py-3 text-sm space-x-2">
                    <button onClick={() => handleEdit(entry)} className="text-blue-400 hover:text-blue-300 font-medium">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(entry.id)} className="text-red-400 hover:text-red-300 font-medium"> title="Delete key to delete" Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition">Previous</button>
        <span className="text-sm text-gray-400">Page {page} of {totalPages}</span>
        <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition">Next</button>
      </div>
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-gray-100">Confirm Delete</h3>
            <p className="text-gray-400">Are you sure you want to delete this analytics entry? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-500 transition"> title="Escape to close" Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsCRUD;
