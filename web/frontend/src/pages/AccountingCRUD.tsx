import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface AccountingEntry {
  id: number; date: string; description: string; category: string;
  amount: number; type: string; account: string; reference: string;
}

interface FormState {
  date: string; description: string; category: string;
  amount: number; type: string; account: string; reference: string;
}

const API_BASE = "/api/accounting";
const PAGE_SIZE = 10;

const emptyForm: FormState = {
  date: "", description: "", category: "", amount: 0, type: "expense", account: "", reference: "",
};

export default function AccountingCRUD() {
  const [entries, setEntries] = useState<AccountingEntry[]>([]);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const { sortedData: sortedEntries, requestSort, getSortIndicator } = useSort(entries);

  const fetchEntries = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams({
        page: String(page), limit: String(PAGE_SIZE),
        ...(search && { search }), ...(filterType && { type: filterType }), ...(filterCategory && { category: filterCategory }),
      });
      const res = await fetch(`${API_BASE}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setEntries(data.entries || data.data || []);
      setTotalPages(data.total_pages || data.totalPages || 1);
    } catch (e: any) { setError(e.message || "Failed to fetch entries"); }
    finally { setLoading(false); }
  }, [page, search, filterType, filterCategory]);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(""); setSubmitting(true);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm(emptyForm); setEditingId(null); setShowForm(false);
      fetchEntries();
    } catch (e: any) { setError(e.message || "Save failed"); }
    finally { setSubmitting(false); }
  };

  const handleEdit = (entry: AccountingEntry) => {
    setForm({ date: entry.date, description: entry.description, category: entry.category,
      amount: entry.amount, type: entry.type, account: entry.account, reference: entry.reference });
    setEditingId(entry.id); setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null); fetchEntries();
    } catch (e: any) { setError(e.message || "Delete failed"); }
  };

  const handleCancel = () => { setForm(emptyForm); setEditingId(null); setShowForm(false); setError(""); };
  const categories = [...new Set(entries.map((e) => e.category).filter(Boolean))];

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(entries as unknown as Record<string, unknown>[], "accounting_export.csv"), onDelete: () => { if (entries.length > 0) setShowDeleteConfirm(entries[0].id); }, onClose: handleCancel });

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Accounting</h1>
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}

      <div className="flex flex-wrap gap-3 mb-4">
        <input type="text" placeholder="Search entries..." value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"  ref={searchRef}/>
        <select value={filterType} onChange={(e) => { setFilterType(e.target.value); setPage(1); }} className="border rounded px-3 py-2">
          <option value="">All Types</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </select>
        <select value={filterCategory} onChange={(e) => { setFilterCategory(e.target.value); setPage(1); }} className="border rounded px-3 py-2">
          <option value="">All Categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"> title="Ctrl+N"+ New Entry</button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">{editingId ? "Edit Entry" : "Create Entry"}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Date</label>
              <input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input type="text" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <input type="text" required value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="w-full border rounded px-3 py-2">
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Account</label>
              <input type="text" value={form.account} onChange={(e) => setForm({ ...form, account: e.target.value })} className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Reference</label>
              <input type="text" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} className="w-full border rounded px-3 py-2" />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="submit" disabled={submitting} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
              {submitting ? "Saving..." : editingId ? "Update" : "Create"}
            </button>
            <button type="button" onClick={handleCancel} className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"> title="Escape to close" Cancel</button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto bg-white border rounded-lg shadow">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('date')}>Date{getSortIndicator('date')}</th>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('description')}>Description{getSortIndicator('description')}</th>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('category')}>Category{getSortIndicator('category')}</th>
              <th className="px-4 py-3 text-right cursor-pointer select-none" onClick={() => requestSort('amount')}>Amount{getSortIndicator('amount')}</th>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('type')}>Type{getSortIndicator('type')}</th>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('account')}>Account{getSortIndicator('account')}</th>
              <th className="px-4 py-3 text-left cursor-pointer select-none" onClick={() => requestSort('reference')}>Reference{getSortIndicator('reference')}</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-500">No entries found</td></tr>
            ) : (
              sortedEntries.map((entry) => (
                <tr key={entry.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">{entry.id}</td>
                  <td className="px-4 py-3">{entry.date}</td>
                  <td className="px-4 py-3 font-medium">{entry.description}</td>
                  <td className="px-4 py-3">{entry.category}</td>
                  <td className={`px-4 py-3 text-right ${entry.type === "income" ? "text-green-600" : "text-red-600"}`}>
                    {entry.type === "income" ? "+" : "-"}${entry.amount.toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${entry.type === "income" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{entry.type}</span>
                  </td>
                  <td className="px-4 py-3">{entry.account}</td>
                  <td className="px-4 py-3">{entry.reference}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleEdit(entry)} className="text-blue-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(entry.id)} className="text-red-600 hover:underline"> title="Delete key to delete" Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="px-3 py-1 border rounded disabled:opacity-50">Previous</button>
        <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
        <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
      </div>

      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to delete entry #{showDeleteConfirm}? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 border rounded hover:bg-gray-100"> title="Escape to close" Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
