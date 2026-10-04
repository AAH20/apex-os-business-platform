import React, { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Asset {
  id: number;
  name: string;
  asset_tag: string;
  category_id: number;
  purchase_date: string;
  purchase_cost: number;
  salvage_value: number;
  status: string;
  location?: string;
  description?: string;
}

interface AssetCategory {
  id: number;
  name: string;
  description?: string;
  depreciation_method: string;
  useful_life_years: number;
}

interface MaintenanceSchedule {
  id: number;
  asset_id: number;
  title: string;
  description?: string;
  frequency: string;
  next_due_date: string;
  assigned_to?: string;
  estimated_cost: number;
  status: string;
}

interface DepreciationRecord {
  id: number;
  asset_id: number;
  period_start: string;
  period_end: string;
  depreciation_amount: number;
  accumulated_depreciation: number;
  book_value: number;
}

type Tab = 'assets' | 'categories' | 'maintenance' | 'depreciation';

const EMPTY_ASSET = { name: '', asset_tag: '', category_id: 0, purchase_date: '', purchase_cost: 0, salvage_value: 0, status: 'active', location: '', description: '' };
const EMPTY_CATEGORY = { name: '', description: '', depreciation_method: 'straight_line', useful_life_years: 5 };
const EMPTY_MAINTENANCE = { asset_id: 0, title: '', description: '', frequency: 'monthly', next_due_date: '', assigned_to: '', estimated_cost: 0, status: 'scheduled' };
const EMPTY_DEPRECIATION = { asset_id: 0, period_start: '', period_end: '', depreciation_amount: 0, accumulated_depreciation: 0, book_value: 0 };

const PAGE_SIZE = 10;

export default function AssetManagement() {
  const [tab, setTab] = useState<Tab>('assets');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [categories, setCategories] = useState<AssetCategory[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceSchedule[]>([]);
  const [depreciation, setDepreciation] = useState<DepreciationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showDelete, setShowDelete] = useState<{ type: Tab; id: number } | null>(null);
  const [editing, setEditing] = useState<{ type: Tab; id: number } | null>(null);

  // Form states
  const [assetForm, setAssetForm] = useState({ ...EMPTY_ASSET });
  const [categoryForm, setCategoryForm] = useState({ ...EMPTY_CATEGORY });
  const [maintenanceForm, setMaintenanceForm] = useState({ ...EMPTY_MAINTENANCE });
  const [depreciationForm, setDepreciationForm] = useState({ ...EMPTY_DEPRECIATION });

  // ─── Fetch Helpers ──────────────────────────────────────────────────────────

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { 'X-API-Key': 'test-api-key-12345' };
      const [a, c, m, d] = await Promise.all([
        fetch('/api/assets/', { headers }),
        fetch('/api/assets/categories/', { headers }),
        fetch('/api/assets/maintenance/', { headers }),
        fetch('/api/assets/depreciation/', { headers }),
      ]);
      setAssets(await a.json());
      setCategories(await c.json());
      setMaintenance(await m.json());
      setDepreciation(await d.json());
    } catch {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ─── CRUD Helpers ───────────────────────────────────────────────────────────

  const createItem = async (type: Tab, data: unknown) => {
    const endpoint = type === 'assets' ? '/' : `/${type}/`;
    const res = await fetch(`/api/assets${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Create failed');
  };

  const updateItem = async (type: Tab, id: number, data: unknown) => {
    const endpoint = type === 'assets' ? `/${id}` : `/${type}/${id}`;
    const res = await fetch(`/api/assets${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Update failed');
  };

  const deleteItem = async (type: Tab, id: number) => {
    const endpoint = type === 'assets' ? `/${id}` : `/${type}/${id}`;
    const res = await fetch(`/api/assets${endpoint}`, {
      method: 'DELETE',
      headers: { 'X-API-Key': 'test-api-key-12345' },
    });
    if (!res.ok) throw new Error('Delete failed');
  };

  // ─── Filtered & Paginated Data ──────────────────────────────────────────────

  const getFiltered = () => {
    const q = search.toLowerCase();
    switch (tab) {
      case 'assets':
        return assets.filter(a => a.name.toLowerCase().includes(q) || a.asset_tag.toLowerCase().includes(q));
      case 'categories':
        return categories.filter(c => c.name.toLowerCase().includes(q));
      case 'maintenance':
        return maintenance.filter(m => m.title.toLowerCase().includes(q));
      case 'depreciation':
        return depreciation.filter(d => String(d.asset_id).includes(q));
    }
  };

  const filtered = getFiltered();
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => { setPage(1); }, [search, tab]);

  // ─── Form Handlers ──────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (editing) {
        if (tab === 'assets') await updateItem('assets', editing.id, assetForm);
        else if (tab === 'categories') await updateItem('categories', editing.id, categoryForm);
        else if (tab === 'maintenance') await updateItem('maintenance', editing.id, maintenanceForm);
        else await updateItem('depreciation', editing.id, depreciationForm);
      } else {
        if (tab === 'assets') await createItem('assets', assetForm);
        else if (tab === 'categories') await createItem('categories', categoryForm);
        else if (tab === 'maintenance') await createItem('maintenance', maintenanceForm);
        else await createItem('depreciation', depreciationForm);
      }
      resetForms();
      fetchAll();
    } catch {
      setError('Save failed');
    }
  };

  const resetForms = () => {
    setAssetForm({ ...EMPTY_ASSET });
    setCategoryForm({ ...EMPTY_CATEGORY });
    setMaintenanceForm({ ...EMPTY_MAINTENANCE });
    setDepreciationForm({ ...EMPTY_DEPRECIATION });
    setEditing(null);
  };

  const handleEdit = (type: Tab, item: Asset | AssetCategory | MaintenanceSchedule | DepreciationRecord) => {
    setEditing({ type, id: (item as { id: number }).id });
    if (type === 'assets') setAssetForm(item as typeof assetForm);
    else if (type === 'categories') setCategoryForm(item as typeof categoryForm);
    else if (type === 'maintenance') setMaintenanceForm(item as typeof maintenanceForm);
    else setDepreciationForm(item as typeof depreciationForm);
  };

  const handleDelete = async () => {
    if (!showDelete) return;
    try {
      await deleteItem(showDelete.type, showDelete.id);
      setShowDelete(null);
      fetchAll();
    } catch {
      setError('Delete failed');
    }
  };

  // ─── Render Helpers ─────────────────────────────────────────────────────────

  const getCategoryName = (id: number) => categories.find(c => c.id === id)?.name || `Cat #${id}`;
  const getAssetName = (id: number) => assets.find(a => a.id === id)?.name || `Asset #${id}`;

  const statusColor = (s: string) =>
    s === 'active' ? 'text-emerald-400' : s === 'maintenance' ? 'text-amber-400' : s === 'completed' ? 'text-blue-400' : 'text-gray-400';

  const inputCls = 'bg-gray-700 text-gray-100 p-2 rounded w-full';
  const btnPrimary = 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded';
  const btnDanger = 'bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded';
  const btnCancel = 'bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded';

  // ─── Tab Config ─────────────────────────────────────────────────────────────

  const tabs: { key: Tab; label: string }[] = [
    { key: 'assets', label: 'Assets' },
    { key: 'categories', label: 'Categories' },
    { key: 'maintenance', label: 'Maintenance' },
    { key: 'depreciation', label: 'Depreciation' },
  ];

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">Asset Management</h1>

      {error && <div className="bg-red-900 text-red-200 p-3 rounded mb-4">{error}</div>}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); resetForms(); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <input
        className="bg-gray-800 text-gray-100 p-2 rounded w-full mb-4"
        placeholder="Search..."
        value={search}
        onChange={e => setSearch(e.target.value)}
      />

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-gray-800 p-4 rounded-lg mb-6">
        <h2 className="text-lg font-semibold mb-3">{editing ? 'Edit' : 'Add'} {tab.slice(0, -1)}</h2>

        {tab === 'assets' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className={inputCls} placeholder="Name" value={assetForm.name} onChange={e => setAssetForm({ ...assetForm, name: e.target.value })} required />
            <input className={inputCls} placeholder="Asset Tag" value={assetForm.asset_tag} onChange={e => setAssetForm({ ...assetForm, asset_tag: e.target.value })} required />
            <select className={inputCls} value={assetForm.category_id} onChange={e => setAssetForm({ ...assetForm, category_id: Number(e.target.value) })} required>
              <option value={0}>Select Category</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input className={inputCls} type="date" value={assetForm.purchase_date} onChange={e => setAssetForm({ ...assetForm, purchase_date: e.target.value })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Purchase Cost" value={assetForm.purchase_cost} onChange={e => setAssetForm({ ...assetForm, purchase_cost: Number(e.target.value) })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Salvage Value" value={assetForm.salvage_value} onChange={e => setAssetForm({ ...assetForm, salvage_value: Number(e.target.value) })} />
            <select className={inputCls} value={assetForm.status} onChange={e => setAssetForm({ ...assetForm, status: e.target.value })}>
              <option value="active">Active</option>
              <option value="maintenance">Maintenance</option>
              <option value="retired">Retired</option>
              <option value="disposed">Disposed</option>
            </select>
            <input className={inputCls} placeholder="Location" value={assetForm.location} onChange={e => setAssetForm({ ...assetForm, location: e.target.value })} />
            <input className={inputCls} placeholder="Description" value={assetForm.description} onChange={e => setAssetForm({ ...assetForm, description: e.target.value })} />
          </div>
        )}

        {tab === 'categories' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className={inputCls} placeholder="Name" value={categoryForm.name} onChange={e => setCategoryForm({ ...categoryForm, name: e.target.value })} required />
            <input className={inputCls} placeholder="Description" value={categoryForm.description} onChange={e => setCategoryForm({ ...categoryForm, description: e.target.value })} />
            <select className={inputCls} value={categoryForm.depreciation_method} onChange={e => setCategoryForm({ ...categoryForm, depreciation_method: e.target.value })}>
              <option value="straight_line">Straight Line</option>
              <option value="declining_balance">Declining Balance</option>
              <option value="units_of_production">Units of Production</option>
            </select>
            <input className={inputCls} type="number" placeholder="Useful Life (years)" value={categoryForm.useful_life_years} onChange={e => setCategoryForm({ ...categoryForm, useful_life_years: Number(e.target.value) })} required />
          </div>
        )}

        {tab === 'maintenance' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select className={inputCls} value={maintenanceForm.asset_id} onChange={e => setMaintenanceForm({ ...maintenanceForm, asset_id: Number(e.target.value) })} required>
              <option value={0}>Select Asset</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <input className={inputCls} placeholder="Title" value={maintenanceForm.title} onChange={e => setMaintenanceForm({ ...maintenanceForm, title: e.target.value })} required />
            <input className={inputCls} placeholder="Description" value={maintenanceForm.description} onChange={e => setMaintenanceForm({ ...maintenanceForm, description: e.target.value })} />
            <select className={inputCls} value={maintenanceForm.frequency} onChange={e => setMaintenanceForm({ ...maintenanceForm, frequency: e.target.value })}>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="annually">Annually</option>
            </select>
            <input className={inputCls} type="date" value={maintenanceForm.next_due_date} onChange={e => setMaintenanceForm({ ...maintenanceForm, next_due_date: e.target.value })} required />
            <input className={inputCls} placeholder="Assigned To" value={maintenanceForm.assigned_to} onChange={e => setMaintenanceForm({ ...maintenanceForm, assigned_to: e.target.value })} />
            <input className={inputCls} type="number" step="0.01" placeholder="Estimated Cost" value={maintenanceForm.estimated_cost} onChange={e => setMaintenanceForm({ ...maintenanceForm, estimated_cost: Number(e.target.value) })} />
            <select className={inputCls} value={maintenanceForm.status} onChange={e => setMaintenanceForm({ ...maintenanceForm, status: e.target.value })}>
              <option value="scheduled">Scheduled</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        )}

        {tab === 'depreciation' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select className={inputCls} value={depreciationForm.asset_id} onChange={e => setDepreciationForm({ ...depreciationForm, asset_id: Number(e.target.value) })} required>
              <option value={0}>Select Asset</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <input className={inputCls} type="date" value={depreciationForm.period_start} onChange={e => setDepreciationForm({ ...depreciationForm, period_start: e.target.value })} required />
            <input className={inputCls} type="date" value={depreciationForm.period_end} onChange={e => setDepreciationForm({ ...depreciationForm, period_end: e.target.value })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Depreciation Amount" value={depreciationForm.depreciation_amount} onChange={e => setDepreciationForm({ ...depreciationForm, depreciation_amount: Number(e.target.value) })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Accumulated Depreciation" value={depreciationForm.accumulated_depreciation} onChange={e => setDepreciationForm({ ...depreciationForm, accumulated_depreciation: Number(e.target.value) })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Book Value" value={depreciationForm.book_value} onChange={e => setDepreciationForm({ ...depreciationForm, book_value: Number(e.target.value) })} required />
          </div>
        )}

        <div className="flex gap-2 mt-3">
          <button type="submit" className={btnPrimary}>{editing ? 'Update' : 'Add'}</button>
          {editing && <button type="button" onClick={resetForms} className={btnCancel}>Cancel</button>}
        </div>
      </form>

      {/* Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              {tab === 'assets' && <tr><th className="p-3 text-left">Name</th><th className="p-3 text-left">Tag</th><th className="p-3 text-left">Category</th><th className="p-3 text-right">Cost</th><th className="p-3 text-left">Status</th><th className="p-3 text-center">Actions</th></tr>}
              {tab === 'categories' && <tr><th className="p-3 text-left">Name</th><th className="p-3 text-left">Method</th><th className="p-3 text-right">Life (yrs)</th><th className="p-3 text-center">Actions</th></tr>}
              {tab === 'maintenance' && <tr><th className="p-3 text-left">Title</th><th className="p-3 text-left">Asset</th><th className="p-3 text-left">Frequency</th><th className="p-3 text-left">Next Due</th><th className="p-3 text-left">Status</th><th className="p-3 text-center">Actions</th></tr>}
              {tab === 'depreciation' && <tr><th className="p-3 text-left">Asset</th><th className="p-3 text-left">Period</th><th className="p-3 text-right">Amount</th><th className="p-3 text-right">Accumulated</th><th className="p-3 text-right">Book Value</th><th className="p-3 text-center">Actions</th></tr>}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="p-4 text-center">Loading...</td></tr>
            ) : paged.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-16 text-center">
                <div className="text-5xl mb-4">📦</div>
                <h3 className="text-lg font-semibold text-gray-100 mb-2">No records yet</h3>
                <p className="text-gray-400 mb-4">Get started by adding your first {tab.slice(0, -1)}.</p>
              </td></tr>
            ) : (
              paged.map((item) => {
                if (tab === 'assets') {
                  const a = item as Asset;
                  return (
                    <tr key={a.id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="p-3">{a.name}</td>
                      <td className="p-3">{a.asset_tag}</td>
                      <td className="p-3">{getCategoryName(a.category_id)}</td>
                      <td className="p-3 text-right">${a.purchase_cost.toFixed(2)}</td>
                      <td className={`p-3 ${statusColor(a.status)}`}>{a.status}</td>
                      <td className="p-3 text-center">
                        <button onClick={() => handleEdit('assets', a)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                        <button onClick={() => setShowDelete({ type: 'assets', id: a.id })} className="text-red-400 hover:text-red-300">Delete</button>
                      </td>
                    </tr>
                  );
                }
                if (tab === 'categories') {
                  const c = item as AssetCategory;
                  return (
                    <tr key={c.id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="p-3">{c.name}</td>
                      <td className="p-3">{c.depreciation_method}</td>
                      <td className="p-3 text-right">{c.useful_life_years}</td>
                      <td className="p-3 text-center">
                        <button onClick={() => handleEdit('categories', c)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                        <button onClick={() => setShowDelete({ type: 'categories', id: c.id })} className="text-red-400 hover:text-red-300">Delete</button>
                      </td>
                    </tr>
                  );
                }
                if (tab === 'maintenance') {
                  const m = item as MaintenanceSchedule;
                  return (
                    <tr key={m.id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="p-3">{m.title}</td>
                      <td className="p-3">{getAssetName(m.asset_id)}</td>
                      <td className="p-3">{m.frequency}</td>
                      <td className="p-3">{m.next_due_date}</td>
                      <td className={`p-3 ${statusColor(m.status)}`}>{m.status}</td>
                      <td className="p-3 text-center">
                        <button onClick={() => handleEdit('maintenance', m)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                        <button onClick={() => setShowDelete({ type: 'maintenance', id: m.id })} className="text-red-400 hover:text-red-300">Delete</button>
                      </td>
                    </tr>
                  );
                }
                const d = item as DepreciationRecord;
                return (
                  <tr key={d.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="p-3">{getAssetName(d.asset_id)}</td>
                    <td className="p-3">{d.period_start} → {d.period_end}</td>
                    <td className="p-3 text-right">${d.depreciation_amount.toFixed(2)}</td>
                    <td className="p-3 text-right">${d.accumulated_depreciation.toFixed(2)}</td>
                    <td className="p-3 text-right">${d.book_value.toFixed(2)}</td>
                    <td className="p-3 text-center">
                      <button onClick={() => handleEdit('depreciation', d)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                      <button onClick={() => setShowDelete({ type: 'depreciation', id: d.id })} className="text-red-400 hover:text-red-300">Delete</button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded">Prev</button>
          <span className="px-3 py-1">Page {page} of {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded">Next</button>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-300 mb-4">Are you sure you want to delete this record?</p>
            <div className="flex gap-3">
              <button onClick={handleDelete} className={btnDanger + ' flex-1'}>Delete</button>
              <button onClick={() => setShowDelete(null)} className={btnCancel + ' flex-1'}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
