import React, { useState, useEffect, useCallback } from 'react';
import { useSort } from '../hooks/useSort';
import { fetchWithTimeout } from '../api/fallback';

interface InventoryItem {
  id: number;
  name: string;
  sku: string;
  quantity: number;
  price: number;
  category: string;
  description?: string;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

const API_BASE = '/api/inventory';

const InventoryCRUD: React.FC = () => {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [pagination, setPagination] = useState<Pagination>({ page: 1, limit: 10, total: 0, totalPages: 0 });
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [formData, setFormData] = useState({ name: '', sku: '', quantity: 0, price: 0, category_id: 0, description: '' });
  const { sortedData: sortedItems, requestSort, getSortIndicator } = useSort(items);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(pagination.page), limit: String(pagination.limit) });
      if (search) params.set('search', search);
      if (categoryFilter) params.set('category', categoryFilter);
      const res = await fetchWithTimeout(`${API_BASE}?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setPagination(data.pagination || { page: 1, limit: 10, total: 0, totalPages: 0 });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.limit, search, categoryFilter]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const resetForm = () => {
    setFormData({ name: '', sku: '', quantity: 0, price: 0, category_id: 0, description: '' });
    setEditingItem(null);
    setShowForm(false);
  };

  const openCreate = () => { resetForm(); setShowForm(true); };

  const openEdit = (item: InventoryItem) => {
    setFormData({ name: item.name, sku: item.sku, quantity: item.quantity, price: item.price, category_id: 0, description: item.description || '' });
    setEditingItem(item);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingItem ? `${API_BASE}/${editingItem.id}` : API_BASE;
      const method = editingItem ? 'PUT' : 'POST';
      const res = await fetchWithTimeout(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      resetForm();
      fetchItems();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      const res = await fetchWithTimeout(`${API_BASE}/${id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchItems();
    } catch (e: any) { setError(e.message); }
  };

  const categories = [...new Set(items.map(i => i.category).filter(Boolean))];

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'SKU', 'Quantity', 'Price', 'Category', 'Description'];
    const rows = sortedItems.map(item => [
      item.id, item.name, item.sku, item.quantity, (item.price ?? 0).toFixed(2), item.category, item.description || ''
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'inventory.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Inventory Management</h1>
      {error && <div className="bg-red-900/50 text-red-200 p-3 rounded mb-4">{error}</div>}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4 flex-wrap">
        <input className="border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px]" placeholder="Search by name or SKU..." value={search} onChange={e => { setSearch(e.target.value); setPagination(p => ({ ...p, page: 1 })); }} />
        <select className="border-gray-700 rounded px-3 py-2" value={categoryFilter} onChange={e => { setCategoryFilter(e.target.value); setPagination(p => ({ ...p, page: 1 })); }}>
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <button onClick={openCreate} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">+ New Item</button>
        <button onClick={exportCSV} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Export CSV</button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border-gray-700 rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">{editingItem ? 'Edit Item' : 'Create Item'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input required className="border-gray-700 rounded px-3 py-2" placeholder="Name" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} />
            <input required className="border-gray-700 rounded px-3 py-2" placeholder="SKU" value={formData.sku} onChange={e => setFormData({ ...formData, sku: e.target.value })} />
            <input required type="number" min="0" className="border-gray-700 rounded px-3 py-2" placeholder="Quantity" value={formData.quantity} onChange={e => setFormData({ ...formData, quantity: Number(e.target.value) })} />
            <input required type="number" min="0" step="0.01" className="border-gray-700 rounded px-3 py-2" placeholder="Price" value={formData.price} onChange={e => setFormData({ ...formData, price: Number(e.target.value) })} />
            <input required className="border-gray-700 rounded px-3 py-2" placeholder="Category" value={formData.category_id} onChange={e => setFormData({ ...formData, category_id: Number(e.target.value) })} />
            <input className="border-gray-700 rounded px-3 py-2" placeholder="Description" value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} />
          </div>
          <div className="mt-3 flex gap-2">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">{editingItem ? 'Update' : 'Create'}</button>
            <button type="button" onClick={resetForm} className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600">Cancel</button>
          </div>
        </form>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse bg-gray-800 shadow rounded">
          <thead><tr className="bg-gray-800">
            <th className="border-gray-700 px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th><th className="border-gray-700 px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('sku')}>SKU{getSortIndicator('sku')}</th>
            <th className="border-gray-700 px-3 py-2 text-right cursor-pointer select-none" onClick={() => requestSort('quantity')}>Qty{getSortIndicator('quantity')}</th><th className="border-gray-700 px-3 py-2 text-right cursor-pointer select-none" onClick={() => requestSort('price')}>Price{getSortIndicator('price')}</th>
            <th className="border-gray-700 px-3 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('category')}>Category{getSortIndicator('category')}</th><th className="border-gray-700 px-3 py-2 text-center">Actions</th>
          </tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={6} className="text-center py-4">Loading...</td></tr> :
              sortedItems.length === 0 ? <tr><td colSpan={6} className="text-center py-4 text-gray-400">No items found</td></tr> :
              sortedItems.map(item => (
                <tr key={item.id} className="hover:bg-gray-900">
                  <td className="border-gray-700 px-3 py-2">{item.name}</td>
                  <td className="border-gray-700 px-3 py-2 font-mono text-sm">{item.sku}</td>
                  <td className="border-gray-700 px-3 py-2 text-right">{item.quantity}</td>
                  <td className="border-gray-700 px-3 py-2 text-right">${(item.price ?? 0).toFixed(2)}</td>
                  <td className="border-gray-700 px-3 py-2">{item.category}</td>
                  <td className="border-gray-700 px-3 py-2 text-center whitespace-nowrap">
                    <button onClick={() => openEdit(item)} className="text-blue-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(item.id)} className="text-red-600 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <span className="text-sm text-gray-300">Page {pagination.page} of {pagination.totalPages} ({pagination.total} items)</span>
        <div className="flex gap-2">
          <button disabled={pagination.page <= 1} onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))} className="px-3 py-1 border-gray-700 rounded disabled:opacity-40 hover:bg-gray-800">Prev</button>
          <button disabled={pagination.page >= pagination.totalPages} onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))} className="px-3 py-1 border-gray-700 rounded disabled:opacity-40 hover:bg-gray-800">Next</button>
        </div>
      </div>

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 shadow-xl max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-300 mb-4">Are you sure you want to delete this item? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 border-gray-700 rounded hover:bg-gray-800">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InventoryCRUD;
