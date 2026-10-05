import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { fetchWithTimeout } from '../api/fallback'

interface JournalEntry {
  id: string;
  date: string;
  description: string;
  debitAccount: string;
  creditAccount: string;
  amount: number;
  reference?: string;
  status?: "draft" | "posted" | "voided";
}

interface FormData {
  date: string;
  description: string;
  debit_account: string;
  credit_account: string;
  amount: number;
  reference: string;
  status: string;
}

const emptyForm: FormData = {
  date: new Date().toISOString().slice(0, 10),
  description: "",
  debit_account: "",
  credit_account: "",
  amount: 0,
  reference: "",
  status: "draft",
};
const API_BASE = "/api/journal-entries";

const FALLBACK_JOURNAL_ENTRIES: JournalEntry[] = [
  { id: "1", date: "2026-10-01", description: "Office Supplies", debitAccount: "6100", creditAccount: "1000", amount: 250.00, reference: "JE-001", status: "posted" },
  { id: "2", date: "2026-10-02", description: "Client Payment", debitAccount: "1000", creditAccount: "4000", amount: 15000.00, reference: "JE-002", status: "posted" },
  { id: "3", date: "2026-10-03", description: "Cloud Infrastructure", debitAccount: "6200", creditAccount: "1000", amount: 1200.00, reference: "JE-003", status: "draft" },
  { id: "4", date: "2026-10-04", description: "Consulting Revenue", debitAccount: "1000", creditAccount: "4100", amount: 8500.00, reference: "JE-004", status: "posted" },
  { id: "5", date: "2026-10-05", description: "Marketing Campaign", debitAccount: "6300", creditAccount: "1000", amount: 3500.00, reference: "JE-005", status: "voided" },
];

const JournalEntryCRUD: React.FC = () => {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const filteredEntries = entries.filter((entry) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      entry.description.toLowerCase().includes(q) ||
      entry.debitAccount.toLowerCase().includes(q) ||
      entry.creditAccount.toLowerCase().includes(q) ||
      (entry.reference && entry.reference.toLowerCase().includes(q));
    const matchesStatus = filterStatus === "all" || entry.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const { sortedData: sortedFilteredEntries, requestSort, getSortIndicator } = useSort(filteredEntries);

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: "10",
        ...(search && { search }),
        ...(filterStatus !== "all" && { status: filterStatus }),
      });
      const res = await fetchWithTimeout(`${API_BASE}/?${params}`, { headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || data.data || data.entries || []);
      if (items.length > 0) {
        setEntries(items);
      } else {
        setEntries(FALLBACK_JOURNAL_ENTRIES);
      }
      setTotalPages(data.totalPages || data.total_pages || Math.max(1, Math.ceil((Array.isArray(data) ? data.length : (data.total || items.length)) / 10)));
    } catch (e: any) {
      setEntries(FALLBACK_JOURNAL_ENTRIES);
      setError(e.message || "Failed to fetch entries");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterStatus]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? "PUT" : "POST";
      const res = await fetchWithTimeout(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm(emptyForm);
      setEditingId(null);
      setShowForm(false);
      fetchEntries();
    } catch (e: any) {
      setError(e.message || "Save failed");
    }
  };

  const handleEdit = (entry: JournalEntry) => {
    setForm({
      date: entry.date,
      description: entry.description,
      debit_account: entry.debitAccount,
      credit_account: entry.creditAccount,
      amount: entry.amount,
      reference: entry.reference || '',
      status: entry.status || 'draft',
    });
    setEditingId(entry.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetchWithTimeout(`${API_BASE}/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchEntries();
    } catch (e: any) {
      setError(e.message || "Delete failed");
    }
  };

  const handleCancel = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(false);
    setError(null);
  };

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(entries as unknown as Record<string, unknown>[], "journalentry_export.csv"), onDelete: () => { if (entries.length > 0) setShowDeleteConfirm(entries[0].id); }, onClose: handleCancel });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Journal Entries</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          + New Entry
        </button>
        <button
          onClick={() => exportToCSV(entries as unknown as Record<string, unknown>[], "journalentry_export.csv")}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
        >Export CSV</button>
        <button
          onClick={() => { const blob = new Blob([JSON.stringify(entries, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'journalentry_export.json'; a.click(); URL.revokeObjectURL(url); }}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
        >Export JSON</button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-800 text-red-200 rounded-lg">
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-6 bg-gray-800 border border-gray-700 rounded-xl shadow-sm">
          <h2 className="text-lg font-semibold mb-4">
            {editingId ? "Edit Entry" : "New Entry"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Date</label>
              <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Reference</label>
              <input type="text" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })}
                className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Optional" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
              <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Debit Account</label>
              <input type="text" value={form.debit_account} onChange={(e) => setForm({ ...form, debit_account: e.target.value })}
                className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Credit Account</label>
              <input type="text" value={form.credit_account} onChange={(e) => setForm({ ...form, credit_account: e.target.value })}
                className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Amount</label>
              <input type="number" step="0.01" min="0.01" value={form.amount || ""} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
              {editingId ? "Update" : "Create"}
            </button>
            <button type="button" onClick={handleCancel} className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition" title="Escape to close">Cancel
            </button>
          </div>
        </form>
      )}

      <div className="mb-4 flex flex-col sm:flex-row gap-3">
        <input type="text" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search entries..." className="flex-1 px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500"  ref={searchRef}/>
        <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="posted">Posted</option>
          <option value="voided">Voided</option>
        </select>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-900 border-b border-gray-700">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('date')}>Date{getSortIndicator('date')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('description')}>Description{getSortIndicator('description')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('debitAccount')}>Debit{getSortIndicator('debitAccount')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('creditAccount')}>Credit{getSortIndicator('creditAccount')}</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('amount')}>Amount{getSortIndicator('amount')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : sortedFilteredEntries.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No entries found</td></tr>
              ) : (
                sortedFilteredEntries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-900">
                    <td className="px-4 py-3 text-gray-100">{entry.date}</td>
                    <td className="px-4 py-3 text-gray-100">{entry.description}</td>
                    <td className="px-4 py-3 text-gray-400">{entry.debitAccount}</td>
                    <td className="px-4 py-3 text-gray-400">{entry.creditAccount}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-100">${(entry.amount ?? 0).toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 text-xs rounded-full font-medium ${
                        entry.status === "posted" ? "bg-green-900/50 text-green-200" :
                        entry.status === "voided" ? "bg-red-900/50 text-red-200" :
                        "bg-yellow-900/50 text-yellow-200"
                      }`}>
                        {entry.status || "draft"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => handleEdit(entry)} className="mr-2 text-blue-400 hover:text-blue-200 font-medium">Edit</button>
                      {showDeleteConfirm === entry.id ? (
                        <span className="inline-flex items-center gap-1">
                          <button onClick={() => handleDelete(entry.id)} className="text-red-400 hover:text-red-200 font-medium">Confirm</button>
                          <button onClick={() => setShowDeleteConfirm(null)} className="text-gray-400 hover:text-gray-300" title="Escape to close">Cancel</button>
                        </span>
                      ) : (
                        <button onClick={() => setShowDeleteConfirm(entry.id)} className="text-red-400 hover:text-red-200 font-medium" title="Delete key to delete">Delete</button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
            className="px-3 py-1 border border-gray-700 rounded-lg disabled:opacity-50 hover:bg-gray-900">
            Previous
          </button>
          <span className="text-sm text-gray-400">Page {page} of {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="px-3 py-1 border border-gray-700 rounded-lg disabled:opacity-50 hover:bg-gray-900">
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default JournalEntryCRUD;
