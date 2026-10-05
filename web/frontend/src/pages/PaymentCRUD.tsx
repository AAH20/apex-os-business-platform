import React, { useState, useEffect, useCallback, useRef } from "react"
import { fetchWithTimeout } from '../api/fallback';
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts"

interface Payment {
  id: string;
  amount: number;
  currency: string;
  status: "pending" | "completed" | "failed" | "refunded";
  method: string;
  customerName: string;
  customerEmail: string;
  description: string;
  createdAt: string;
}

interface PaymentFormData {
  amount: number;
  currency: string;
  method: string;
  status: Payment["status"];
  order_id: string;
  customer_id: string;
  customerName: string;
  customerEmail: string;
  description: string;
}

const EMPTY_FORM: PaymentFormData = {
  amount: 0,
  currency: "USD",
  method: "card",
  status: "pending",
  order_id: "",
  customer_id: "",
  customerName: "",
  customerEmail: "",
  description: "",
};

const API_BASE = "/api/payments";

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetchWithTimeout(url, {
    headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export default function PaymentCRUD() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [formData, setFormData] = useState<PaymentFormData>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { sortedData: sortedPayments, requestSort, getSortIndicator } = useSort(payments);

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: "10",
        ...(search && { search }),
        ...(statusFilter !== "all" && { status: statusFilter }),
      });
      const data = await apiFetch<{ payments: Payment[]; totalPages: number }>(
        `${API_BASE}?${params}`
      );
      setPayments(data.payments);
      setTotalPages(data.totalPages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch payments");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (editingId) {
        await apiFetch(`${API_BASE}/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(formData),
        });
      } else {
        await apiFetch(API_BASE, {
          method: "POST",
          body: JSON.stringify(formData),
        });
      }
      setFormData(EMPTY_FORM);
      setEditingId(null);
      setShowForm(false);
      fetchPayments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save payment");
    }
  };

  const handleEdit = (payment: Payment) => {
    setFormData({
      amount: payment.amount,
      currency: payment.currency,
      status: payment.status,
      method: payment.method,
      order_id: '',
      customer_id: '',
      customerName: payment.customerName,
      customerEmail: payment.customerEmail,
      description: payment.description,
    });
    setEditingId(payment.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError("");
    try {
      await apiFetch(`${API_BASE}/${id}`, { method: "DELETE" });
      setShowDeleteConfirm(null);
      fetchPayments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete payment");
    }
  };

  const handleCancel = () => {
    setFormData(EMPTY_FORM);
    setEditingId(null);
    setShowForm(false);
    setError("");
  };

  const statusColors: Record<string, string> = {
    pending: "bg-yellow-900/50 text-yellow-200",
    completed: "bg-green-900/50 text-green-200",
    failed: "bg-red-900/50 text-red-200",
    refunded: "bg-blue-900/50 text-blue-200",
  };

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(payments as unknown as Record<string, unknown>[], "payment_export.csv"), onDelete: () => { if (payments.length > 0) setShowDeleteConfirm(payments[0].id); }, onClose: handleCancel });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Payment Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex flex-wrap gap-4 mb-6">
        <input
          type="text"
          placeholder="Search payments..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"
         ref={searchRef}/>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="all">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="refunded">Refunded</option>
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(EMPTY_FORM); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Payment
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border rounded-lg p-6 mb-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">
            {editingId ? "Edit Payment" : "Create Payment"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input
                type="number"
                step="0.01"
                required
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Currency</label>
              <select
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                className="w-full border rounded px-3 py-2"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as Payment["status"] })}
                className="w-full border rounded px-3 py-2"
              >
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Method</label>
              <select
                value={formData.method}
                onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                className="w-full border rounded px-3 py-2"
              >
                <option value="card">Card</option>
                <option value="bank_transfer">Bank Transfer</option>
                <option value="paypal">PayPal</option>
                <option value="crypto">Crypto</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Customer Name</label>
              <input
                type="text"
                required
                value={formData.customerName}
                onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Customer Email</label>
              <input
                type="email"
                required
                value={formData.customerEmail}
                onChange={(e) => setFormData({ ...formData, customerEmail: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? "Update" : "Create"}
            </button>
            <button type="button" onClick={handleCancel} className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-400"> title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {/* Payments Table */}
      <div className="bg-gray-800 border rounded-lg shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('customerName')}>Customer{getSortIndicator('customerName')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('amount')}>Amount{getSortIndicator('amount')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('method')}>Method{getSortIndicator('method')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('createdAt')}>Date{getSortIndicator('createdAt')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedPayments.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No payments found</td></tr>
            ) : (
              sortedPayments.map((p) => (
                <tr key={p.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3">
                    <div className="font-medium">{p.customerName}</div>
                    <div className="text-sm text-gray-400">{p.customerEmail}</div>
                  </td>
                  <td className="px-4 py-3 font-medium">${(p.amount ?? 0).toFixed(2)} {p.currency}</td>
                  <td className="px-4 py-3 capitalize">{p.method.replace("_", " ")}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[p.status]}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400">
                    {new Date(p.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(p)}
                        className="text-blue-600 hover:text-blue-200 text-sm font-medium"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(p.id)}
                        className="text-red-600 hover:text-red-200 text-sm font-medium"
                      > title="Delete key to delete" Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-center items-center gap-4 mt-6">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-800"
        >
          Previous
        </button>
        <span className="text-sm text-gray-300">Page {page} of {totalPages}</span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-800"
        >
          Next
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-300 mb-4">Are you sure you want to delete this payment? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 border rounded hover:bg-gray-800"
              > title="Escape to close" Cancel
              </button>
              <button
                onClick={() => handleDelete(showDeleteConfirm)}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}