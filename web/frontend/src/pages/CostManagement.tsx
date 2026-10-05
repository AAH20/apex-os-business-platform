import React, { useState, useEffect, useCallback } from 'react'
import { fetchWithTimeout } from '../api/fallback';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { exportToCSV } from '../hooks/useKeyboardShortcuts'

// ─── Types ──────────────────────────────────────────────────────────────────

interface CostCenter {
  id: number;
  name: string;
  code: string;
  manager?: string;
  department?: string;
  created_at: string;
}

interface CostAllocation {
  id: number;
  cost_center_id: number;
  allocation_name: string;
  amount: number;
  period?: string;
  description?: string;
  created_at: string;
}

interface CostForecast {
  id: number;
  cost_center_id: number;
  forecast_name: string;
  period: string;
  forecast_amount: number;
  actual_amount: number;
  created_at: string;
}

interface CostVariance {
  id: number;
  cost_center_id: number;
  period: string;
  budgeted_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_percent: number;
  status: string;
  notes?: string;
  created_at: string;
}

type TabKey = 'cost-centers' | 'allocations' | 'forecasts' | 'variances';

const API_BASE = '/api/cost-management';

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetchWithTimeout(url, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

const emptyCCForm = { name: '', code: '', manager: '', department: '' };
const emptyAllocForm = { cost_center_id: 0, allocation_name: '', amount: 0, period: '', description: '' };
const emptyForecastForm = { cost_center_id: 0, forecast_name: '', period: '', forecast_amount: 0, actual_amount: 0 };
const emptyVarianceForm = { cost_center_id: 0, period: '', budgeted_amount: 0, actual_amount: 0, variance_amount: 0, variance_percent: 0, status: 'on_budget', notes: '' };

const statusColors: Record<string, string> = {
  under_budget: 'bg-blue-900 text-blue-300',
  on_budget: 'bg-green-900 text-green-300',
  over_budget: 'bg-red-900 text-red-300',
};

const fmt = (n: number) => n == null ? '$0.00' : `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function CostManagement() {
  const [activeTab, setActiveTab] = useState<TabKey>('cost-centers');
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [allocations, setAllocations] = useState<CostAllocation[]>([]);
  const [forecasts, setForecasts] = useState<CostForecast[]>([]);
  const [variances, setVariances] = useState<CostVariance[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const [ccForm, setCCForm] = useState(emptyCCForm);
  const [allocForm, setAllocForm] = useState(emptyAllocForm);
  const [forecastForm, setForecastForm] = useState(emptyForecastForm);
  const [varianceForm, setVarianceForm] = useState(emptyVarianceForm);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [cc, alloc, fc, v] = await Promise.all([
        apiFetch<CostCenter[]>(`${API_BASE}/cost-centers/`),
        apiFetch<CostAllocation[]>(`${API_BASE}/cost-allocations/`),
        apiFetch<CostForecast[]>(`${API_BASE}/cost-forecasts/`),
        apiFetch<CostVariance[]>(`${API_BASE}/cost-variances/`),
      ]);
      setCostCenters(cc); setAllocations(alloc); setForecasts(fc); setVariances(v);
    } catch (e: any) { setError(e.message || 'Failed to fetch'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDelete = async (id: number) => {
    setError('');
    try {
      const url = activeTab === 'cost-centers' ? `${API_BASE}/cost-centers/${id}`
        : activeTab === 'allocations' ? `${API_BASE}/cost-allocations/${id}`
        : activeTab === 'forecasts' ? `${API_BASE}/cost-forecasts/${id}`
        : `${API_BASE}/cost-variances/${id}`;
      await apiFetch(url, { method: 'DELETE' });
      setShowDeleteConfirm(null); fetchAll();
    } catch (e: any) { setError(e.message || 'Delete failed'); }
  };

  const handleSubmitCC = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/cost-centers/${editingId}` : `${API_BASE}/cost-centers/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(ccForm) });
      setCCForm(emptyCCForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitAlloc = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/cost-allocations/${editingId}` : `${API_BASE}/cost-allocations/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(allocForm) });
      setAllocForm(emptyAllocForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitForecast = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/cost-forecasts/${editingId}` : `${API_BASE}/cost-forecasts/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(forecastForm) });
      setForecastForm(emptyForecastForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitVariance = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/cost-variances/${editingId}` : `${API_BASE}/cost-variances/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(varianceForm) });
      setVarianceForm(emptyVarianceForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const startEdit = (id: number) => {
    setEditingId(id);
    if (activeTab === 'cost-centers') {
      const c = costCenters.find(x => x.id === id);
      if (c) setCCForm({ name: c.name, code: c.code, manager: c.manager || '', department: c.department || '' });
    } else if (activeTab === 'allocations') {
      const a = allocations.find(x => x.id === id);
      if (a) setAllocForm({ cost_center_id: a.cost_center_id, allocation_name: a.allocation_name, amount: a.amount, period: a.period || '', description: a.description || '' });
    } else if (activeTab === 'forecasts') {
      const f = forecasts.find(x => x.id === id);
      if (f) setForecastForm({ cost_center_id: f.cost_center_id, forecast_name: f.forecast_name, period: f.period, forecast_amount: f.forecast_amount, actual_amount: f.actual_amount });
    } else {
      const v = variances.find(x => x.id === id);
      if (v) setVarianceForm({ cost_center_id: v.cost_center_id, period: v.period, budgeted_amount: v.budgeted_amount, actual_amount: v.actual_amount, variance_amount: v.variance_amount, variance_percent: v.variance_percent, status: v.status, notes: v.notes || '' });
    }
    setShowForm(true);
  };

  const cancelForm = () => { setShowForm(false); setEditingId(null); setError(''); };

  const getCurrentData = (): any[] => {
    if (activeTab === 'cost-centers') return costCenters;
    if (activeTab === 'allocations') return allocations;
    if (activeTab === 'forecasts') return forecasts;
    return variances;
  };

  const getSearchableFields = (item: any): string => {
    return Object.values(item).join(' ').toLowerCase();
  };

  const filteredData = getCurrentData().filter(item => {
    const matchesSearch = !searchQuery || getSearchableFields(item).includes(searchQuery.toLowerCase());
    const matchesStatus = !filterStatus || item.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const exportCSV = () => {
    const data = filteredData;
    if (data.length === 0) return;
    const headers = Object.keys(data[0]);
    const csv = [headers.join(','), ...data.map(item => headers.map(h => JSON.stringify(item[h] ?? '')).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${activeTab}_export.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    const data = filteredData;
    if (data.length === 0) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${activeTab}_export.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'cost-centers', label: 'Cost Centers' },
    { key: 'allocations', label: 'Allocations' },
    { key: 'forecasts', label: 'Forecasts' },
    { key: 'variances', label: 'Variances' },
  ];

  const inputCls = 'w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500';
  const labelCls = 'block text-sm font-medium text-gray-300 mb-1';
  const btnPrimary = 'bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700';
  const btnDanger = 'bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700';
  const btnCancel = 'bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-500';

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Cost Management</h1>
      {error && <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">{error}</div>}

      {/* Dashboard */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-100 mb-3">Dashboard</h2>
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Cost Centers</div>
            <div className="text-2xl font-bold text-gray-100">{costCenters.length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Total Allocations</div>
            <div className="text-2xl font-bold text-gray-100">{fmt((allocations || []).reduce((s, a) => s + (a.amount ?? 0), 0))}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Forecast Total</div>
            <div className="text-2xl font-bold text-gray-100">{fmt((forecasts || []).reduce((s, f) => s + (f.forecast_amount ?? 0), 0))}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Variance Alerts</div>
            <div className="text-2xl font-bold text-red-400">{variances.filter(v => v.status === 'over_budget').length}</div>
          </div>
        </div>
        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Allocations by Cost Center</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={costCenters.map(cc => ({
                name: cc.code,
                total: (allocations || []).filter(a => a.cost_center_id === cc.id).reduce((s, a) => s + (a.amount ?? 0), 0),
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Bar dataKey="total" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Variance by Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={Object.entries((variances || []).reduce((acc, v) => { acc[v.status] = (acc[v.status] || 0) + 1; return acc; }, {} as Record<string, number>)).map(([status, count]) => ({ status, count }))} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={80} label>
                  {Object.entries(variances.reduce((acc, v) => { acc[v.status] = (acc[v.status] || 0) + 1; return acc; }, {} as Record<string, number>)).map((_, i) => (
                    <Cell key={i} fill={['#10b981', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6'][i % 5]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setActiveTab(t.key); setShowForm(false); setEditingId(null); }}
            className={`px-4 py-2 rounded font-medium ${activeTab === t.key ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-4">
        <button onClick={() => { setShowForm(true); setEditingId(null); }} className={btnPrimary}>+ New {activeTab === 'cost-centers' ? 'Cost Center' : activeTab === 'allocations' ? 'Allocation' : activeTab === 'forecasts' ? 'Forecast' : 'Variance'}</button>
        <button onClick={fetchAll} className="bg-gray-700 text-gray-300 px-4 py-2 rounded hover:bg-gray-600">Refresh</button>
        <button onClick={() => { const data = activeTab === 'cost-centers' ? costCenters : activeTab === 'allocations' ? allocations : activeTab === 'forecasts' ? forecasts : variances; exportToCSV(data as unknown as Record<string, unknown>[], `${activeTab}_export.csv`); }} className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600">Export CSV</button>
      </div>

      {/* Search, Filter & Export */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
        />
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          {activeTab === 'variances' && <><option value="under_budget">Under Budget</option><option value="on_budget">On Budget</option><option value="over_budget">Over Budget</option></>}
        </select>
        <button onClick={exportCSV} className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600">Export CSV</button>
        <button onClick={exportJSON} className="bg-indigo-700 text-white px-4 py-2 rounded hover:bg-indigo-600">Export JSON</button>
      </div>

      {/* Forms */}
      {showForm && activeTab === 'cost-centers' && (
        <form onSubmit={handleSubmitCC} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Cost Center' : 'Create Cost Center'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <div><label className={labelCls}>Name</label><input className={inputCls} value={ccForm.name} onChange={e => setCCForm({ ...ccForm, name: e.target.value })} required /></div>
            <div><label className={labelCls}>Code</label><input className={inputCls} value={ccForm.code} onChange={e => setCCForm({ ...ccForm, code: e.target.value })} required /></div>
            <div><label className={labelCls}>Manager</label><input className={inputCls} value={ccForm.manager} onChange={e => setCCForm({ ...ccForm, manager: e.target.value })} /></div>
            <div><label className={labelCls}>Department</label><input className={inputCls} value={ccForm.department} onChange={e => setCCForm({ ...ccForm, department: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'allocations' && (
        <form onSubmit={handleSubmitAlloc} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Allocation' : 'Create Allocation'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Cost Center</label><select className={inputCls} value={allocForm.cost_center_id} onChange={e => setAllocForm({ ...allocForm, cost_center_id: +e.target.value })}><option value={0}>Select...</option>{costCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div><label className={labelCls}>Allocation Name</label><input className={inputCls} value={allocForm.allocation_name} onChange={e => setAllocForm({ ...allocForm, allocation_name: e.target.value })} required /></div>
            <div><label className={labelCls}>Amount</label><input type="number" step="0.01" className={inputCls} value={allocForm.amount} onChange={e => setAllocForm({ ...allocForm, amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Period</label><input className={inputCls} placeholder="e.g. 2026-Q1" value={allocForm.period} onChange={e => setAllocForm({ ...allocForm, period: e.target.value })} /></div>
            <div><label className={labelCls}>Description</label><input className={inputCls} value={allocForm.description} onChange={e => setAllocForm({ ...allocForm, description: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'forecasts' && (
        <form onSubmit={handleSubmitForecast} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Forecast' : 'Create Forecast'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Cost Center</label><select className={inputCls} value={forecastForm.cost_center_id} onChange={e => setForecastForm({ ...forecastForm, cost_center_id: +e.target.value })}><option value={0}>Select...</option>{costCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div><label className={labelCls}>Forecast Name</label><input className={inputCls} value={forecastForm.forecast_name} onChange={e => setForecastForm({ ...forecastForm, forecast_name: e.target.value })} required /></div>
            <div><label className={labelCls}>Period</label><input className={inputCls} value={forecastForm.period} onChange={e => setForecastForm({ ...forecastForm, period: e.target.value })} required /></div>
            <div><label className={labelCls}>Forecast Amount</label><input type="number" step="0.01" className={inputCls} value={forecastForm.forecast_amount} onChange={e => setForecastForm({ ...forecastForm, forecast_amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Actual Amount</label><input type="number" step="0.01" className={inputCls} value={forecastForm.actual_amount} onChange={e => setForecastForm({ ...forecastForm, actual_amount: +e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'variances' && (
        <form onSubmit={handleSubmitVariance} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Variance' : 'Create Variance'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Cost Center</label><select className={inputCls} value={varianceForm.cost_center_id} onChange={e => setVarianceForm({ ...varianceForm, cost_center_id: +e.target.value })}><option value={0}>Select...</option>{costCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div><label className={labelCls}>Period</label><input className={inputCls} value={varianceForm.period} onChange={e => setVarianceForm({ ...varianceForm, period: e.target.value })} required /></div>
            <div><label className={labelCls}>Budgeted Amount</label><input type="number" step="0.01" className={inputCls} value={varianceForm.budgeted_amount} onChange={e => setVarianceForm({ ...varianceForm, budgeted_amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Actual Amount</label><input type="number" step="0.01" className={inputCls} value={varianceForm.actual_amount} onChange={e => setVarianceForm({ ...varianceForm, actual_amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Variance Amount</label><input type="number" step="0.01" className={inputCls} value={varianceForm.variance_amount} onChange={e => setVarianceForm({ ...varianceForm, variance_amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Variance %</label><input type="number" step="0.01" className={inputCls} value={varianceForm.variance_percent} onChange={e => setVarianceForm({ ...varianceForm, variance_percent: +e.target.value })} /></div>
            <div><label className={labelCls}>Status</label><select className={inputCls} value={varianceForm.status} onChange={e => setVarianceForm({ ...varianceForm, status: e.target.value })}><option value="under_budget">Under Budget</option><option value="on_budget">On Budget</option><option value="over_budget">Over Budget</option></select></div>
            <div><label className={labelCls}>Notes</label><input className={inputCls} value={varianceForm.notes} onChange={e => setVarianceForm({ ...varianceForm, notes: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {/* Tables */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="px-4 py-8 text-center text-gray-400">Loading...</div>
        ) : activeTab === 'cost-centers' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Code</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Manager</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Department</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No cost centers found</td></tr>
              ) : filteredData.map(c => (
                <tr key={c.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{c.name}</td>
                  <td className="px-4 py-3 text-gray-300">{c.code}</td>
                  <td className="px-4 py-3 text-gray-300">{c.manager || '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{c.department || '—'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(c.id)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(c.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : activeTab === 'allocations' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Cost Center</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Amount</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No allocations found</td></tr>
              ) : filteredData.map(a => (
                <tr key={a.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{a.allocation_name}</td>
                  <td className="px-4 py-3 text-gray-300">{costCenters.find(c => c.id === a.cost_center_id)?.name || '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{a.period || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(a.amount)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(a.id)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(a.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : activeTab === 'forecasts' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Cost Center</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Forecast</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actual</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No forecasts found</td></tr>
              ) : filteredData.map(f => (
                <tr key={f.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{f.forecast_name}</td>
                  <td className="px-4 py-3 text-gray-300">{costCenters.find(c => c.id === f.cost_center_id)?.name || '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{f.period}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(f.forecast_amount)}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(f.actual_amount)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(f.id)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(f.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Cost Center</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Budgeted</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actual</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Variance</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No variances found</td></tr>
              ) : filteredData.map(v => (
                <tr key={v.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{costCenters.find(c => c.id === v.cost_center_id)?.name || '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{v.period}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(v.budgeted_amount)}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(v.actual_amount)}</td>
                  <td className={`px-4 py-3 text-right ${v.variance_amount < 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(v.variance_amount)}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[v.status] || 'bg-gray-700 text-gray-300'}`}>{v.status.replace('_', ' ')}</span></td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(v.id)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(v.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-100 mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this item? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className={btnCancel}>Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className={btnDanger}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}