import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from '../hooks/useKeyboardShortcuts';
import { api } from '../api/client';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import type {
  DRPlan,
  DRPlanInput,
  BackupSchedule,
  BackupScheduleInput,
  RecoveryProcedure,
  RecoveryProcedureInput,
  DRTest,
  DRTestInput,
} from '../api/client';

type TabKey = 'dr_plans' | 'backup_schedules' | 'recovery_procedures' | 'dr_tests';

const PAGE_SIZE = 10;

const tabConfig: { key: TabKey; label: string }[] = [
  { key: 'dr_plans', label: 'DR Plans' },
  { key: 'backup_schedules', label: 'Backup Schedules' },
  { key: 'recovery_procedures', label: 'Recovery Procedures' },
  { key: 'dr_tests', label: 'DR Tests' },
];

const emptyForms: Record<TabKey, Record<string, any>> = {
  dr_plans: { name: '', description: '', rto_hours: 4, rpo_hours: 1, status: 'draft', last_tested: null },
  backup_schedules: { name: '', schedule: '0 2 * * *', retention_days: 30, target: '', enabled: true, last_run: null },
  recovery_procedures: { dr_plan_id: 1, step: 1, title: '', description: '', owner: '', estimated_minutes: 30 },
  dr_tests: { dr_plan_id: 1, test_date: '', result: 'scheduled', rto_achieved_hours: null, notes: '' },
};

const DisasterRecoveryManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('dr_plans');
  const [drPlans, setDRPlans] = useState<DRPlan[]>([]);
  const [backupSchedules, setBackupSchedules] = useState<BackupSchedule[]>([]);
  const [recoveryProcedures, setRecoveryProcedures] = useState<RecoveryProcedure[]>([]);
  const [drTests, setDRTests] = useState<DRTest[]>([]);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState<Record<string, any>>(emptyForms.dr_plans);
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
      case 'dr_plans': return drPlans;
      case 'backup_schedules': return backupSchedules;
      case 'recovery_procedures': return recoveryProcedures;
      case 'dr_tests': return drTests;
    }
  }, [activeTab, drPlans, backupSchedules, recoveryProcedures, drTests]);

  const { sortedData: _sortedItems, requestSort, getSortIndicator } = useSort(currentData() as DRPlan[]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [plans, schedules, procedures, tests] = await Promise.all([
        api.getDRPlans(),
        api.getBackupSchedules(),
        api.getRecoveryProcedures(),
        api.getDRTests(),
      ]);
      setDRPlans(plans);
      setBackupSchedules(schedules);
      setRecoveryProcedures(procedures);
      setDRTests(tests);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch disaster recovery data');
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
      case 'dr_plans':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
              <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">RTO (hours)</label>
              <input type="number" step="0.5" value={formData.rto_hours} onChange={e => setFormData({ ...formData, rto_hours: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">RPO (hours)</label>
              <input type="number" step="0.5" value={formData.rpo_hours} onChange={e => setFormData({ ...formData, rpo_hours: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Last Tested</label>
              <input type="date" value={formData.last_tested || ''} onChange={e => setFormData({ ...formData, last_tested: e.target.value || null })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </>
        );
      case 'backup_schedules':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Cron Schedule</label>
              <input value={formData.schedule} onChange={e => setFormData({ ...formData, schedule: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" placeholder="0 2 * * *" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Retention (days)</label>
              <input type="number" value={formData.retention_days} onChange={e => setFormData({ ...formData, retention_days: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Target</label>
              <input value={formData.target} onChange={e => setFormData({ ...formData, target: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" placeholder="s3://backups/..." />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Enabled</label>
              <select value={String(formData.enabled)} onChange={e => setFormData({ ...formData, enabled: e.target.value === 'true' })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>
          </>
        );
      case 'recovery_procedures':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">DR Plan *</label>
              <select value={formData.dr_plan_id} onChange={e => setFormData({ ...formData, dr_plan_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                {drPlans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Step #</label>
              <input type="number" value={formData.step} onChange={e => setFormData({ ...formData, step: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
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
              <label className="block text-sm font-medium mb-1 text-gray-300">Owner</label>
              <input value={formData.owner} onChange={e => setFormData({ ...formData, owner: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Est. Minutes</label>
              <input type="number" value={formData.estimated_minutes} onChange={e => setFormData({ ...formData, estimated_minutes: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </>
        );
      case 'dr_tests':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">DR Plan *</label>
              <select value={formData.dr_plan_id} onChange={e => setFormData({ ...formData, dr_plan_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                {drPlans.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Test Date</label>
              <input type="date" value={formData.test_date} onChange={e => setFormData({ ...formData, test_date: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Result</label>
              <select value={formData.result} onChange={e => setFormData({ ...formData, result: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="scheduled">Scheduled</option>
                <option value="passed">Passed</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">RTO Achieved (hours)</label>
              <input type="number" step="0.1" value={formData.rto_achieved_hours || ''} onChange={e => setFormData({ ...formData, rto_achieved_hours: e.target.value ? Number(e.target.value) : null })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Notes</label>
              <textarea value={formData.notes} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" rows={2} />
            </div>
          </>
        );
    }
  };

  const renderTable = () => {
    const items = pagedItems as any[];
    if (loading) {
      return <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>;
    }
    if (items.length === 0) {
      return <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">No {activeTab.replace(/_/g, ' ')} found</td></tr>;
    }
    return items.map((item) => (
      <tr key={item.id} className="border-t border-gray-700 hover:bg-gray-750">
        <td className="px-4 py-3 text-gray-400">{item.id}</td>
        {activeTab === 'dr_plans' && (
          <>
            <td className="px-4 py-3 font-medium">{item.name}</td>
            <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{item.description}</td>
            <td className="px-4 py-3 text-gray-400">RTO: {item.rto_hours}h</td>
            <td className="px-4 py-3 text-gray-400">RPO: {item.rpo_hours}h</td>
            <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
          </>
        )}
        {activeTab === 'backup_schedules' && (
          <>
            <td className="px-4 py-3 font-medium">{item.name}</td>
            <td className="px-4 py-3 text-gray-400 font-mono text-xs">{item.schedule}</td>
            <td className="px-4 py-3 text-gray-400">{item.retention_days}d</td>
            <td className="px-4 py-3"><EnabledBadge enabled={item.enabled} /></td>
          </>
        )}
        {activeTab === 'recovery_procedures' && (
          <>
            <td className="px-4 py-3 font-medium">Step {item.step}: {item.title}</td>
            <td className="px-4 py-3 text-gray-400">{drPlans.find(p => p.id === item.dr_plan_id)?.name || '-'}</td>
            <td className="px-4 py-3 text-gray-400">{item.owner}</td>
            <td className="px-4 py-3 text-gray-400">{item.estimated_minutes}m</td>
          </>
        )}
        {activeTab === 'dr_tests' && (
          <>
            <td className="px-4 py-3 font-medium">{drPlans.find(p => p.id === item.dr_plan_id)?.name || '-'}</td>
            <td className="px-4 py-3 text-gray-400">{item.test_date}</td>
            <td className="px-4 py-3"><ResultBadge result={item.result} /></td>
            <td className="px-4 py-3 text-gray-400">{item.rto_achieved_hours ? `${item.rto_achieved_hours}h` : '-'}</td>
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
      <h1 className="text-2xl font-bold mb-6">Disaster Recovery Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      {/* Dashboard */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4 text-gray-200">Dashboard</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Active DR Plans', value: drPlans.filter(p => p.status === 'active').length, color: 'text-cyan-400' },
            { label: 'Backup Schedules', value: backupSchedules.filter(s => s.enabled).length, color: 'text-blue-400' },
            { label: 'Recovery Steps', value: recoveryProcedures.length, color: 'text-amber-400' },
            { label: 'Tests Passed', value: drTests.filter(t => t.result === 'passed').length, color: 'text-green-400' },
          ].map(kpi => (
            <div key={kpi.label} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-sm text-gray-400">{kpi.label}</p>
              <p className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">DR Plans by Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={['draft', 'active', 'archived'].map(status => ({
                name: status.charAt(0).toUpperCase() + status.slice(1),
                count: drPlans.filter(p => p.status === status).length,
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
            <h3 className="text-sm font-medium text-gray-300 mb-3">DR Test Results</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={['passed', 'failed', 'scheduled', 'cancelled'].map(result => ({
                    name: result.charAt(0).toUpperCase() + result.slice(1),
                    value: drTests.filter(t => t.result === result).length,
                  })).filter(d => d.value > 0)}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {['#22C55E', '#EF4444', '#3B82F6', '#6B7280'].map((color, i) => (
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
          placeholder={`Search ${activeTab.replace(/_/g, ' ')}...`}
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px] text-gray-100 placeholder-gray-500"
          ref={searchRef}
        />
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForms[activeTab]); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New {activeTab.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit' : 'Create New'} {activeTab.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</h2>
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
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              {activeTab === 'dr_plans' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Description</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">RTO</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">RPO</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                </>
              )}
              {activeTab === 'backup_schedules' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Schedule</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Retention</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Enabled</th>
                </>
              )}
              {activeTab === 'recovery_procedures' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('title')}>Step & Title{getSortIndicator('title')}</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">DR Plan</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Owner</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Est. Time</th>
                </>
              )}
              {activeTab === 'dr_tests' && (
                <>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">DR Plan</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Test Date</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Result</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">RTO Achieved</th>
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
    draft: 'bg-yellow-900/50 text-yellow-300',
    archived: 'bg-gray-700 text-gray-400',
  };
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${colorMap[status] || 'bg-gray-700 text-gray-400'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function EnabledBadge({ enabled }: { enabled: boolean }) {
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${enabled ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'}`}>
      {enabled ? 'Enabled' : 'Disabled'}
    </span>
  );
}

function ResultBadge({ result }: { result: string }) {
  const colorMap: Record<string, string> = {
    passed: 'bg-green-900/50 text-green-300',
    failed: 'bg-red-900/50 text-red-300',
    scheduled: 'bg-blue-900/50 text-blue-300',
    cancelled: 'bg-gray-700 text-gray-400',
  };
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${colorMap[result] || 'bg-gray-700 text-gray-400'}`}>
      {result}
    </span>
  );
}

// ── API helpers (inline to avoid circular deps) ──────────────────────────────

async function createItem(tab: TabKey, data: Record<string, any>) {
  switch (tab) {
    case 'dr_plans': return api.createDRPlan(data as DRPlanInput);
    case 'backup_schedules': return api.createBackupSchedule(data as BackupScheduleInput);
    case 'recovery_procedures': return api.createRecoveryProcedure(data as RecoveryProcedureInput);
    case 'dr_tests': return api.createDRTest(data as DRTestInput);
  }
}

async function updateItem(tab: TabKey, id: string, data: Record<string, any>) {
  switch (tab) {
    case 'dr_plans': return api.updateDRPlan(id, data as DRPlanInput);
    case 'backup_schedules': return api.updateBackupSchedule(id, data as BackupScheduleInput);
    case 'recovery_procedures': return api.updateRecoveryProcedure(id, data as RecoveryProcedureInput);
    case 'dr_tests': return api.updateDRTest(id, data as DRTestInput);
  }
}

async function deleteItem(tab: TabKey, id: string) {
  switch (tab) {
    case 'dr_plans': return api.deleteDRPlan(id);
    case 'backup_schedules': return api.deleteBackupSchedule(id);
    case 'recovery_procedures': return api.deleteRecoveryProcedure(id);
    case 'dr_tests': return api.deleteDRTest(id);
  }
}

export default DisasterRecoveryManagement;
