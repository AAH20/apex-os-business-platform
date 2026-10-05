import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { fetchWithTimeout } from '../api/fallback';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Budget {
  id: number;
  name: string;
  fiscal_year: number;
  status: string;
  total_budgeted: number;
  total_actual: number;
  currency: string;
  start_date?: string;
  end_date?: string;
  created_at: string;
}

interface BudgetLine {
  id: number;
  budget_id: number;
  cost_center_id: number;
  category: string;
  description?: string;
  budgeted_amount: number;
  actual_amount: number;
  period?: string;
  created_at: string;
}

interface CostCenter {
  id: number;
  name: string;
  code: string;
  manager?: string;
  department?: string;
  created_at: string;
}

interface VarianceAnalysis {
  id: number;
  budget_id: number;
  budget_line_id: number;
  period: string;
  budgeted_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_percent: number;
  status: string;
  notes?: string;
  created_at: string;
}

type TabKey = 'budgets' | 'lines' | 'cost-centers' | 'variance';

const API_BASE = '/api/budgeting';

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetchWithTimeout(url, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

const emptyBudgetForm = { name: '', fiscal_year: 2026, status: 'draft', total_budgeted: 0, total_actual: 0, currency: 'USD', start_date: '', end_date: '' };
const emptyLineForm = { budget_id: 0, cost_center_id: 0, category: '', description: '', budgeted_amount: 0, actual_amount: 0, period: '' };
const emptyCCForm = { name: '', code: '', manager: '', department: '' };
const emptyVarianceForm = { budget_id: 0, budget_line_id: 0, period: '', budgeted_amount: 0, actual_amount: 0, variance_amount: 0, variance_percent: 0, status: 'on_budget', notes: '' };

const statusColors: Record<string, string> = {
  active: 'bg-green-900 text-green-300',
  draft: 'bg-yellow-900 text-yellow-300',
  closed: 'bg-gray-700 text-gray-300',
  under_budget: 'bg-blue-900 text-blue-300',
  on_budget: 'bg-green-900 text-green-300',
  over_budget: 'bg-red-900 text-red-300',
};

const fmt = (n: number) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function BudgetingManagement() {
  const [activeTab, setActiveTab] = useState<TabKey>('budgets');
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [lines, setLines] = useState<BudgetLine[]>([]);
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [variances, setVariances] = useState<VarianceAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const [budgetForm, setBudgetForm] = useState(emptyBudgetForm);
  const [lineForm, setLineForm] = useState(emptyLineForm);
  const [ccForm, setCCForm] = useState(emptyCCForm);
  const [varianceForm, setVarianceForm] = useState(emptyVarianceForm);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [b, l, cc, v] = await Promise.all([
        apiFetch<Budget[]>(`${API_BASE}/budgets/`),
        apiFetch<BudgetLine[]>(`${API_BASE}/budget-lines/`),
        apiFetch<CostCenter[]>(`${API_BASE}/cost-centers/`),
        apiFetch<VarianceAnalysis[]>(`${API_BASE}/variance-analysis/`),
      ]);
      setBudgets(b); setLines(l); setCostCenters(cc); setVariances(v);
    } catch (e: any) { setError(e.message || 'Failed to fetch'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDelete = async (id: number) => {
    setError('');
    try {
      const url = activeTab === 'budgets' ? `${API_BASE}/budgets/${id}`
        : activeTab === 'lines' ? `${API_BASE}/budget-lines/${id}`
        : activeTab === 'cost-centers' ? `${API_BASE}/cost-centers/${id}`
        : `${API_BASE}/variance-analysis/${id}`;
      await apiFetch(url, { method: 'DELETE' });
      setShowDeleteConfirm(null); fetchAll();
    } catch (e: any) { setError(e.message || 'Delete failed'); }
  };

  const handleSubmitBudget = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/budgets/${editingId}` : `${API_BASE}/budgets/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(budgetForm) });
      setBudgetForm(emptyBudgetForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitLine = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/budget-lines/${editingId}` : `${API_BASE}/budget-lines/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(lineForm) });
      setLineForm(emptyLineForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitCC = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/cost-centers/${editingId}` : `${API_BASE}/cost-centers/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(ccForm) });
      setCCForm(emptyCCForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const handleSubmitVariance = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    try {
      const url = editingId ? `${API_BASE}/variance-analysis/${editingId}` : `${API_BASE}/variance-analysis/`;
      await apiFetch(url, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(varianceForm) });
      setVarianceForm(emptyVarianceForm); setEditingId(null); setShowForm(false); fetchAll();
    } catch (e: any) { setError(e.message || 'Save failed'); }
  };

  const startEdit = (id: number) => {
    setEditingId(id);
    if (activeTab === 'budgets') {
      const b = budgets.find(x => x.id === id);
      if (b) setBudgetForm({ name: b.name, fiscal_year: b.fiscal_year, status: b.status, total_budgeted: b.total_budgeted, total_actual: b.total_actual, currency: b.currency, start_date: b.start_date || '', end_date: b.end_date || '' });
    } else if (activeTab === 'lines') {
      const l = lines.find(x => x.id === id);
      if (l) setLineForm({ budget_id: l.budget_id, cost_center_id: l.cost_center_id, category: l.category, description: l.description || '', budgeted_amount: l.budgeted_amount, actual_amount: l.actual_amount, period: l.period || '' });
    } else if (activeTab === 'cost-centers') {
      const c = costCenters.find(x => x.id === id);
      if (c) setCCForm({ name: c.name, code: c.code, manager: c.manager || '', department: c.department || '' });
    } else {
      const v = variances.find(x => x.id === id);
      if (v) setVarianceForm({ budget_id: v.budget_id, budget_line_id: v.budget_line_id, period: v.period, budgeted_amount: v.budgeted_amount, actual_amount: v.actual_amount, variance_amount: v.variance_amount, variance_percent: v.variance_percent, status: v.status, notes: v.notes || '' });
    }
    setShowForm(true);
  };

  const cancelForm = () => { setShowForm(false); setEditingId(null); setError(''); };

  const getCurrentData = (): any[] => {
    if (activeTab === 'budgets') return budgets;
    if (activeTab === 'lines') return lines;
    if (activeTab === 'cost-centers') return costCenters;
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
    { key: 'budgets', label: 'Budgets' },
    { key: 'lines', label: 'Budget Lines' },
    { key: 'cost-centers', label: 'Cost Centers' },
    { key: 'variance', label: 'Variance Analysis' },
  ];

  const inputCls = 'w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500';
  const labelCls = 'block text-sm font-medium text-gray-300 mb-1';
  const btnPrimary = 'bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700';
  const btnDanger = 'bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700';
  const btnCancel = 'bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-500';

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Budgeting Management</h1>
      {error && <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">{error}</div>}

      {/* Dashboard */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-100 mb-3">Dashboard</h2>
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Total Budgets</div>
            <div className="text-2xl font-bold text-gray-100">{budgets.length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Active Cost Centers</div>
            <div className="text-2xl font-bold text-gray-100">{costCenters.length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Budget Lines</div>
            <div className="text-2xl font-bold text-gray-100">{lines.length}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Variance Alerts</div>
            <div className="text-2xl font-bold text-red-400">{variances.filter(v => v.status === 'over_budget').length}</div>
          </div>
        </div>
        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Budgets by Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={Object.entries(budgets.reduce((acc, b) => { acc[b.status] = (acc[b.status] || 0) + 1; return acc; }, {} as Record<string, number>)).map(([status, count]) => ({ status, count }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="status" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Variance by Type</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={Object.entries(variances.reduce((acc, v) => { acc[v.status] = (acc[v.status] || 0) + 1; return acc; }, {} as Record<string, number>)).map(([status, count]) => ({ status, count }))} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={80} label>
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
        <button onClick={() => { setShowForm(true); setEditingId(null); }} className={btnPrimary}>+ New {activeTab === 'cost-centers' ? 'Cost Center' : activeTab === 'lines' ? 'Budget Line' : activeTab === 'variance' ? 'Variance Analysis' : 'Budget'}</button>
        <button onClick={fetchAll} className="bg-gray-700 text-gray-300 px-4 py-2 rounded hover:bg-gray-600">Refresh</button>
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
          {activeTab === 'budgets' && <><option value="draft">Draft</option><option value="active">Active</option><option value="closed">Closed</option></>}
          {activeTab === 'variance' && <><option value="under_budget">Under Budget</option><option value="on_budget">On Budget</option><option value="over_budget">Over Budget</option></>}
        </select>
        <button onClick={exportCSV} className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600">Export CSV</button>
        <button onClick={exportJSON} className="bg-indigo-700 text-white px-4 py-2 rounded hover:bg-indigo-600">Export JSON</button>
      </div>

      {/* Forms */}
      {showForm && activeTab === 'budgets' && (
        <form onSubmit={handleSubmitBudget} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Budget' : 'Create Budget'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Name</label><input className={inputCls} value={budgetForm.name} onChange={e => setBudgetForm({ ...budgetForm, name: e.target.value })} required /></div>
            <div><label className={labelCls}>Fiscal Year</label><input type="number" className={inputCls} value={budgetForm.fiscal_year} onChange={e => setBudgetForm({ ...budgetForm, fiscal_year: +e.target.value })} /></div>
            <div><label className={labelCls}>Status</label><select className={inputCls} value={budgetForm.status} onChange={e => setBudgetForm({ ...budgetForm, status: e.target.value })}><option value="draft">Draft</option><option value="active">Active</option><option value="closed">Closed</option></select></div>
            <div><label className={labelCls}>Total Budgeted</label><input type="number" step="0.01" className={inputCls} value={budgetForm.total_budgeted} onChange={e => setBudgetForm({ ...budgetForm, total_budgeted: +e.target.value })} /></div>
            <div><label className={labelCls}>Total Actual</label><input type="number" step="0.01" className={inputCls} value={budgetForm.total_actual} onChange={e => setBudgetForm({ ...budgetForm, total_actual: +e.target.value })} /></div>
            <div><label className={labelCls}>Currency</label><input className={inputCls} value={budgetForm.currency} onChange={e => setBudgetForm({ ...budgetForm, currency: e.target.value })} /></div>
            <div><label className={labelCls}>Start Date</label><input type="date" className={inputCls} value={budgetForm.start_date} onChange={e => setBudgetForm({ ...budgetForm, start_date: e.target.value })} /></div>
            <div><label className={labelCls}>End Date</label><input type="date" className={inputCls} value={budgetForm.end_date} onChange={e => setBudgetForm({ ...budgetForm, end_date: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

      {showForm && activeTab === 'lines' && (
        <form onSubmit={handleSubmitLine} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Budget Line' : 'Create Budget Line'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Budget</label><select className={inputCls} value={lineForm.budget_id} onChange={e => setLineForm({ ...lineForm, budget_id: +e.target.value })}><option value={0}>Select...</option>{budgets.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
            <div><label className={labelCls}>Cost Center</label><select className={inputCls} value={lineForm.cost_center_id} onChange={e => setLineForm({ ...lineForm, cost_center_id: +e.target.value })}><option value={0}>Select...</option>{costCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div><label className={labelCls}>Category</label><input className={inputCls} value={lineForm.category} onChange={e => setLineForm({ ...lineForm, category: e.target.value })} required /></div>
            <div><label className={labelCls}>Description</label><input className={inputCls} value={lineForm.description} onChange={e => setLineForm({ ...lineForm, description: e.target.value })} /></div>
            <div><label className={labelCls}>Budgeted Amount</label><input type="number" step="0.01" className={inputCls} value={lineForm.budgeted_amount} onChange={e => setLineForm({ ...lineForm, budgeted_amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Actual Amount</label><input type="number" step="0.01" className={inputCls} value={lineForm.actual_amount} onChange={e => setLineForm({ ...lineForm, actual_amount: +e.target.value })} /></div>
            <div><label className={labelCls}>Period</label><input className={inputCls} placeholder="e.g. 2026-Q1" value={lineForm.period} onChange={e => setLineForm({ ...lineForm, period: e.target.value })} /></div>
          </div>
          <div className="flex gap-3 mt-4"><button type="submit" className={btnPrimary}>{editingId ? 'Update' : 'Create'}</button><button type="button" onClick={cancelForm} className={btnCancel}>Cancel</button></div>
        </form>
      )}

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

      {showForm && activeTab === 'variance' && (
        <form onSubmit={handleSubmitVariance} className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-3">{editingId ? 'Edit Variance Analysis' : 'Create Variance Analysis'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Budget</label><select className={inputCls} value={varianceForm.budget_id} onChange={e => setVarianceForm({ ...varianceForm, budget_id: +e.target.value })}><option value={0}>Select...</option>{budgets.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
            <div><label className={labelCls}>Budget Line</label><select className={inputCls} value={varianceForm.budget_line_id} onChange={e => setVarianceForm({ ...varianceForm, budget_line_id: +e.target.value })}><option value={0}>Select...</option>{lines.map(l => <option key={l.id} value={l.id}>{l.category}</option>)}</select></div>
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
        ) : activeTab === 'budgets' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">FY</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Budgeted</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actual</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Variance</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No budgets found</td></tr>
              ) : filteredData.map(b => (
                <tr key={b.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{b.name}</td>
                  <td className="px-4 py-3 text-gray-300">{b.fiscal_year}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[b.status] || 'bg-gray-700 text-gray-300'}`}>{b.status}</span></td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(b.total_budgeted)}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(b.total_actual)}</td>
                  <td className={`px-4 py-3 text-right ${b.total_actual > b.total_budgeted ? 'text-red-400' : 'text-green-400'}`}>{fmt(b.total_actual - b.total_budgeted)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(b.id)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(b.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : activeTab === 'lines' ? (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Category</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Description</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Budgeted</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actual</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Variance</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No budget lines found</td></tr>
              ) : filteredData.map(l => (
                <tr key={l.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{l.category}</td>
                  <td className="px-4 py-3 text-gray-300">{l.description || '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{l.period || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(l.budgeted_amount)}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(l.actual_amount)}</td>
                  <td className={`px-4 py-3 text-right ${l.actual_amount > l.budgeted_amount ? 'text-red-400' : 'text-green-400'}`}>{fmt(l.actual_amount - l.budgeted_amount)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => startEdit(l.id)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(l.id)} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
        ) : (
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Budgeted</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actual</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Variance</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Var %</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No variance analysis found</td></tr>
              ) : filteredData.map(v => (
                <tr key={v.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-gray-100 font-medium">{v.period}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(v.budgeted_amount)}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{fmt(v.actual_amount)}</td>
                  <td className={`px-4 py-3 text-right ${v.variance_amount < 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(v.variance_amount)}</td>
                  <td className={`px-4 py-3 text-right ${v.variance_percent < 0 ? 'text-green-400' : 'text-red-400'}`}>{v.variance_percent.toFixed(1)}%</td>
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
