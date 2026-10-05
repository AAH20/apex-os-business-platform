import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from '../hooks/useKeyboardShortcuts';
import { api, isAbortError } from '../api/client';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import type {
  ComplianceFramework,
  ComplianceFrameworkInput,
  Control,
  ControlInput,
  Audit,
  AuditInput,
  Finding,
  FindingInput,
  RemediationPlan,
  RemediationPlanInput,
} from '../api/client';

type TabKey = 'frameworks' | 'controls' | 'audits' | 'findings' | 'remediation_plans';

const PAGE_SIZE = 10;

const tabConfig: { key: TabKey; label: string }[] = [
  { key: 'frameworks', label: 'Frameworks' },
  { key: 'controls', label: 'Controls' },
  { key: 'audits', label: 'Audits' },
  { key: 'findings', label: 'Findings' },
  { key: 'remediation_plans', label: 'Remediation Plans' },
];

const emptyForms: Record<TabKey, Record<string, any>> = {
  frameworks: { name: '', version: '', description: '', status: 'active' },
  controls: { framework_id: 1, name: '', description: '', status: 'planned', owner: '' },
  audits: { framework_id: 1, name: '', auditor: '', start_date: '', end_date: '', status: 'scheduled', result: null },
  findings: { audit_id: 1, title: '', description: '', severity: 'medium', status: 'open', assigned_to: '', due_date: '' },
  remediation_plans: { finding_id: 1, title: '', description: '', status: 'not_started', owner: '', target_date: '' },
};

const ComplianceManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('frameworks');
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([]);
  const [controls, setControls] = useState<Control[]>([]);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [remediationPlans, setRemediationPlans] = useState<RemediationPlan[]>([]);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState<Record<string, any>>(emptyForms.frameworks);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const currentData = useCallback(() => {
    switch (activeTab) {
      case 'frameworks': return frameworks;
      case 'controls': return controls;
      case 'audits': return audits;
      case 'findings': return findings;
      case 'remediation_plans': return remediationPlans;
    }
  }, [activeTab, frameworks, controls, audits, findings, remediationPlans]);

  const { sortedData: _sortedItems, requestSort, getSortIndicator } = useSort(currentData() as ComplianceFramework[]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fw, ct, au, fi, rp] = await Promise.all([
        api.getComplianceFrameworks(),
        api.getComplianceControls(),
        api.getComplianceAudits(),
        api.getComplianceFindings(),
        api.getComplianceRemediationPlans(),
      ]);
      setFrameworks(fw);
      setControls(ct);
      setAudits(au);
      setFindings(fi);
      setRemediationPlans(rp);
    } catch (e: any) {
      if (isAbortError(e)) return;
      setError(e.message || 'Failed to fetch compliance data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const getFiltered = useCallback(() => {
    const data = currentData();
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter((item: any) =>
      Object.values(item).some((v) => String(v).toLowerCase().includes(q))
    );
  }, [currentData, search]);

  const filtered = getFiltered();
  const total = filtered.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const pagedItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
    setPage(1);
    setSearch('');
    setFormData(emptyForms[tab]);
    setEditingId(null);
    setShowForm(false);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        await updateItem(activeTab, editingId, formData);
      } else {
        await createItem(activeTab, formData);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForms[activeTab]);
      fetchData();
    } catch (e: any) {
      if (isAbortError(e)) return;
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (item: any) => {
    setFormData({ ...item });
    setEditingId(String(item.id));
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    setDeleting(true);
    try {
      await deleteItem(activeTab, id);
      setShowDeleteConfirm(null);
      fetchData();
    } catch (e: any) {
      if (isAbortError(e)) return;
      setError(e.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  useKeyboardShortcuts({
    onNew: () => { setShowForm(true); setEditingId(null); setFormData(emptyForms[activeTab]); },
    onSearch: () => searchRef.current?.focus(),
    searchRef,
    onExport: () => exportToCSV(currentData() as unknown as Record<string, unknown>[], `${activeTab}_export.csv`),
    onDelete: () => { if (currentData().length > 0) setShowDeleteConfirm(String((currentData()[0] as any).id)); },
    onClose: () => setShowForm(false),
  });

  const renderForm = () => {
    switch (activeTab) {
      case 'frameworks':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Version</label>
              <input value={formData.version} onChange={e => setFormData({ ...formData, version: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
              <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
              </select>
            </div>
          </>
        );
      case 'controls':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Framework *</label>
              <select value={formData.framework_id} onChange={e => setFormData({ ...formData, framework_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                {frameworks.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
              <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="planned">Planned</option>
                <option value="in_progress">In Progress</option>
                <option value="implemented">Implemented</option>
                <option value="deprecated">Deprecated</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Owner</label>
              <input value={formData.owner} onChange={e => setFormData({ ...formData, owner: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </>
        );
      case 'audits':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Framework *</label>
              <select value={formData.framework_id} onChange={e => setFormData({ ...formData, framework_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                {frameworks.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Auditor</label>
              <input value={formData.auditor} onChange={e => setFormData({ ...formData, auditor: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Start Date</label>
              <input type="date" value={formData.start_date} onChange={e => setFormData({ ...formData, start_date: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">End Date</label>
              <input type="date" value={formData.end_date} onChange={e => setFormData({ ...formData, end_date: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="scheduled">Scheduled</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Result</label>
              <select value={formData.result || ''} onChange={e => setFormData({ ...formData, result: e.target.value || null })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="">None</option>
                <option value="passed">Passed</option>
                <option value="failed">Failed</option>
                <option value="conditional">Conditional</option>
              </select>
            </div>
          </>
        );
      case 'findings':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Audit *</label>
              <select value={formData.audit_id} onChange={e => setFormData({ ...formData, audit_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                {audits.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Title *</label>
              <input required value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
              <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Severity</label>
              <select value={formData.severity} onChange={e => setFormData({ ...formData, severity: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Assigned To</label>
              <input value={formData.assigned_to} onChange={e => setFormData({ ...formData, assigned_to: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Due Date</label>
              <input type="date" value={formData.due_date} onChange={e => setFormData({ ...formData, due_date: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </>
        );
      case 'remediation_plans':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Finding *</label>
              <select value={formData.finding_id} onChange={e => setFormData({ ...formData, finding_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                {findings.map(f => <option key={f.id} value={f.id}>{f.title}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Title *</label>
              <input required value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
              <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Owner</label>
              <input value={formData.owner} onChange={e => setFormData({ ...formData, owner: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Target Date</label>
              <input type="date" value={formData.target_date} onChange={e => setFormData({ ...formData, target_date: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </>
        );
    }
  };

  const renderTable = () => {
    const items = pagedItems as any[];
    if (loading) {
      return <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>;
    }
    if (items.length === 0) {
      return <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No {activeTab.replace('_', ' ')} found</td></tr>;
    }
    return items.map((item) => (
      <tr key={item.id} className="border-t border-gray-700 hover:bg-gray-600">
        <td className="px-4 py-3 text-gray-400">{item.id}</td>
        {activeTab === 'frameworks' && (
          <>
            <td className="px-4 py-3 font-medium">{item.name}</td>
            <td className="px-4 py-3 text-gray-400">{item.version}</td>
            <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{item.description}</td>
            <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
          </>
        )}
        {activeTab === 'controls' && (
          <>
            <td className="px-4 py-3 font-medium">{item.name}</td>
            <td className="px-4 py-3 text-gray-400">{frameworks.find(f => f.id === item.framework_id)?.name || '-'}</td>
            <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
            <td className="px-4 py-3 text-gray-400">{item.owner}</td>
          </>
        )}
        {activeTab === 'audits' && (
          <>
            <td className="px-4 py-3 font-medium">{item.name}</td>
            <td className="px-4 py-3 text-gray-400">{item.auditor}</td>
            <td className="px-4 py-3 text-gray-400">{item.start_date} → {item.end_date}</td>
            <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
            <td className="px-4 py-3">{item.result ? <ResultBadge result={item.result} /> : '-'}</td>
          </>
        )}
        {activeTab === 'findings' && (
          <>
            <td className="px-4 py-3 font-medium">{item.title}</td>
            <td className="px-4 py-3"><SeverityBadge severity={item.severity} /></td>
            <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
            <td className="px-4 py-3 text-gray-400">{item.assigned_to}</td>
            <td className="px-4 py-3 text-gray-400">{item.due_date}</td>
          </>
        )}
        {activeTab === 'remediation_plans' && (
          <>
            <td className="px-4 py-3 font-medium">{item.title}</td>
            <td className="px-4 py-3 text-gray-400">{findings.find(f => f.id === item.finding_id)?.title || '-'}</td>
            <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
            <td className="px-4 py-3 text-gray-400">{item.owner}</td>
            <td className="px-4 py-3 text-gray-400">{item.target_date}</td>
          </>
        )}
        <td className="px-4 py-3">
          <button onClick={() => handleEdit(item)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
          <button onClick={() => setShowDeleteConfirm(String(item.id))} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
        </td>
      </tr>
    ));
  };



  return (
    <div className="p-6 max-w-7xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Compliance Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      {/* Dashboard */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4 text-gray-200">Dashboard</h2>
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Active Frameworks', value: frameworks.filter(f => f.status === 'active').length, color: 'text-cyan-400' },
            { label: 'Total Controls', value: controls.length, color: 'text-blue-400' },
            { label: 'Open Audits', value: audits.filter(a => a.status === 'in_progress').length, color: 'text-amber-400' },
            { label: 'Open Findings', value: findings.filter(f => f.status === 'open').length, color: 'text-red-400' },
          ].map(kpi => (
            <div key={kpi.label} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-sm text-gray-400">{kpi.label}</p>
              <p className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</p>
            </div>
          ))}
        </div>
        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Controls by Framework</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={frameworks.map(fw => ({
                name: fw.name,
                count: controls.filter(c => c.framework_id === fw.id).length,
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9CA3AF', fontSize: 12 }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }} labelStyle={{ color: '#E5E7EB' }} />
                <Bar dataKey="count" fill="#06B6D4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Findings by Severity</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={['critical', 'high', 'medium', 'low'].map(sev => ({
                    name: sev.charAt(0).toUpperCase() + sev.slice(1),
                    value: findings.filter(f => f.severity === sev).length,
                  })).filter(d => d.value > 0)}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {['#EF4444', '#F97316', '#EAB308', '#22C55E'].map((color, i) => (
                    <Cell key={i} fill={color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }} />
                <Legend wrapperStyle={{ color: '#9CA3AF', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-4">
        {tabConfig.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-cyan-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search + New */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder={`Search ${activeTab.replace('_', ' ')}...`}
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px] text-gray-100 placeholder-gray-500"
          ref={searchRef}
        />
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForms[activeTab]); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New {activeTab.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
        </button>
        <button
          onClick={() => exportToCSV(currentData() as unknown as Record<string, unknown>[], `${activeTab}_export.csv`)}
          className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Export CSV
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit' : 'Create New'} {activeTab.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderForm()}
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
              {saving ? 'Saving...' : editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); setFormData(emptyForms[activeTab]); }} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this item? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} disabled={deleting} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} disabled={deleting} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50">
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden shadow">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              {activeTab === 'frameworks' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Version</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Description</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                </>
              )}
              {activeTab === 'controls' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Framework</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Owner</th>
                </>
              )}
              {activeTab === 'audits' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Auditor</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Dates</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Result</th>
                </>
              )}
              {activeTab === 'findings' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('title')}>Title{getSortIndicator('title')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Severity</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Assigned To</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Due Date</th>
                </>
              )}
              {activeTab === 'remediation_plans' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('title')}>Title{getSortIndicator('title')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Finding</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Owner</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Target Date</th>
                </>
              )}
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>{renderTable()}</tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-gray-400">Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}</p>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border border-gray-600 rounded disabled:opacity-50 hover:bg-gray-700 text-gray-300">Previous</button>
            <span className="px-3 py-1 text-gray-400">{page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 border border-gray-600 rounded disabled:opacity-50 hover:bg-gray-700 text-gray-300">Next</button>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Badge Components ─────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    active: 'bg-green-900/50 text-green-300',
    inactive: 'bg-gray-700 text-gray-400',
    draft: 'bg-yellow-900/50 text-yellow-300',
    planned: 'bg-blue-900/50 text-blue-300',
    in_progress: 'bg-amber-900/50 text-amber-300',
    implemented: 'bg-green-900/50 text-green-300',
    deprecated: 'bg-red-900/50 text-red-300',
    scheduled: 'bg-blue-900/50 text-blue-300',
    completed: 'bg-green-900/50 text-green-300',
    cancelled: 'bg-red-900/50 text-red-300',
    open: 'bg-red-900/50 text-red-300',
    resolved: 'bg-green-900/50 text-green-300',
    closed: 'bg-gray-700 text-gray-400',
    not_started: 'bg-gray-700 text-gray-400',
  };
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${colorMap[status] || 'bg-gray-700 text-gray-400'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colorMap: Record<string, string> = {
    low: 'bg-green-900/50 text-green-300',
    medium: 'bg-yellow-900/50 text-yellow-300',
    high: 'bg-orange-900/50 text-orange-300',
    critical: 'bg-red-900/50 text-red-300',
  };
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${colorMap[severity] || 'bg-gray-700 text-gray-400'}`}>
      {severity}
    </span>
  );
}

function ResultBadge({ result }: { result: string }) {
  const colorMap: Record<string, string> = {
    passed: 'bg-green-900/50 text-green-300',
    failed: 'bg-red-900/50 text-red-300',
    conditional: 'bg-yellow-900/50 text-yellow-300',
  };
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${colorMap[result] || 'bg-gray-700 text-gray-400'}`}>
      {result}
    </span>
  );
}

// ── API helpers (inline to avoid circular deps) ──────────────────────────────

async function createItem(tab: TabKey, data: Record<string, any>) {
  const payload = { ...data };
  if (tab === 'audits' && payload.result === '') payload.result = null;
  switch (tab) {
    case 'frameworks': return api.createComplianceFramework(payload as ComplianceFrameworkInput);
    case 'controls': return api.createComplianceControl(payload as ControlInput);
    case 'audits': return api.createComplianceAudit(payload as AuditInput);
    case 'findings': return api.createComplianceFinding(payload as FindingInput);
    case 'remediation_plans': return api.createComplianceRemediationPlan(payload as RemediationPlanInput);
  }
}

async function updateItem(tab: TabKey, id: string, data: Record<string, any>) {
  const payload = { ...data };
  if (tab === 'audits' && payload.result === '') payload.result = null;
  switch (tab) {
    case 'frameworks': return api.updateComplianceFramework(id, payload as ComplianceFrameworkInput);
    case 'controls': return api.updateComplianceControl(id, payload as ControlInput);
    case 'audits': return api.updateComplianceAudit(id, payload as AuditInput);
    case 'findings': return api.updateComplianceFinding(id, payload as FindingInput);
    case 'remediation_plans': return api.updateComplianceRemediationPlan(id, payload as RemediationPlanInput);
  }
}

async function deleteItem(tab: TabKey, id: string) {
  switch (tab) {
    case 'frameworks': return api.deleteComplianceFramework(id);
    case 'controls': return api.deleteComplianceControl(id);
    case 'audits': return api.deleteComplianceAudit(id);
    case 'findings': return api.deleteComplianceFinding(id);
    case 'remediation_plans': return api.deleteComplianceRemediationPlan(id);
  }
}

export default ComplianceManagement;
