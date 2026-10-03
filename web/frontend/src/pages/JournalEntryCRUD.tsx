import React, { useState, useEffect, useCallback } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

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
  debitAccount: string;
  creditAccount: string;
  amount: number;
  reference: string;
}

const emptyForm: FormData = {
  date: new Date().toISOString().slice(0, 10),
  description: "",
  debitAccount: "",
  creditAccount: "",
  amount: 0,
  reference: "",
};
const API_BASE = "/api/journal-entries";

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
      const res = await fetch(`${API_BASE}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setEntries(data.items || data.data || []);
      setTotalPages(data.totalPages || 1);
    } catch (e: any) {
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
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
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
      debitAccount: entry.debitAccount,
      creditAccount: entry.creditAccount,
      amount: entry.amount,
      reference: entry.reference || "",
    });
    setEditingId(entry.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
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

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(entries as Record<string, unknown>[], "journalentry_export.csv"), onDelete: () => { if (entries.length > 0) setShowDeleteConfirm(entries[0].id); }, onClose: handleCancel });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Journal Entries</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        > title="Ctrl+N"
          + New Entry
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-6 bg-white border border-gray-200 rounded-xl shadow-sm">
          <h2 className="text-lg font-semibold mb-4">
            {editingId ? "Edit Entry" : "New Entry"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
              <input type="text" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Optional" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Debit Account</label>
              <input type="text" value={form.debitAccount} onChange={(e) => setForm({ ...form, debitAccount: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Credit Account</label>
              <input type="text" value={form.creditAccount} onChange={(e) => setForm({ ...form, creditAccount: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
              <input type="number" step="0.01" min="0.01" value={form.amount || ""} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
              {editingId ? "Update" : "Create"}
            </button>
            <button type="button" onClick={handleCancel} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"> title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      <div className="mb-4 flex flex-col sm:flex-row gap-3">
        <input type="text" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search entries..." className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"  ref={searchRef}/>
        <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="posted">Posted</option>
          <option value="voided">Voided</option>
        </select>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('date')}>Date{getSortIndicator('date')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('description')}>Description{getSortIndicator('description')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('debitAccount')}>Debit{getSortIndicator('debitAccount')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('creditAccount')}>Credit{getSortIndicator('creditAccount')}</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('amount')}>Amount{getSortIndicator('amount')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
              ) : sortedFilteredEntries.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No entries found</td></tr>
              ) : (
                sortedFilteredEntries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-900">{entry.date}</td>
                    <td className="px-4 py-3 text-gray-900">{entry.description}</td>
                    <td className="px-4 py-3 text-gray-600">{entry.debitAccount}</td>
                    <td className="px-4 py-3 text-gray-600">{entry.creditAccount}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">${entry.amount.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 text-xs rounded-full font-medium ${
                        entry.status === "posted" ? "bg-green-100 text-green-700" :
                        entry.status === "voided" ? "bg-red-100 text-red-700" :
                        "bg-yellow-100 text-yellow-700"
                      }`}>
                        {entry.status || "draft"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => handleEdit(entry)} className="mr-2 text-blue-600 hover:text-blue-800 font-medium">Edit</button>
                      {showDeleteConfirm === entry.id ? (
                        <span className="inline-flex items-center gap-1">
                          <button onClick={() => handleDelete(entry.id)} className="text-red-600 hover:text-red-800 font-medium">Confirm</button>
                          <button onClick={() => setShowDeleteConfirm(null)} className="text-gray-500 hover:text-gray-700"> title="Escape to close" Cancel</button>
                        </span>
                      ) : (
                        <button onClick={() => setShowDeleteConfirm(entry.id)} className="text-red-600 hover:text-red-800 font-medium"> title="Delete key to delete" Delete</button>
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
            className="px-3 py-1 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50">
            Previous
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="px-3 py-1 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50">
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default JournalEntryCRUD;
