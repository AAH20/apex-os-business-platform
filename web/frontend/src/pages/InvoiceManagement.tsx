import React, { useState, useEffect, useCallback } from 'react';
import { fetchWithTimeout } from '../api/fallback';

interface Invoice {
  id: string;
  customer_name: string;
  customer_email: string;
  amount: number;
  currency: string;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  issue_date: string;
  due_date: string;
}

interface InvoiceFormData {
  customer_name: string;
  customer_email: string;
  amount: string;
  currency: string;
  status: Invoice['status'];
  issue_date: string;
  due_date: string;
}

const EMPTY_FORM: InvoiceFormData = {
  customer_name: '',
  customer_email: '',
  amount: '',
  currency: 'USD',
  status: 'draft',
  issue_date: '',
  due_date: '',
};

const STATUSES: Invoice['status'][] = ['draft', 'sent', 'paid', 'overdue', 'cancelled'];
const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CAD'];
const PAGE_SIZE = 10;

export default function InvoiceManagement() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
  const [formData, setFormData] = useState<InvoiceFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<Invoice | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithTimeout('/api/invoices', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setInvoices(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch invoices');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  useEffect(() => {
    if (!showForm && !deleteConfirm) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowForm(false);
        setDeleteConfirm(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showForm, deleteConfirm]);

  const filtered = invoices.filter(inv => {
    const q = search.toLowerCase();
    const matchesSearch = !q || inv.customer_name.toLowerCase().includes(q) || inv.customer_email.toLowerCase().includes(q) || inv.id.toLowerCase().includes(q);
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const openCreate = () => {
    setEditingInvoice(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  };

  const openEdit = (inv: Invoice) => {
    setEditingInvoice(inv);
    setFormData({
      customer_name: inv.customer_name,
      customer_email: inv.customer_email,
      amount: String(inv.amount),
      currency: inv.currency,
      status: inv.status,
      issue_date: inv.issue_date,
      due_date: inv.due_date,
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        amount: parseFloat(formData.amount),
        currency: formData.currency,
        status: formData.status,
        issue_date: formData.issue_date,
        due_date: formData.due_date,
      };
      const url = editingInvoice ? `/api/invoices/${editingInvoice.id}` : '/api/invoices';
      const method = editingInvoice ? 'PUT' : 'POST';
      const res = await fetchWithTimeout(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      fetchInvoices();
    } catch (e: any) {
      setError(e.message || 'Failed to save invoice');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(`/api/invoices/${deleteConfirm.id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      fetchInvoices();
    } catch (e: any) {
      setError(e.message || 'Failed to delete invoice');
    } finally {
      setDeleting(false);
    }
  };

  const statusColor = (s: string) => {
    const map: Record<string, string> = { draft: 'bg-gray-600 text-gray-200', sent: 'bg-blue-600 text-blue-100', paid: 'bg-green-600 text-green-100', overdue: 'bg-red-600 text-red-100', cancelled: 'bg-gray-700 text-gray-400' };
    return map[s] || 'bg-gray-600 text-gray-200';
  };

  const exportCSV = () => {
    const headers = ['ID', 'Customer', 'Email', 'Amount', 'Currency', 'Status', 'Issue Date', 'Due Date'];
    const rows = filtered.map(inv => [
      inv.id, inv.customer_name, inv.customer_email, (inv.amount ?? 0).toFixed(2), inv.currency, inv.status, inv.issue_date, inv.due_date
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'invoices.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Invoice Management</h1>
          <div className="flex gap-2">
            <button onClick={exportCSV} className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition-colors">Export CSV</button>
            <button onClick={openCreate} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors">+ New Invoice</button>
          </div>
        </div>

        {error && <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>}

        <div className="flex flex-wrap gap-3 mb-4">
          <input type="text" placeholder="Search invoices..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm flex-1 min-w-[200px] focus:outline-none focus:border-blue-500" />
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500">
            <option value="all">All Statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading invoices...</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded border border-gray-800">
              <table className="w-full text-sm">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">ID</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Customer</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Email</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-300">Amount</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Issue Date</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-300">Due Date</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-16 text-center">
                      <div className="text-5xl mb-4">🧾</div>
                      <h3 className="text-lg font-semibold text-gray-100 mb-2">No invoices yet</h3>
                      <p className="text-gray-400 mb-4">Get started by creating your first invoice.</p>
                      <button onClick={openCreate} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                        + New Invoice
                      </button>
                    </td></tr>
                  ) : paginated.map(inv => (
                    <tr key={inv.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-400">{inv.id.slice(0, 8)}</td>
                      <td className="px-4 py-3">{inv.customer_name}</td>
                      <td className="px-4 py-3 text-gray-400">{inv.customer_email}</td>
                      <td className="px-4 py-3 text-right">{inv.currency} {(inv.amount ?? 0).toFixed(2)}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColor(inv.status)}`}>{inv.status}</span></td>
                      <td className="px-4 py-3 text-gray-400">{inv.issue_date}</td>
                      <td className="px-4 py-3 text-gray-400">{inv.due_date}</td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <button onClick={() => openEdit(inv)} className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded transition-colors">Edit</button>
                        <button onClick={() => setDeleteConfirm(inv)} className="px-2 py-1 text-xs bg-red-700 hover:bg-red-600 rounded transition-colors">Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
              <span>Showing {paginated.length} of {filtered.length} invoices</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={safePage <= 1} className="px-3 py-1 bg-gray-800 border border-gray-700 rounded disabled:opacity-40 hover:bg-gray-700 transition-colors">Prev</button>
                <span className="px-3 py-1">Page {safePage} of {totalPages}</span>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={safePage >= totalPages} className="px-3 py-1 bg-gray-800 border border-gray-700 rounded disabled:opacity-40 hover:bg-gray-700 transition-colors">Next</button>
              </div>
            </div>
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowForm(false)}>
            <div className="bg-gray-800 border border-gray-700 rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between p-4 border-b border-gray-700">
                <h2 className="text-lg font-semibold">{editingInvoice ? 'Edit Invoice' : 'Create Invoice'}</h2>
                <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-200 text-xl leading-none">&times;</button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Customer Name</label>
                  <input required type="text" value={formData.customer_name} onChange={e => setFormData(d => ({ ...d, customer_name: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Customer Email</label>
                  <input required type="email" value={formData.customer_email} onChange={e => setFormData(d => ({ ...d, customer_email: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Amount</label>
                    <input required type="number" step="0.01" min="0" value={formData.amount} onChange={e => setFormData(d => ({ ...d, amount: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Currency</label>
                    <select value={formData.currency} onChange={e => setFormData(d => ({ ...d, currency: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500">
                      {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Status</label>
                  <select value={formData.status} onChange={e => setFormData(d => ({ ...d, status: e.target.value as Invoice['status'] }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500">
                    {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Issue Date</label>
                    <input required type="date" value={formData.issue_date} onChange={e => setFormData(d => ({ ...d, issue_date: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Due Date</label>
                    <input required type="date" value={formData.due_date} onChange={e => setFormData(d => ({ ...d, due_date: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">Cancel</button>
                  <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium disabled:opacity-50 transition-colors">{saving ? 'Saving...' : editingInvoice ? 'Update' : 'Create'}</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setDeleteConfirm(null)}>
            <div className="bg-gray-800 border border-gray-700 rounded-lg w-full max-w-sm p-6 relative" onClick={e => e.stopPropagation()}>
              <button onClick={() => setDeleteConfirm(null)} className="absolute top-3 right-3 text-gray-400 hover:text-gray-200 text-xl leading-none">&times;</button>
              <h2 className="text-lg font-semibold mb-2">Delete Invoice</h2>
              <p className="text-sm text-gray-400 mb-6">Are you sure you want to delete invoice for <span className="text-gray-200 font-medium">{deleteConfirm.customer_name}</span>? This action cannot be undone.</p>
              <div className="flex justify-end gap-3">
                <button onClick={() => setDeleteConfirm(null)} disabled={deleting} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">Cancel</button>
                <button onClick={handleDelete} disabled={deleting} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-medium disabled:opacity-50 transition-colors">{deleting ? 'Deleting...' : 'Delete'}</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
