import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend } from 'recharts';
import { exportToCSV } from '../hooks/useKeyboardShortcuts';

// ─── Types ──────────────────────────────────────────────────────────────────

interface CapacityPlan {
  id: number;
  name: string;
  status: string;
  start_date?: string;
  end_date?: string;
  total_budget: number;
  currency: string;
  notes?: string;
  created_at: string;
}

interface ResourceAllocation {
  id: number;
  plan_id: number;
  resource_type: string;
  resource_name: string;
  allocated_units: number;
  utilized_units: number;
  unit?: string;
  cost_per_unit: number;
  created_at: string;
}

interface Forecast {
  id: number;
  plan_id: number;
  metric: string;
  period: string;
  forecast_value: number;
  confidence_lower?: number;
  confidence_upper?: number;
  model?: string;
  created_at: string;
}

interface Scenario {
  id: number;
  plan_id: number;
  name: string;
  description?: string;
  assumptions?: string;
  probability: number;
  impact: string;
  created_at: string;
}

type TabKey = 'plans' | 'allocations' | 'forecasts' | 'scenarios';

const API_BASE = '/api/capacity-planning';

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

const emptyPlanForm = { name: '', status: 'draft', start_date: '', end_date: '', total_budget: 0, currency: 'USD', notes: '' };
const emptyAllocForm = { plan_id: 0, resource_type: '', resource_name: '', allocated_units: 0, utilized_units: 0, unit: '', cost_per_unit: 0 };
const emptyForecastForm = { plan_id: 0, metric: '', period: '', forecast_value: 0, confidence_lower: 0, confidence_upper: 0, model: '' };
const emptyScenarioForm = { plan_id: 0, name: '', description: '', assumptions: '', probability: 0.5, impact: 'medium' };

const statusColors: Record<string, string> = {
  active: 'bg-green-900 text-green-300',
  draft: 'bg-yellow-900 text-yellow-300',
  archived: 'bg-gray-700 text-gray-300',
  low: 'bg-blue-900 text-blue-300',
  medium: 'bg-yellow-900 text-yellow-300',
  high: 'bg-orange-900 text-orange-300',
  critical: 'bg-red-900 text-red-300',
};

const fmt = (n: number) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtNum = (n: number) => n.toLocaleString('en-US');

export default function CapacityPlanningManagement() {
  const [activeTab, setActiveTab] = useState<TabKey>('plans');
  const [plans, setPlans] = useState<CapacityPlan[]>([]);
  const [allocations, setAllocations] = useState<ResourceAllocation[]>([]);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const [planForm, setPlanForm] = useState(emptyPlanForm);
  const [allocForm, setAllocForm] = useState(emptyAllocForm);
  const [forecastForm, setForecastForm] = useState(emptyForecastForm);
  const [scenarioForm, setScenarioForm] = useState(emptyScenarioForm);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [p, a, f, s] = await Promise.all([
        apiFetch<CapacityPlan[]>(`${API_BASE}/capacity-plans/`),
        apiFetch<ResourceAllocation[]>(`${API_BASE}/resource-allocations/`),
        apiFetch<Forecast[]>(`${API_BASE}/forecasts/`),
        apiFetch<Scenario[]>(`${API_BASE}/scenarios/`),
      ]);
      setPlans(p); setAllocations(a); setForecasts(f); setScenarios(s);
    } catch (e: any) { setError(e.message || 'Failed to fetch'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDelete = async (id: number) => {
    setError('');
    try {
      const url = activeTab === 'plans' ? `${API_BASE}/capacity-plans/${id}`
        : activeTab === 'allocations' ? `${API_BASE}/resource-allocations/${id}`
        : activeTab === 'forecasts' ? `${API_BASE}/forecasts/${id}`
        : `${API_BASE}/scenarios/${id}`;
      await apiFetch(url, { method: 'DELETE' });
      setShowDeleteConfirm(null); fetchAll();
    } catch (e: any) { setError(e.message || 'Delete failed'); }
  };

  const handleSubmitPlan = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/capacity-plans/${editingId}` : `${API_BASE}/capacity-plans/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(planForm) });
      setPlanForm(emptyPlanForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitAlloc = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/resource-allocations/${editingId}` : `${API_BASE}/resource-allocations/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(allocForm) });
      setAllocForm(emptyAllocForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitForecast = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/forecasts/${editingId}` : `${API_BASE}/forecasts/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(forecastForm) });
      setForecastForm(emptyForecastForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitScenario = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/scenarios/${editingId}` : `${API_BASE}/scenarios/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(scenarioForm) });
      setScenarioForm(emptyScenarioForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const startEdit = (id: number) => {
    setEditingId(id);
    if (activeTab === 'plans') {
      const p = plans.find(x => x.id === id);
      if (p) setPlanForm({ name: p.name, status: p.status, start_date: p.start_date || '', end_date: p.end_date || '', total_budget: p.total_budget, currency: p.currency, notes: p.notes || '' });
    } else if (activeTab === 'allocations') {
      const a = allocations.find(x => x.id === id);
      if (a) setAllocForm({ plan_id: a.plan_id, resource_type: a.resource_type, resource_name: a.resource_name, allocated_units: a.allocated_units, utilized_units: a.utilized_units, unit: a.unit || '', cost_per_unit: a.cost_per_unit });
    } else if (activeTab === 'forecasts') {
      const f = forecasts.find(x => x.id === id);
      if (f) setForecastForm({ plan_id: f.plan_id, metric: f.metric, period: f.period, forecast_value: f.forecast_value, confidence_lower: f.confidence_lower || 0, confidence_upper: f.confidence_upper || 0, model: f.model || '' });
    } else {
      const s = scenarios.find(x => x.id === id);
      if (s) setScenarioForm({ plan_id: s.plan_id, name: s.name, description: s.description || '', assumptions: s.assumptions || '', probability: s.probability, impact: s.impact });
    }
    setShowForm(true);
  };

  const cancelForm = () => { setShowForm(false); setEditingId(null); setError(''); };

  const getCurrentData = (): any[] => {
    if (activeTab === 'plans') return plans;
    if (activeTab === 'allocations') return allocations;
    if (activeTab === 'forecasts') return forecasts;
    return scenarios;
  };

  const getSearchableFields = (item: any): string => {
    return Object.values(item).join(' ').toLowerCase();
  };

  const filteredData = getCurrentData().filter(item => {
    const matchesSearch = !searchQuery || getSearchableFields(item).includes(searchQuery.toLowerCase());
    const matchesStatus = !filterStatus || item.status === filterStatus || item.impact === filterStatus;
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

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'plans', label: 'Capacity Plans' },
    { key: 'allocations', label: 'Resource Allocations' },
    { key: 'forecasts', label: 'Forecasts' },
    { key: 'scenarios', label: 'Scenarios' },
  ];

  const inputCls = 'w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500';
  const labelCls = 'block text-sm font-medium text-gray-300 mb-1';
  const btnPrimary = 'bg-cyan-600 text-white px-4 py-2 rounded hover:bg-cyan-700';
  const btnDanger = 'bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700';
  const btnCancel = 'bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-500';

  // Chart data
  const utilizationData = allocations.map(a => ({
    name: a.resource_name.length > 15 ? a.resource_name.substring(0, 15) + '...' : a.resource_name,
    allocated: a.allocated_units,
    utilized: a.utilized_units,
    utilization_rate: a.allocated_units > 0 ? Math.round((a.utilized_units / a.allocated_units) * 100) : 0,
  }));

  const forecastData = forecasts.map(f => ({
    metric: f.metric.length > 12 ? f.metric.substring(0, 12) + '...' : f.metric,
    forecast: f.forecast_value,
    lower: f.confidence_lower || f.forecast_value * 0.9,
    upper: f.confidence_upper || f.forecast_value * 1.1,
  }));

  const scenarioImpactData = Object.entries(scenarios.reduce((acc, s) => { acc[s.impact] = (acc[s.impact] || 0) + 1; return acc; }, {} as Record<string, number>)).map(([impact, count]) => ({ impact, count }));

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Capacity Planning</h1>
      {error && <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">{error}</div>}

      {/* Dashboard */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-100 mb-3">Dashboard</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Active Plans</div>
            <div className="text-2xl font-bold text-gray-100">{plans.filter(p => p.status === 'active').length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Resource Allocations</div>
            <div className="text-2xl font-bold text-gray-100">{allocations.length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Forecasts</div>
            <div className="text-2xl font-bold text-gray-100">{forecasts.length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Scenarios</div>
            <div className="text-2xl font-bold text-gray-100">{scenarios.length}</div>
          </div>
        </div>
        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Resource Utilization</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={utilizationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Legend />
                <Bar dataKey="allocated" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Allocated" />
                <Bar dataKey="utilized" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Utilized" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Forecast Values</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={forecastData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="metric" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Legend />
                <Line type="monotone" dataKey="forecast" stroke="#06b6d4" strokeWidth={2} name="Forecast" />
                <Line type="monotone" dataKey="lower" stroke="#f59e0b" strokeDasharray="5 5" name="Lower Bound" />
                <Line type="monotone" dataKey="upper" stroke="#10b981" strokeDasharray="5 5" name="Upper Bound" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Scenario Impact Distribution</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={scenarioImpactData} dataKey="count" nameKey="impact" cx="50%" cy="50%" outerRadius={70} label>
                  {scenarioImpactData.map((_, i) => (
                    <Cell key={i} fill={['#10b981', '#f59e0b', '#ef4444', '#6366f1'][i % 4]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Utilization Rates (%)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={utilizationData.map(d => ({ name: d.name, rate: d.utilization_rate }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Bar dataKey="rate" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Utilization %" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setActiveTab(t.key); setShowForm(false); setEditingId(null); }}
            className={`px-4 py-2 rounded font-medium ${activeTab === t.key ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-4">
        <button onClick={() => { setShowForm(true); setEditingId(null); }} className={btnPrimary}>+ New {activeTab === 'plans' ? 'Plan' : activeTab === 'allocations' ? 'Allocation' : activeTab === 'forecasts' ? 'Forecast' : 'Scenario'}</button>
        <button onClick={fetchAll} className="bg-gray-700 text-gray-300 px-4 py-2 rounded hover:bg-gray-600">Refresh</button>
        <button onClick={() => { const data = activeTab === 'plans' ? plans : activeTab === 'allocations' ? allocations : activeTab === 'forecasts' ? forecasts : scenarios; exportToCSV(data as unknown as Record<string, unknown>[], `${activeTab}_export.csv`); }} className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600">Export CSV</button>
      </div>

      {/* Search, Filter & Export */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input type="text" placeholder="Search..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500" />
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500">
          <option value="">All</option>
          {activeTab === 'plans' && <><option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option></>}
          {activeTab === 'scenarios' && <><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></>}
        </select>
        <button onClick={exportCSV} className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600">Export CSV</button>
      </div>

      {/* Forms */}
      {showForm && activeTab === 'plans' && (
        <form onSubmit={handleSubmitPlan} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Plan' : 'Create Plan'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Name</label><input className={inputCls} value={planForm.name} onChange={e => setPlanForm({ ...planForm, name: e.target.value })} required /></div>
            <div><label className={labelCls}>Status</label><select className={inputCls} value={planForm.status} onChange={e => setPlanForm({ ...planForm, status: e.target.value })}><option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option></select></div>
            <div><label className={labelCls}>Start Date</label><input type="date" className={inputCls} value={planForm.start_date} onChange={e => setPlanForm({ ...planForm, start_date: e.target.value })} /></div>
            <div><label className={labelCls}>End Date</label><input type="date" className={inputCls} value={planForm.end_date} onChange={e => setPlanForm({ ...planForm, end_date: e.target.value })} /></div>
            <div><label className={labelCls}>Total Budget</label><input type="number" step="0.01" className={inputCls} value={planForm.total_budget} onChange={e => setPlanForm({ ...planForm, total_budget: +e.target.value })} /></div>
            <div><label className={labelCls}>Currency</label><input className={inputCls} value={planForm.currency} onChange={e => setPlanForm({ ...planForm, currency: e.target.value })} /></div>
            <div className="md:col-span-2 lg:col-span-3"><label className={labelCls}>Notes</label><input className={inputCls} value={planForm.notes} onChange={e => setPlanForm({ ...planForm, notes: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'allocations' && (
        <form onSubmit={handleSubmitAlloc} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Allocation' : 'Create Allocation'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Plan</label><select className={inputCls} value={allocForm.plan_id} onChange={e => setAllocForm({ ...allocForm, plan_id: +e.target.value })}><option value={0}>Select...</option>{plans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
            <div><label className={labelCls}>Resource Type</label><input className={inputCls} value={allocForm.resource_type} onChange={e => setAllocForm({ ...allocForm, resource_type: e.target.value })} required /></div>
            <div><label className={labelCls}>Resource Name</label><input className={inputCls} value={allocForm.resource_name} onChange={e => setAllocForm({ ...allocForm, resource_name: e.target.value })} required /></div>
            <div><label className={labelCls}>Allocated Units</label><input type="number" step="0.01" className={inputCls} value={allocForm.allocated_units} onChange={e => setAllocForm({ ...allocForm, allocated_units: +e.target.value })} /></div>
            <div><label className={labelCls}>Utilized Units</label><input type="number" step="0.01" className={inputCls} value={allocForm.utilized_units} onChange={e => setAllocForm({ ...allocForm, utilized_units: +e.target.value })} /></div>
            <div><label className={labelCls}>Unit</label><input className={inputCls} placeholder="e.g. instances, GB, FTE" value={allocForm.unit} onChange={e => setAllocForm({ ...allocForm, unit: e.target.value })} /></div>
            <div><label className={labelCls}>Cost Per Unit</label><input type="number" step="0.01" className={inputCls} value={allocForm.cost_per_unit} onChange={e => setAllocForm({ ...allocForm, cost_per_unit: +e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'forecasts' && (
        <form onSubmit={handleSubmitForecast} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Forecast' : 'Create Forecast'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Plan</label><select className={inputCls} value={forecastForm.plan_id} onChange={e => setForecastForm({ ...forecastForm, plan_id: +e.target.value })}><option value={0}>Select...</option>{plans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
            <div><label className={labelCls}>Metric</label><input className={inputCls} value={forecastForm.metric} onChange={e => setForecastForm({ ...forecastForm, metric: e.target.value })} required /></div>
            <div><label className={labelCls}>Period</label><input className={inputCls} placeholder="e.g. 2026-Q4" value={forecastForm.period} onChange={e => setForecastForm({ ...forecastForm, period: e.target.value })} required /></div>
            <div><label className={labelCls}>Forecast Value</label><input type="number" step="0.01" className={inputCls} value={forecastForm.forecast_value} onChange={e => setForecastForm({ ...forecastForm, forecast_value: +e.target.value })} /></div>
            <div><label className={labelCls}>Confidence Lower</label><input type="number" step="0.01" className={inputCls} value={forecastForm.confidence_lower} onChange={e => setForecastForm({ ...forecastForm, confidence_lower: +e.target.value })} /></div>
            <div><label className={labelCls}>Confidence Upper</label><input type="number" step="0.01" className={inputCls} value={forecastForm.confidence_upper} onChange={e => setForecastForm({ ...forecastForm, confidence_upper: +e.target.value })} /></div>
            <div><label className={labelCls}>Model</label><input className={inputCls} placeholder="e.g. ARIMA, Prophet" value={forecastForm.model} onChange={e => setForecastForm({ ...forecastForm, model: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'scenarios' && (
        <form onSubmit={handleSubmitScenario} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Scenario' : 'Create Scenario'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Plan</label><select className={inputCls} value={scenarioForm.plan_id} onChange={e => setScenarioForm({ ...scenarioForm, plan_id: +e.target.value })}><option value={0}>Select...</option>{plans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
            <div><label className={labelCls}>Name</label><input className={inputCls} value={scenarioForm.name} onChange={e => setScenarioForm({ ...scenarioForm, name: e.target.value })} required /></div>
            <div><label className={labelCls}>Impact</label><select className={inputCls} value={scenarioForm.impact} onChange={e => setScenarioForm({ ...scenarioForm, impact: e.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>
            <div><label className={labelCls}>Probability (0-1)</label><input type="number" step="0.01" min="0" max="1" className={inputCls} value={scenarioForm.probability} onChange={e => setScenarioForm({ ...scenarioForm, probability: +e.target.value })} /></div>
            <div className="md:col-span-2"><label className={labelCls}>Description</label><input className={inputCls} value={scenarioForm.description} onChange={e => setScenarioForm({ ...scenarioForm, description: e.target.value })} /></div>
            <div className="md:col-span-2 lg:col-span-3"><label className={labelCls}>Assumptions</label><input className={inputCls} value={scenarioForm.assumptions} onChange={e => setScenarioForm({ ...scenarioForm, assumptions: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {/* Tables */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="px-4 py-8 text-center text-gray-400">Loading...</div>
        ) : activeTab === 'plans' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Budget</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Notes</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No capacity plans found</td></tr>
              ) : filteredData.map(p => (
                <tr key={p.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{p.name}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[p.status] || 'bg-gray-700 text-gray-300'}`}>{p.status}</span></td>
                  <td className="px-4 py-3 text-gray-300">{p.start_date || '—'} → {p.end_date || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(p.total_budget)}</td>
                  <td className="px-4 py-3 text-gray-300">{p.notes || '—'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(p.id)} className="text-cyan-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(p.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : activeTab === 'allocations' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Resource</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Type</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Allocated</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Utilized</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Util %</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Cost/Unit</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No allocations found</td></tr>
              ) : filteredData.map(a => (
                <tr key={a.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{a.resource_name}</td>
                  <td className="px-4 py-3 text-gray-300">{a.resource_type}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmtNum(a.allocated_units)} {a.unit || ''}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmtNum(a.utilized_units)} {a.unit || ''}</td>
                  <td className={`px-4 py-3 text-right ${a.allocated_units > 0 && (a.utilized_units / a.allocated_units) > 0.9 ? 'text-red-400' : 'text-green-400'}`}>{a.allocated_units > 0 ? Math.round((a.utilized_units / a.allocated_units) * 100) : 0}%</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(a.cost_per_unit)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(a.id)} className="text-cyan-400 hover:underline mr-3">Edit</button>
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
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Metric</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Forecast</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Lower</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Upper</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Model</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No forecasts found</td></tr>
              ) : filteredData.map(f => (
                <tr key={f.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{f.metric}</td>
                  <td className="px-4 py-3 text-gray-300">{f.period}</td>
                  <td className="px-4 py-3 text-right text-cyan-400">{f.forecast_value}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{f.confidence_lower ?? '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{f.confidence_upper ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{f.model || '—'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(f.id)} className="text-cyan-400 hover:underline mr-3">Edit</button>
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
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Description</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Probability</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Impact</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Assumptions</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No scenarios found</td></tr>
              ) : filteredData.map(s => (
                <tr key={s.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{s.name}</td>
                  <td className="px-4 py-3 text-gray-300">{s.description || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{(s.probability * 100).toFixed(0)}%</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[s.impact] || 'bg-gray-700 text-gray-300'}`}>{s.impact}</span></td>
                  <td className="px-4 py-3 text-gray-300">{s.assumptions || '—'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(s.id)} className="text-cyan-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(s.id)} className="text-red-400 hover:underline">Delete</button>
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
