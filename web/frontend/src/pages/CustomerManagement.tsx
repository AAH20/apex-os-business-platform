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
      const res = await fetch('/api/customers/');
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
        headers: { 'Content-Type': 'application/json' },
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
      const res = await fetch(`/api/customers/${deleteConfirm.id}/`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      await fetchCustomers();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setSaving(false);
    }
  };

  const inputClass = 'w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500';
  const btnPrimary = 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors disabled:opacity-50';
  const btnSecondary = 'bg-gray-700 hover:bg-gray-600 text-gray-100 px-4 py-2 rounded font-medium transition-colors';
  const btnDanger = 'bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium transition-colors';

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Customer Management</h1>
          <button onClick={openCreate} className={btnPrimary}>+ New Customer</button>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">
            {error}
            <button onClick={() => setError(null)} className="float-right font-bold">&times;</button>
          </div>
        )}

        <div className="flex flex-wrap gap-4 mb-4">
          <input
            type="text"
            placeholder="Search name, email, phone..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className={`${inputClass} max-w-sm`}
          />
          <select
            value={companyFilter}
            onChange={e => { setCompanyFilter(e.target.value); setPage(1); }}
            className={`${inputClass} max-w-xs`}
          >
            <option value="">All Companies</option>
            {companies.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : (
          <>
            <div className="overflow-x-auto bg-gray-800 rounded-lg shadow">
              <table className="w-full text-left">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-sm font-semibold">Name</th>
                    <th className="px-4 py-3 text-sm font-semibold">Email</th>
                    <th className="px-4 py-3 text-sm font-semibold">Phone</th>
                    <th className="px-4 py-3 text-sm font-semibold">Company</th>
                    <th className="px-4 py-3 text-sm font-semibold text-right">Actions</th>
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
                        <button onClick={() => openEdit(c)} className="text-blue-400 hover:text-blue-300 text-sm font-medium">Edit</button>
                        <button onClick={() => setDeleteConfirm(c)} className="text-red-400 hover:text-red-300 text-sm font-medium">Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-400">
                Showing {paginated.length} of {filtered.length} customers
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                  className={btnSecondary + ' disabled:opacity-50'}
                >
                  Previous
                </button>
                <span className="px-3 py-2 text-sm">Page {safePage} of {totalPages}</span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                  className={btnSecondary + ' disabled:opacity-50'}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4">{editingCustomer ? 'Edit Customer' : 'New Customer'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Name *</label>
                  <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Email *</label>
                  <input required type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Phone</label>
                  <input value={formData.phone} onChange={e => setFormData({ ...formData, phone: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Company</label>
                  <input value={formData.company} onChange={e => setFormData({ ...formData, company: e.target.value })} className={inputClass} />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setShowForm(false)} className={btnSecondary}>Cancel</button>
                  <button type="submit" disabled={saving} className={btnPrimary}>
                    {saving ? 'Saving...' : editingCustomer ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-sm">
              <h2 className="text-xl font-bold mb-2">Confirm Delete</h2>
              <p className="text-gray-300 mb-6">Are you sure you want to delete <strong>{deleteConfirm.name}</strong>? This action cannot be undone.</p>
              <div className="flex justify-end gap-3">
                <button onClick={() => setDeleteConfirm(null)} className={btnSecondary}>Cancel</button>
                <button onClick={handleDelete} disabled={saving} className={btnDanger}>
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
