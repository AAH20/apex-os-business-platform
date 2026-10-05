import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { EmptyState } from '../components/ui';
import { ActionButtons } from '../components/ActionButtons';
import { fetchWithTimeout } from '../api/fallback';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Asset {
  id: number;
  name: string;
  serial_number: string;
  category: string;
  purchase_date: string;
  purchase_cost: number;
  salvage_value: number;
  useful_life_years: number;
  depreciation_method: string;
  status: string;
  location?: string;
  description?: string;
}

interface AssetCategory {
  id: number;
  name: string;
  description?: string;
}

interface MaintenanceSchedule {
  id: number;
  asset_id: number;
  description: string;
  maintenance_type: string;
  scheduled_date: string;
  technician?: string;
  cost: number;
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
  method: string;
}

type Tab = 'assets' | 'categories' | 'maintenance' | 'depreciation';

const EMPTY_ASSET = { name: '', serial_number: '', category: 'other', purchase_date: '', purchase_cost: 0, salvage_value: 0, useful_life_years: 5, depreciation_method: 'straight_line', status: 'active', location: '', description: '' };
const EMPTY_CATEGORY = { name: '', description: '' };
const EMPTY_MAINTENANCE = { asset_id: 0, description: '', maintenance_type: 'preventive', scheduled_date: '', technician: '', cost: 0, status: 'scheduled' };
const EMPTY_DEPRECIATION = { asset_id: 0, period_start: '', period_end: '', depreciation_amount: 0, accumulated_depreciation: 0, book_value: 0, method: 'straight_line' };

const PAGE_SIZE = 10;

export default function AssetManagement() {
  const [tab, setTab] = useState<Tab>('assets');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [assets, setAssets] = useState<Asset[]>([]);
  const [categories, setCategories] = useState<AssetCategory[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceSchedule[]>([]);
  const [depreciation, setDepreciation] = useState<DepreciationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [_searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('');
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
    setError('');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const headers = { 'X-API-Key': 'test-api-key-12345' };
      const [a, c, m, d] = await Promise.all([
        fetchWithTimeout('/api/assets/', { headers, signal: controller.signal }),
        fetchWithTimeout('/api/assets/categories/', { headers, signal: controller.signal }),
        fetchWithTimeout('/api/assets/maintenance/', { headers, signal: controller.signal }),
        fetchWithTimeout('/api/assets/depreciation/', { headers, signal: controller.signal }),
      ]);
      setAssets(await a.json());
      setCategories(await c.json());
      setMaintenance(await m.json());
      setDepreciation(await d.json());
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setError('Request timed out — try again');
      } else {
        setError('Failed to load data');
      }
    } finally {
      clearTimeout(timeout);
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ─── CRUD Helpers ───────────────────────────────────────────────────────────

  const parseError = async (res: Response, fallback: string) => {
    if (res.status === 422) {
      const errData = await res.json().catch(() => null);
      if (errData?.detail) {
        const details = Array.isArray(errData.detail)
          ? errData.detail.map((d: any) => d.msg || d.loc?.join('.') || String(d)).join(', ')
          : String(errData.detail);
        return `Validation: ${details}`;
      }
    }
    return fallback;
  };

  const createItem = async (type: Tab, data: unknown) => {
    const endpoint = type === 'assets' ? '/' : `/${type}/`;
    const res = await fetchWithTimeout(`/api/assets${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await parseError(res, 'Create failed'));
  };

  const updateItem = async (type: Tab, id: number, data: unknown) => {
    const endpoint = type === 'assets' ? `/${id}` : `/${type}/${id}`;
    const res = await fetchWithTimeout(`/api/assets${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await parseError(res, 'Update failed'));
  };

  const deleteItem = async (type: Tab, id: number) => {
    const endpoint = type === 'assets' ? `/${id}` : `/${type}/${id}`;
    const res = await fetchWithTimeout(`/api/assets${endpoint}`, {
      method: 'DELETE',
      headers: { 'X-API-Key': 'test-api-key-12345' },
    });
    if (!res.ok) throw new Error('Delete failed');
  };

  // ─── Filtered & Paginated Data ──────────────────────────────────────────────

  const getFiltered = () => {
    const q = search.toLowerCase();
    let items: any[];
    switch (tab) {
      case 'assets':
        items = assets.filter(a => a.name.toLowerCase().includes(q) || a.serial_number.toLowerCase().includes(q));
        if (filter) items = items.filter(a => a.status === filter);
        return items;
      case 'categories':
        items = categories.filter(c => c.name.toLowerCase().includes(q));
        return items;
      case 'maintenance':
        items = maintenance.filter(m => m.description.toLowerCase().includes(q));
        if (filter) items = items.filter(m => m.status === filter);
        return items;
      case 'depreciation':
        items = depreciation.filter(d => String(d.asset_id).includes(q));
        return items;
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


  const getCurrentData = () => {
    return filtered;
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
    a.download = 'assetmanagement_export.csv';
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
    a.download = 'assetmanagement_export.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRefresh = () => {
    fetchAll();
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} selected item(s)?`)) return;
    setSelectedIds(new Set());
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">Asset Management</h1>
        <ActionButtons
          onSearch={handleSearch}
          onExportCSV={handleExportCSV}
          onExportJSON={handleExportJSON}
          onRefresh={handleRefresh}
          onBulkDelete={handleBulkDelete}
          selectedCount={selectedIds.size}
          searchPlaceholder="Search assets..."
        />

      {error && <div className="bg-red-900 text-red-200 p-3 rounded mb-4 flex items-center justify-between"><span>{error}</span><button onClick={fetchAll} className="ml-4 rounded bg-red-800 px-3 py-1 text-xs font-medium hover:bg-red-700">Retry</button></div>}

      {/* Dashboard */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Dashboard</h2>
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Total Assets</p>
            <p className="text-2xl font-bold text-blue-400">{assets.length}</p>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Active Categories</p>
            <p className="text-2xl font-bold text-emerald-400">{categories.length}</p>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Scheduled Maintenance</p>
            <p className="text-2xl font-bold text-amber-400">{maintenance.filter(m => m.status === 'scheduled').length}</p>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Depreciation Records</p>
            <p className="text-2xl font-bold text-purple-400">{depreciation.length}</p>
          </div>
        </div>
        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 p-4 rounded-lg">
            <h3 className="text-sm font-semibold mb-3 text-gray-300">Assets by Category</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categories.map(c => ({ name: c.name, count: assets.filter(a => a.category === c.name).length }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', color: '#F3F4F6' }} />
                <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <h3 className="text-sm font-semibold mb-3 text-gray-300">Maintenance by Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={['scheduled', 'in_progress', 'completed', 'cancelled'].map(s => ({
                    name: s.replace('_', ' '),
                    value: maintenance.filter(m => m.status === s).length,
                  })).filter(d => d.value > 0)}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name} (${value})`}
                >
                  {['#F59E0B', '#3B82F6', '#10B981', '#EF4444'].map((color, i) => (
                    <Cell key={i} fill={color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', color: '#F3F4F6' }} />
                <Legend wrapperStyle={{ color: '#D1D5DB', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

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

      {/* Search & Filter */}
      <div className="flex gap-3 mb-4">
        <input
          className="bg-gray-800 text-gray-100 p-2 rounded flex-1"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="bg-gray-800 text-gray-100 p-2 rounded"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        >
          <option value="">All</option>
          {tab === 'assets' && <><option value="active">Active</option><option value="in_maintenance">In Maintenance</option><option value="idle">Idle</option><option value="retired">Retired</option><option value="disposed">Disposed</option></>}
          {tab === 'maintenance' && <><option value="scheduled">Scheduled</option><option value="in_progress">In Progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option><option value="overdue">Overdue</option></>}
        </select>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-gray-800 p-4 rounded-lg mb-6">
        <h2 className="text-lg font-semibold mb-3">{editing ? 'Edit' : 'Add'} {tab.slice(0, -1)}</h2>

        {tab === 'assets' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className={inputCls} placeholder="Name" value={assetForm.name} onChange={e => setAssetForm({ ...assetForm, name: e.target.value })} required />
            <input className={inputCls} placeholder="Serial Number" value={assetForm.serial_number} onChange={e => setAssetForm({ ...assetForm, serial_number: e.target.value })} required />
            <select className={inputCls} value={assetForm.category} onChange={e => setAssetForm({ ...assetForm, category: e.target.value })} required>
              <option value="vehicle">Vehicle</option>
              <option value="machinery">Machinery</option>
              <option value="furniture">Furniture</option>
              <option value="electronics">Electronics</option>
              <option value="building">Building</option>
              <option value="land">Land</option>
              <option value="software">Software</option>
              <option value="other">Other</option>
            </select>
            <input className={inputCls} type="date" value={assetForm.purchase_date} onChange={e => setAssetForm({ ...assetForm, purchase_date: e.target.value })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Purchase Cost" value={assetForm.purchase_cost} onChange={e => setAssetForm({ ...assetForm, purchase_cost: Number(e.target.value) })} required />
            <input className={inputCls} type="number" step="0.01" placeholder="Salvage Value" value={assetForm.salvage_value} onChange={e => setAssetForm({ ...assetForm, salvage_value: Number(e.target.value) })} />
            <input className={inputCls} type="number" placeholder="Useful Life (years)" value={assetForm.useful_life_years} onChange={e => setAssetForm({ ...assetForm, useful_life_years: Number(e.target.value) })} required />
            <select className={inputCls} value={assetForm.depreciation_method} onChange={e => setAssetForm({ ...assetForm, depreciation_method: e.target.value })}>
              <option value="straight_line">Straight Line</option>
              <option value="declining_balance">Declining Balance</option>
              <option value="sum_of_years_digits">Sum of Years Digits</option>
              <option value="units_of_production">Units of Production</option>
            </select>
            <select className={inputCls} value={assetForm.status} onChange={e => setAssetForm({ ...assetForm, status: e.target.value })}>
              <option value="active">Active</option>
              <option value="in_maintenance">In Maintenance</option>
              <option value="idle">Idle</option>
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
          </div>
        )}

        {tab === 'maintenance' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select className={inputCls} value={maintenanceForm.asset_id} onChange={e => setMaintenanceForm({ ...maintenanceForm, asset_id: Number(e.target.value) })} required>
              <option value={0}>Select Asset</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <input className={inputCls} placeholder="Description" value={maintenanceForm.description} onChange={e => setMaintenanceForm({ ...maintenanceForm, description: e.target.value })} required />
            <select className={inputCls} value={maintenanceForm.maintenance_type} onChange={e => setMaintenanceForm({ ...maintenanceForm, maintenance_type: e.target.value })}>
              <option value="preventive">Preventive</option>
              <option value="corrective">Corrective</option>
              <option value="predictive">Predictive</option>
              <option value="inspection">Inspection</option>
            </select>
            <input className={inputCls} type="date" value={maintenanceForm.scheduled_date} onChange={e => setMaintenanceForm({ ...maintenanceForm, scheduled_date: e.target.value })} required />
            <input className={inputCls} placeholder="Technician" value={maintenanceForm.technician} onChange={e => setMaintenanceForm({ ...maintenanceForm, technician: e.target.value })} />
            <input className={inputCls} type="number" step="0.01" placeholder="Cost" value={maintenanceForm.cost} onChange={e => setMaintenanceForm({ ...maintenanceForm, cost: Number(e.target.value) })} />
            <select className={inputCls} value={maintenanceForm.status} onChange={e => setMaintenanceForm({ ...maintenanceForm, status: e.target.value })}>
              <option value="scheduled">Scheduled</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
              <option value="overdue">Overdue</option>
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
            <select className={inputCls} value={depreciationForm.method} onChange={e => setDepreciationForm({ ...depreciationForm, method: e.target.value })}>
              <option value="straight_line">Straight Line</option>
              <option value="declining_balance">Declining Balance</option>
              <option value="sum_of_years_digits">Sum of Years Digits</option>
              <option value="units_of_production">Units of Production</option>
            </select>
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
            {tab === 'assets' && <tr><th className="p-3 text-left">Name</th><th className="p-3 text-left">Serial</th><th className="p-3 text-left">Category</th><th className="p-3 text-right">Cost</th><th className="p-3 text-left">Status</th><th className="p-3 text-center">Actions</th></tr>}
            {tab === 'categories' && <tr><th className="p-3 text-left">Name</th><th className="p-3 text-center">Actions</th></tr>}
            {tab === 'maintenance' && <tr><th className="p-3 text-left">Description</th><th className="p-3 text-left">Asset</th><th className="p-3 text-left">Type</th><th className="p-3 text-left">Scheduled</th><th className="p-3 text-left">Status</th><th className="p-3 text-center">Actions</th></tr>}
            {tab === 'depreciation' && <tr><th className="p-3 text-left">Asset</th><th className="p-3 text-left">Period</th><th className="p-3 text-right">Amount</th><th className="p-3 text-right">Accumulated</th><th className="p-3 text-right">Book Value</th><th className="p-3 text-center">Actions</th></tr>}
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="p-4 text-center"><div className="flex items-center justify-center gap-2"><div className="animate-spin rounded-full border-2 border-gray-600 border-t-blue-500 h-8 w-8"></div><span>Loading...</span></div></td></tr>
            ) : paged.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-16 text-center">
                <EmptyState message={`No ${tab.slice(0, -1)} records yet`} />
              </td></tr>
            ) : (
              paged.map((item) => {
                if (tab === 'assets') {
                  const a = item as Asset;
                  return (
                    <tr key={a.id} className="border-t border-gray-700 hover:bg-gray-600">
                      <td className="p-3">{a.name}</td>
                      <td className="p-3">{a.serial_number}</td>
                      <td className="p-3">{a.category}</td>
                      <td className="p-3 text-right">${(a.purchase_cost ?? 0).toFixed(2)}</td>
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
                    <tr key={c.id} className="border-t border-gray-700 hover:bg-gray-600">
                      <td className="p-3">{c.name}</td>
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
                    <tr key={m.id} className="border-t border-gray-700 hover:bg-gray-600">
                      <td className="p-3">{m.description}</td>
                      <td className="p-3">{getAssetName(m.asset_id)}</td>
                      <td className="p-3">{m.maintenance_type}</td>
                      <td className="p-3">{m.scheduled_date}</td>
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
                  <tr key={d.id} className="border-t border-gray-700 hover:bg-gray-600">
                    <td className="p-3">{getAssetName(d.asset_id)}</td>
                    <td className="p-3">{d.period_start} → {d.period_end}</td>
                    <td className="p-3 text-right">${(d.depreciation_amount ?? 0).toFixed(2)}</td>
                    <td className="p-3 text-right">${(d.accumulated_depreciation ?? 0).toFixed(2)}</td>
                    <td className="p-3 text-right">${(d.book_value ?? 0).toFixed(2)}</td>
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
