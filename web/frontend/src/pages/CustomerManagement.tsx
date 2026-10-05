import React, { useState, useEffect, useCallback } from 'react';

interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string;
  company: string;
}

interface CustomerFormData {
  name: string;
  email: string;
  phone: string;
  company: string;
}

const emptyForm: CustomerFormData = { name: '', email: '', phone: '', company: '' };
const PAGE_SIZE = 10;

const CustomerManagement: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [formData, setFormData] = useState<CustomerFormData>(emptyForm);
  const [deleteConfirm, setDeleteConfirm] = useState<Customer | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/customers/', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCustomers(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch customers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCustomers(); }, [fetchCustomers]);

  const companies = Array.from(new Set(customers.map(c => c.company).filter(Boolean))).sort();

  const filtered = customers.filter(c => {
    const q = search.toLowerCase();
    const matchSearch = !q || c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q) || c.phone.toLowerCase().includes(q);
    const matchCompany = !companyFilter || c.company === companyFilter;
    return matchSearch && matchCompany;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const openCreate = () => {
    setEditingCustomer(null);
    setFormData(emptyForm);
    setShowForm(true);
  };

  const openEdit = (c: Customer) => {
    setEditingCustomer(c);
    setFormData({ name: c.name, email: c.email, phone: c.phone, company: c.company });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const url = editingCustomer ? `/api/customers/${editingCustomer.id}/` : '/api/customers/';
      const method = editingCustomer ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      await fetchCustomers();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/customers/${deleteConfirm.id}/`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      await fetchCustomers();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setSaving(false);
    }
  };

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Email', 'Phone', 'Company'];
    const rows = filtered.map((c) => [c.id, c.name, c.email, c.phone, c.company]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'customers.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const inputClass = 'w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';
  const btnPrimary = 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';
  const btnSecondary = 'bg-gray-700 hover:bg-gray-600 text-gray-100 px-4 py-2 rounded font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';
  const btnDanger = 'bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Customer Management</h1>
          <div className="flex gap-2">
            <button onClick={openCreate} className={btnPrimary} aria-label="Create new customer">+ New Customer</button>
            <button onClick={exportCSV} className={btnSecondary} aria-label="Export customers as CSV">Export CSV</button>
            <button
              onClick={() => {
                const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'customers_export.json';
                a.click();
                URL.revokeObjectURL(url);
              }}
              className={btnSecondary}
              aria-label="Export customers as JSON"
            >
              Export JSON
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-4" role="alert" aria-live="assertive">
            {error}
            <button onClick={() => setError(null)} className="float-right font-bold" aria-label="Dismiss error">&times;</button>
          </div>
        )}

        <div className="flex flex-wrap gap-4 mb-4">
          <input
            type="text"
            placeholder="Search name, email, phone..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className={`${inputClass} max-w-sm`}
            aria-label="Search customers by name, email, or phone"
          />
          <select
            value={companyFilter}
            onChange={e => { setCompanyFilter(e.target.value); setPage(1); }}
            className={`${inputClass} max-w-xs`}
            aria-label="Filter by company"
          >
            <option value="">All Companies</option>
            {companies.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400" role="status" aria-live="polite">Loading...</div>
        ) : (
          <>
            <div className="overflow-x-auto bg-gray-800 rounded-lg shadow">
              <table className="w-full text-left" role="table" aria-label="Customers table">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-sm font-semibold" scope="col">Name</th>
                    <th className="px-4 py-3 text-sm font-semibold" scope="col">Email</th>
                    <th className="px-4 py-3 text-sm font-semibold" scope="col">Phone</th>
                    <th className="px-4 py-3 text-sm font-semibold" scope="col">Company</th>
                    <th className="px-4 py-3 text-sm font-semibold text-right" scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.length === 0 ? (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No customers found</td></tr>
                  ) : paginated.map(c => (
                    <tr key={c.id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="px-4 py-3">{c.name}</td>
                      <td className="px-4 py-3">{c.email}</td>
                      <td className="px-4 py-3">{c.phone}</td>
                      <td className="px-4 py-3">{c.company}</td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <button onClick={() => openEdit(c)} className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label={`Edit customer ${c.name}`}>Edit</button>
                        <button onClick={() => setDeleteConfirm(c)} className="px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-xs transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label={`Delete customer ${c.name}`}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-400" aria-live="polite">
                Showing {paginated.length} of {filtered.length} customers
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                  className={btnSecondary + ' disabled:opacity-50'}
                  aria-label="Go to previous page"
                >
                  Previous
                </button>
                <span className="px-3 py-2 text-sm" aria-live="polite">Page {safePage} of {totalPages}</span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                  className={btnSecondary + ' disabled:opacity-50'}
                  aria-label="Go to next page"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="customer-form-title">
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4" id="customer-form-title">{editingCustomer ? 'Edit Customer' : 'New Customer'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1" htmlFor="customer-name">Name *</label>
                  <input id="customer-name" required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className={inputClass} aria-label="Customer name" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" htmlFor="customer-email">Email *</label>
                  <input id="customer-email" required type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} className={inputClass} aria-label="Customer email" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" htmlFor="customer-phone">Phone</label>
                  <input id="customer-phone" value={formData.phone} onChange={e => setFormData({ ...formData, phone: e.target.value })} className={inputClass} aria-label="Customer phone" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" htmlFor="customer-company">Company</label>
                  <input id="customer-company" value={formData.company} onChange={e => setFormData({ ...formData, company: e.target.value })} className={inputClass} aria-label="Customer company" />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setShowForm(false)} className={btnSecondary} aria-label="Cancel customer form">Cancel</button>
                  <button type="submit" disabled={saving} className={btnPrimary} aria-label={editingCustomer ? 'Update customer' : 'Create customer'}>
                    {saving ? 'Saving...' : editingCustomer ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="delete-confirm-title">
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-sm">
              <h2 className="text-xl font-bold mb-2" id="delete-confirm-title">Confirm Delete</h2>
              <p className="text-gray-300 mb-6">Are you sure you want to delete <strong>{deleteConfirm.name}</strong>? This action cannot be undone.</p>
              <div className="flex justify-end gap-3">
                <button onClick={() => setDeleteConfirm(null)} className={btnSecondary} aria-label="Cancel delete">Cancel</button>
                <button onClick={handleDelete} disabled={saving} className={btnDanger} aria-label={`Confirm delete customer ${deleteConfirm.name}`}>
                  {saving ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerManagement;
