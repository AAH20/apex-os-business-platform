import React, { useState, useEffect, useCallback } from 'react';
import { api, Product, ProductInput } from '../api/client';
import { ActionButtons } from '../components/ActionButtons';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

const EMPTY_FORM: ProductInput = { name: '', sku: '', quantity: 0, price: 0, reorder_level: 10 };
const PAGE_SIZE = 10;

export default function InventoryManagement() {
  const [items, setItems] = useState<Product[]>([]);
  const [filtered, setFiltered] = useState<Product[]>([]);
  const [form, setForm] = useState<ProductInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [filterValue, setFilterValue] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showDelete, setShowDelete] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getProducts({ limit: 100 });
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setError('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  useEffect(() => {
    let result = items;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(i =>
        i.name.toLowerCase().includes(q) || i.sku.toLowerCase().includes(q)
      );
    }
    if (categoryFilter) {
      result = result.filter(i => {
        if (categoryFilter === 'out_of_stock') return i.quantity === 0;
        if (categoryFilter === 'low_stock') return i.quantity > 0 && i.quantity <= i.reorder_level;
        if (categoryFilter === 'in_stock') return i.quantity > i.reorder_level;
        return true;
      });
    }
    setFiltered(result);
    setPage(1);
  }, [items, search, categoryFilter]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (editingId) {
        await api.updateProduct(editingId, form);
      } else {
        await api.createProduct(form);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
      fetchItems();
    } catch (e) {
      setError('Save failed');
    }
  };

  const handleEdit = (item: Product) => {
    setForm({ name: item.name, sku: item.sku, quantity: item.quantity, price: item.price, reorder_level: item.reorder_level });
    setEditingId(item.id);
  };

  const handleDelete = async () => {
    if (showDelete === null) return;
    try {
      await api.deleteProduct(showDelete);
      setShowDelete(null);
      fetchItems();
    } catch (e) {
      setError('Delete failed');
    }
  };


  const getCurrentData = () => {
    return [];
  };

  // ── Action Buttons Handlers ──────────────────────────────────────────────
  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleExportCSV = () => {
    const data = (getCurrentData() as any) || [];
    if (data.length === 0) return;
    const headers = Object.keys(data[0]);
    const csv = [headers.join(','), ...data.map((item: any) => headers.map(h => `"${String(item[h] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'inventorymanagement_export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const data = (getCurrentData() as any) || [];
    if (data.length === 0) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'inventorymanagement_export.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRefresh = () => {
    fetchItems();
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} selected item(s)?`)) return;
    setSelectedIds(new Set());
  };

  // ── Dashboard Data ──────────────────────────────────────────────────────
  const totalProducts = items.length;
  const lowStockItems = items.filter(i => i.quantity > 0 && i.quantity <= i.reorder_level).length;
  const totalSuppliers = new Set(items.map(i => (i as any).supplier).filter(Boolean)).size;
  const pendingOrders = items.filter(i => i.quantity === 0).length;

  const categoryMap: Record<string, number> = {};
  items.forEach(i => {
    const cat = (i as any).category || 'Uncategorized';
    categoryMap[cat] = (categoryMap[cat] || 0) + 1;
  });
  const categoryData = Object.entries(categoryMap).map(([name, value]) => ({ name, value }));

  const stockStatusData = [
    { name: 'In Stock', value: items.filter(i => i.quantity > i.reorder_level).length },
    { name: 'Low Stock', value: lowStockItems },
    { name: 'Out of Stock', value: items.filter(i => i.quantity === 0).length },
  ].filter(d => d.value > 0);

  const PIE_COLORS = ['#22c55e', '#f59e0b', '#ef4444'];

  const kpis = [
    { label: 'Total Products', value: totalProducts, color: 'text-blue-400' },
    { label: 'Low Stock Items', value: lowStockItems, color: 'text-amber-400' },
    { label: 'Total Suppliers', value: totalSuppliers, color: 'text-emerald-400' },
    { label: 'Pending Orders', value: pendingOrders, color: 'text-red-400' },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">Inventory Management</h1>
        <ActionButtons
          onSearch={handleSearch}
          onExportCSV={handleExportCSV}
          onExportJSON={handleExportJSON}
          onRefresh={handleRefresh}
          onBulkDelete={handleBulkDelete}
          selectedCount={selectedIds.size}
          searchPlaceholder="Search products..."
        />

      {error && <div className="bg-red-900 text-red-200 p-3 rounded mb-4 flex items-center justify-between"><span>{error}</span><button onClick={fetchItems} className="ml-4 rounded bg-red-800 px-3 py-1 text-xs font-medium hover:bg-red-700">Retry</button></div>}

      {/* Dashboard */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Dashboard</h2>
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {kpis.map(kpi => (
            <div key={kpi.label} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-sm text-gray-400 mb-1">{kpi.label}</p>
              <p className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</p>
            </div>
          ))}
        </div>
        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold mb-3 text-gray-300">Products by Category</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.375rem' }} labelStyle={{ color: '#f3f4f6' }} />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold mb-3 text-gray-300">Stock Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={stockStatusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {stockStatusData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.375rem' }} labelStyle={{ color: '#f3f4f6' }} />
                <Legend wrapperStyle={{ color: '#9ca3af', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-gray-800 p-4 rounded-lg mb-6">
        <h2 className="text-lg font-semibold mb-3">{editingId ? 'Edit Product' : 'Add Product'}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
          <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="SKU" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} required />
          <input className="bg-gray-700 text-gray-100 p-2 rounded" type="number" placeholder="Quantity" value={form.quantity} onChange={e => setForm({ ...form, quantity: Number(e.target.value) })} required />
          <input className="bg-gray-700 text-gray-100 p-2 rounded" type="number" step="0.01" placeholder="Price" value={form.price} onChange={e => setForm({ ...form, price: Number(e.target.value) })} required />
          <input className="bg-gray-700 text-gray-100 p-2 rounded" type="number" placeholder="Reorder Level" value={form.reorder_level} onChange={e => setForm({ ...form, reorder_level: Number(e.target.value) })} />
          <div className="flex gap-2">
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex-1">
              {editingId ? 'Update' : 'Add'}
            </button>
            {editingId && (
              <button type="button" onClick={() => { setForm(EMPTY_FORM); setEditingId(null); }} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">
                Cancel
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Search & Filter */}
      <div className="flex flex-col md:flex-row gap-3 mb-4">
        <input
          className="bg-gray-800 text-gray-100 p-2 rounded flex-1"
          placeholder="Search by name or SKU..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="bg-gray-800 text-gray-100 p-2 rounded"
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
        >
          <option value="">All Categories</option>
          <option value="low_stock">Low Stock</option>
          <option value="out_of_stock">Out of Stock</option>
          <option value="in_stock">In Stock</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">SKU</th>
              <th className="p-3 text-right">Qty</th>
              <th className="p-3 text-right">Price</th>
              <th className="p-3 text-right">Reorder</th>
              <th className="p-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="p-4 text-center"><div className="flex items-center justify-center gap-2"><div className="animate-spin rounded-full border-2 border-gray-600 border-t-blue-500 h-8 w-8"></div><span>Loading...</span></div></td></tr>
            ) : paged.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-16 text-center">
                <div className="text-5xl mb-4">📦</div>
                <h3 className="text-lg font-semibold text-gray-100 mb-2">No products yet</h3>
                <p className="text-gray-400 mb-4">Get started by adding your first product.</p>
                <button onClick={() => { setForm(EMPTY_FORM); setEditingId(null); }} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                  + Add Product
                </button>
              </td></tr>
            ) : (
              paged.map(item => (
                <tr key={item.id} className="border-t border-gray-700 hover:bg-gray-750">
                  <td className="p-3">{item.name}</td>
                  <td className="p-3">{item.sku}</td>
                  <td className="p-3 text-right">{item.quantity}</td>
                  <td className="p-3 text-right">${item.price.toFixed(2)}</td>
                  <td className="p-3 text-right">{item.reorder_level}</td>
                  <td className="p-3 text-center">
                    <button onClick={() => handleEdit(item)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                    <button onClick={() => setShowDelete(item.id)} className="text-red-400 hover:text-red-300">Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded"
          >
            Prev
          </button>
          <span className="px-3 py-1">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded"
          >
            Next
          </button>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDelete !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-300 mb-4">Are you sure you want to delete this product?</p>
            <div className="flex gap-3">
              <button onClick={handleDelete} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded flex-1">
                Delete
              </button>
              <button onClick={() => setShowDelete(null)} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded flex-1">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
