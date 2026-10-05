import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Invoice {
  id: string;
  invoiceNumber: string;
  customerName: string;
  customerEmail: string;
  amount: number;
  status: "draft" | "sent" | "paid" | "overdue" | "cancelled";
  dueDate: string;
  items: { description: string; quantity: number; unitPrice: number }[];
  createdAt: string;
}

interface InvoiceFormData {
  customerName: string;
  customerEmail: string;
  amount: number;
  status: Invoice["status"];
  dueDate: string;
  items: { description: string; quantity: number; unitPrice: number }[];
}

const emptyForm: InvoiceFormData = {
  customerName: "",
  customerEmail: "",
  amount: 0,
  status: "draft",
  dueDate: "",
  items: [{ description: "", quantity: 1, unitPrice: 0 }],
};

const API_BASE = "/api/invoices";

export default function InvoiceCRUD() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [filtered, setFiltered] = useState<Invoice[]>([]);
  const [form, setForm] = useState<InvoiceFormData>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const perPage = 10;
  const { sortedData: sortedFiltered, requestSort, getSortIndicator } = useSort(filtered);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}?page=${page}&limit=${perPage}`, { headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error("Fetch failed");
      const data = await res.json();
      setInvoices(data.invoices || []);
      setTotalPages(data.totalPages || 1);
    } catch {
      setError("Failed to fetch invoices");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  useEffect(() => {
    let result = invoices;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (inv) =>
          inv.invoiceNumber.toLowerCase().includes(q) ||
          inv.customerName.toLowerCase().includes(q) ||
          inv.customerEmail.toLowerCase().includes(q)
      );
    }
    if (statusFilter !== "all") {
      result = result.filter((inv) => inv.status === statusFilter);
    }
    setFiltered(result);
  }, [invoices, search, statusFilter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("Save failed");
      setForm(emptyForm);
      setEditingId(null);
      setShowForm(false);
      fetchInvoices();
    } catch {
      setError("Failed to save invoice");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (inv: Invoice) => {
    setError("");
    setForm({
      customerName: inv.customerName,
      customerEmail: inv.customerEmail,
      amount: inv.amount,
      status: inv.status,
      dueDate: inv.dueDate,
      items: inv.items,
    });
    setEditingId(inv.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError("");
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error("Delete failed");
      setConfirmDelete(null);
      fetchInvoices();
    } catch {
      setError("Failed to delete invoice");
    } finally {
      setDeleting(false);
    }
  };

  const addItem = () =>
    setForm({ ...form, items: [...form.items, { description: "", quantity: 1, unitPrice: 0 }] });
  const removeItem = (idx: number) =>
    setForm({ ...form, items: form.items.filter((_, i) => i !== idx) });
  const updateItem = (idx: number, field: string, value: string | number) => {
    const items = [...form.items];
    items[idx] = { ...items[idx], [field]: value };
    setForm({ ...form, items });
  };
  const calcTotal = () =>
    form.items.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(invoices as unknown as Record<string, unknown>[], "invoice_export.csv"), onDelete: () => { if (invoices.length > 0) setConfirmDelete(invoices[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Invoices</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm); setError(""); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >+ New Invoice</button>
        <button
          onClick={() => exportToCSV(invoices as unknown as Record<string, unknown>[], "invoice_export.csv")}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >Export CSV</button>
        <button
          onClick={() => { const blob = new Blob([JSON.stringify(invoices, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'invoice_export.json'; a.click(); URL.revokeObjectURL(url); }}
          className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
        >Export JSON</button>
      </div>
      {error && <div className="bg-red-900/50 text-red-200 p-3 rounded mb-4">{error}</div>}
      <div className="flex gap-4 mb-4">
        <input type="text" placeholder="Search invoices..." value={search}
          onChange={(e) => setSearch(e.target.value)} className="bg-gray-800 text-gray-100 border border-gray-700 rounded px-3 py-2 flex-1"  ref={searchRef}/>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-gray-800 text-gray-100 border border-gray-700 rounded px-3 py-2">
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="sent">Sent</option>
          <option value="paid">Paid</option>
          <option value="overdue">Overdue</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 shadow rounded p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">
            {editingId ? "Edit Invoice" : "Create Invoice"}
          </h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <input placeholder="Customer Name" value={form.customerName}
              onChange={(e) => setForm({ ...form, customerName: e.target.value })}
              className="bg-gray-800 text-gray-100 border border-gray-700 rounded px-3 py-2" required />
            <input placeholder="Customer Email" type="email" value={form.customerEmail}
              onChange={(e) => setForm({ ...form, customerEmail: e.target.value })}
              className="bg-gray-800 text-gray-100 border border-gray-700 rounded px-3 py-2" required />
            <input placeholder="Due Date" type="date" value={form.dueDate}
              onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
              className="bg-gray-800 text-gray-100 border border-gray-700 rounded px-3 py-2" required />
            <select value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as Invoice["status"] })}
              className="bg-gray-800 text-gray-100 border border-gray-700 rounded px-3 py-2">
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="paid">Paid</option>
              <option value="overdue">Overdue</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <h3 className="font-medium mb-2">Line Items</h3>
          {form.items.map((item, idx) => (
            <div key={idx} className="flex gap-2 mb-2">
              <input placeholder="Description" value={item.description}
                onChange={(e) => updateItem(idx, "description", e.target.value)}
                className="border rounded px-3 py-2 flex-1" />
              <input type="number" placeholder="Qty" value={item.quantity}
                onChange={(e) => updateItem(idx, "quantity", Number(e.target.value))}
                className="border rounded px-3 py-2 w-20" />
              <input type="number" placeholder="Price" value={item.unitPrice}
                onChange={(e) => updateItem(idx, "unitPrice", Number(e.target.value))}
                className="border rounded px-3 py-2 w-24" />
              <button type="button" onClick={() => removeItem(idx)} className="text-red-500 px-2">✕</button>
            </div>
          ))}
          <button type="button" onClick={addItem} className="text-blue-400 mb-4">+ Add Item</button>
          <div className="flex justify-between items-center">
            <span className="font-semibold">Total: ${calcTotal().toFixed(2)}</span>
            <div className="flex gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-800 text-gray-100 border border-gray-700 rounded"> title="Escape to close" Cancel</button>
              <button type="submit" disabled={saving}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
                {saving ? "Saving..." : editingId ? "Update" : "Create"}
              </button>
            </div>
          </div>
        </form>
      )}
      <div className="bg-gray-800 shadow rounded overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('invoiceNumber')}>#{getSortIndicator('invoiceNumber')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('customerName')}>Customer{getSortIndicator('customerName')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('amount')}>Amount{getSortIndicator('amount')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('dueDate')}>Due Date{getSortIndicator('dueDate')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-8">Loading...</td></tr>
            ) : sortedFiltered.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No invoices found</td></tr>
            ) : (
              sortedFiltered.map((inv) => (
                <tr key={inv.id} className="border-t border-gray-700 hover:bg-gray-800">
                  <td className="px-4 py-3 text-sm">{inv.invoiceNumber}</td>
                  <td className="px-4 py-3 text-sm">{inv.customerName}</td>
                  <td className="px-4 py-3 text-sm">${inv.amount.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      inv.status === "paid" ? "bg-green-900/50 text-green-200" :
                      inv.status === "overdue" ? "bg-red-900/50 text-red-200" :
                      inv.status === "sent" ? "bg-blue-900/50 text-blue-200" :
                      inv.status === "cancelled" ? "bg-gray-800 text-gray-300" :
                      "bg-yellow-900/50 text-yellow-200"
                    }`}>{inv.status}</span>
                  </td>
                  <td className="px-4 py-3 text-sm">{inv.dueDate}</td>
                  <td className="px-4 py-3 text-sm">
                    <button onClick={() => handleEdit(inv)} className="text-blue-400 mr-3 hover:underline">Edit</button>
                    {confirmDelete === inv.id ? (
                      <>
                        <button onClick={() => handleDelete(inv.id)} disabled={deleting}
                          className="text-red-400 mr-2 hover:underline disabled:opacity-50">
                          {deleting ? "Deleting..." : "Confirm"}
                        </button>
                        <button onClick={() => setConfirmDelete(null)} className="text-gray-400 hover:underline"> title="Escape to close" Cancel</button>
                      </>
                    ) : (
                      <button onClick={() => setConfirmDelete(inv.id)} className="text-red-400 hover:underline"> title="Delete key to delete" Delete</button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="flex justify-center gap-2 mt-4">
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}
          className="px-3 py-1 bg-gray-800 text-gray-100 border border-gray-700 rounded disabled:opacity-50">Prev</button>
        <span className="px-3 py-1">Page {page} of {totalPages}</span>
        <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages}
          className="px-3 py-1 bg-gray-800 text-gray-100 border border-gray-700 rounded disabled:opacity-50">Next</button>
      </div>
    </div>
  );
}
