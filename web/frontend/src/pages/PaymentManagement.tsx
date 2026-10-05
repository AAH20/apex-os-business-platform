import React, { useState, useEffect, useCallback } from 'react';

interface Payment {
  id: number;
  amount: number;
  currency: string;
  method: string;
  status: string;
  order_id: number;
  created_at?: string;
}

interface PaymentFormData {
  amount: number;
  currency: string;
  method: string;
  status: string;
  order_id: number;
}

const EMPTY_FORM: PaymentFormData = {
  amount: 0,
  currency: 'USD',
  method: 'credit_card',
  status: 'pending',
  order_id: 0,
};

const STATUSES = ['pending', 'completed', 'failed', 'refunded'];
const METHODS = ['credit_card', 'debit_card', 'paypal', 'bank_transfer', 'crypto'];
const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CAD'];
const PAGE_SIZE = 10;

export default function PaymentManagement() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingPayment, setEditingPayment] = useState<Payment | null>(null);
  const [formData, setFormData] = useState<PaymentFormData>(EMPTY_FORM);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/payments/');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items: Payment[] = Array.isArray(data) ? data : data.items || [];
      setPayments(items);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch payments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  useEffect(() => {
    if (!showForm && !showDeleteConfirm) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowForm(false);
        setShowDeleteConfirm(false);
        setDeletingId(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showForm, showDeleteConfirm]);

  const filtered = payments.filter((p) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      p.id.toString().includes(q) ||
      p.order_id.toString().includes(q) ||
      p.method.toLowerCase().includes(q) ||
      p.currency.toLowerCase().includes(q);
    const matchesStatus = !statusFilter || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paginated = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const openCreate = () => {
    setEditingPayment(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  };

  const openEdit = (p: Payment) => {
    setEditingPayment(p);
    setFormData({
      amount: p.amount,
      currency: p.currency,
      method: p.method,
      status: p.status,
      order_id: p.order_id,
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const url = editingPayment
        ? `/api/payments/${editingPayment.id}/`
        : '/api/payments/';
      const method = editingPayment ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      await fetchPayments();
    } catch (e: any) {
      setError(e.message || 'Failed to save payment');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (deletingId === null) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/payments/${deletingId}/`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(false);
      setDeletingId(null);
      await fetchPayments();
    } catch (e: any) {
      setError(e.message || 'Failed to delete payment');
    } finally {
      setSubmitting(false);
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'completed': return 'text-green-400';
      case 'pending': return 'text-yellow-400';
      case 'failed': return 'text-red-400';
      case 'refunded': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Payment Management</h1>
          <button
            onClick={openCreate}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            + New Payment
          </button>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-4 mb-6">
          <input
            type="text"
            placeholder="Search by ID, order, method, currency..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="bg-gray-800 border border-gray-700 text-gray-100 px-4 py-2 rounded-lg flex-1 min-w-[200px] focus:outline-none focus:border-blue-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-gray-800 border border-gray-700 text-gray-100 px-4 py-2 rounded-lg focus:outline-none focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading payments...</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-700">
              <table className="w-full text-sm">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">ID</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Order</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Amount</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Currency</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Method</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Created</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {paginated.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-16 text-center">
                        <div className="text-5xl mb-4">💳</div>
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">No payments yet</h3>
                        <p className="text-gray-400 mb-4">Get started by recording your first payment.</p>
                        <button onClick={openCreate} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                          + New Payment
                        </button>
                      </td>
                    </tr>
                  ) : (
                    paginated.map((p) => (
                      <tr key={p.id} className="hover:bg-gray-800/50 transition-colors">
                        <td className="px-4 py-3">{p.id}</td>
                        <td className="px-4 py-3">#{p.order_id}</td>
                        <td className="px-4 py-3 font-medium">{p.amount.toFixed(2)}</td>
                        <td className="px-4 py-3">{p.currency}</td>
                        <td className="px-4 py-3">{p.method.replace('_', ' ')}</td>
                        <td className={`px-4 py-3 font-medium ${statusColor(p.status)}`}>
                          {p.status}
                        </td>
                        <td className="px-4 py-3 text-gray-400">
                          {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button
                              onClick={() => openEdit(p)}
                              className="text-blue-400 hover:text-blue-300 text-xs font-medium"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => { setDeletingId(p.id); setShowDeleteConfirm(true); }}
                              className="text-red-400 hover:text-red-300 text-xs font-medium"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-400">
                Showing {paginated.length} of {filtered.length} payments
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="bg-gray-800 border border-gray-700 text-gray-300 px-3 py-1 rounded disabled:opacity-40 hover:bg-gray-700 transition-colors"
                >
                  Prev
                </button>
                <span className="text-sm text-gray-400 px-3 py-1">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="bg-gray-800 border border-gray-700 text-gray-300 px-3 py-1 rounded disabled:opacity-40 hover:bg-gray-700 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowForm(false)}>
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700 relative" onClick={e => e.stopPropagation()}>
              <button onClick={() => setShowForm(false)} className="absolute top-3 right-3 text-gray-400 hover:text-gray-200 text-xl leading-none">&times;</button>
              <h2 className="text-xl font-bold mb-4">
                {editingPayment ? 'Edit Payment' : 'Create Payment'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Order ID</label>
                  <input
                    type="number"
                    value={formData.order_id}
                    onChange={(e) => setFormData({ ...formData, order_id: parseInt(e.target.value) || 0 })}
                    className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Currency</label>
                  <select
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    {CURRENCIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Method</label>
                  <select
                    value={formData.method}
                    onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    {METHODS.map((m) => (
                      <option key={m} value={m}>{m.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium disabled:opacity-50 transition-colors"
                  >
                    {submitting ? 'Saving...' : editingPayment ? 'Update' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 py-2 rounded-lg font-medium transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => { setShowDeleteConfirm(false); setDeletingId(null); }}>
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm border border-gray-700 relative" onClick={e => e.stopPropagation()}>
              <button onClick={() => { setShowDeleteConfirm(false); setDeletingId(null); }} className="absolute top-3 right-3 text-gray-400 hover:text-gray-200 text-xl leading-none">&times;</button>
              <h2 className="text-xl font-bold mb-2">Delete Payment</h2>
              <p className="text-gray-400 mb-6">
                Are you sure you want to delete payment #{deletingId}? This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDelete}
                  disabled={submitting}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg font-medium disabled:opacity-50 transition-colors"
                >
                  {submitting ? 'Deleting...' : 'Delete'}
                </button>
                <button
                  onClick={() => { setShowDeleteConfirm(false); setDeletingId(null); }}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 py-2 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
