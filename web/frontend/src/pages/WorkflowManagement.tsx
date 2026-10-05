import React, { useState, useEffect, useCallback } from 'react';
import { Play, Plus, Edit2, Trash2, History, Zap, Clock, CheckCircle, XCircle, AlertCircle, Download } from 'lucide-react';
import { exportToCSV } from '../hooks/useKeyboardShortcuts';
import { fetchWithTimeout } from '../api/fallback';

interface WorkflowStep {
  id: number;
  workflow_id: number;
  name: string;
  order: number;
  action: string;
  config: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

interface Workflow {
  id: number;
  name: string;
  description: string | null;
  status: 'draft' | 'active' | 'paused' | 'archived';
  steps: WorkflowStep[];
  created_at: string;
  updated_at: string;
}

interface WorkflowRun {
  id: number;
  workflow_id: number;
  trigger_id: number | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

interface WorkflowFormData {
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'archived';
}

const EMPTY_FORM: WorkflowFormData = { name: '', description: '', status: 'draft' };
const API_KEY = 'test-api-key-12345';
const BASE = '/api/workflows';

function apiHeaders() {
  return { 'Content-Type': 'application/json', 'X-API-Key': API_KEY };
}

const statusColors: Record<string, string> = {
  draft: 'bg-gray-700 text-gray-300',
  active: 'bg-emerald-900/50 text-emerald-300',
  paused: 'bg-amber-900/50 text-amber-300',
  archived: 'bg-red-900/50 text-red-300',
};

const runStatusIcons: Record<string, React.ReactNode> = {
  pending: <Clock size={14} className="text-gray-400" />,
  running: <AlertCircle size={14} className="text-blue-400" />,
  completed: <CheckCircle size={14} className="text-emerald-400" />,
  failed: <XCircle size={14} className="text-red-400" />,
  cancelled: <XCircle size={14} className="text-gray-400" />,
};

export default function WorkflowManagement() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingWf, setEditingWf] = useState<Workflow | null>(null);
  const [formData, setFormData] = useState<WorkflowFormData>(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState<number | null>(null);
  const [viewRuns, setViewRuns] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchWorkflows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(BASE, { headers: apiHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setWorkflows(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch workflows');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRuns = useCallback(async (workflowId: number) => {
    try {
      const res = await fetchWithTimeout(`${BASE}/${workflowId}/runs`, { headers: apiHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRuns(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch runs');
    }
  }, []);

  useEffect(() => { fetchWorkflows(); }, [fetchWorkflows]);

  useEffect(() => {
    if (viewRuns !== null) fetchRuns(viewRuns);
  }, [viewRuns, fetchRuns]);

  const filtered = workflows.filter(w => {
    const q = search.toLowerCase();
    const matchSearch = !q || w.name.toLowerCase().includes(q) || (w.description || '').toLowerCase().includes(q);
    const matchStatus = statusFilter === 'all' || w.status === statusFilter;
    return matchSearch && matchStatus;
  });

  function openCreate() {
    setEditingWf(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(wf: Workflow) {
    setEditingWf(wf);
    setFormData({ name: wf.name, description: wf.description || '', status: wf.status });
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const url = editingWf ? `${BASE}/${editingWf.id}` : BASE;
      const method = editingWf ? 'PUT' : 'POST';
      const res = await fetchWithTimeout(url, {
        method,
        headers: apiHeaders(),
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      await fetchWorkflows();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    try {
      const res = await fetchWithTimeout(`${BASE}/${id}`, { method: 'DELETE', headers: apiHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      await fetchWorkflows();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  }

  async function handleRun(workflowId: number) {
    setRunning(workflowId);
    setError(null);
    try {
      const res = await fetchWithTimeout(`${BASE}/${workflowId}/runs`, {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ workflow_id: workflowId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchRuns(workflowId);
      setViewRuns(workflowId);
    } catch (e: any) {
      setError(e.message || 'Run failed');
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Zap className="text-cyan-400" size={24} />
              Workflow Automation
            </h1>
            <p className="text-sm text-gray-400 mt-1">Create, manage, and run automated workflows</p>
          </div>
          <button onClick={openCreate} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
            <Plus size={16} /> New Workflow
          </button>
          <button onClick={() => exportToCSV(workflows as unknown as Record<string, unknown>[], "workflows_export.csv")} className="px-4 py-2 bg-green-700 hover:bg-green-600 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
            <Download size={16} /> Export CSV
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">{error}</div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-4">
          <input
            type="text"
            placeholder="Search workflows..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-cyan-500"
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {/* Create/Edit Form */}
        {showForm && (
          <div className="mb-6 p-4 bg-gray-800 border border-gray-700 rounded-xl">
            <h2 className="text-lg font-semibold mb-3">{editingWf ? 'Edit Workflow' : 'Create Workflow'}</h2>
            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                required
                placeholder="Workflow name"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-cyan-500"
              />
              <select
                value={formData.status}
                onChange={e => setFormData({ ...formData, status: e.target.value as any })}
                className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-cyan-500"
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="archived">Archived</option>
              </select>
              <textarea
                placeholder="Description"
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
                className="md:col-span-2 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-cyan-500 resize-none"
                rows={2}
              />
              <div className="md:col-span-2 flex gap-2">
                <button type="submit" disabled={saving} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors">
                  {saving ? 'Saving...' : editingWf ? 'Update' : 'Create'}
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Workflow List */}
        <div className="overflow-x-auto bg-gray-800 border border-gray-700 rounded-xl">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-gray-400">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Steps</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-16 text-center">
                  <div className="text-5xl mb-4">⚡</div>
                  <h3 className="text-lg font-semibold text-gray-100 mb-2">No workflows yet</h3>
                  <p className="text-gray-400 mb-4">Create your first workflow to get started.</p>
                  <button onClick={openCreate} className="bg-cyan-600 hover:bg-cyan-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                    + New Workflow
                  </button>
                </td></tr>
              ) : (
                filtered.map(wf => (
                  <tr key={wf.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="px-4 py-3 text-gray-400">{wf.id}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium">{wf.name}</div>
                      {wf.description && <div className="text-xs text-gray-400 mt-0.5">{wf.description}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[wf.status]}`}>
                        {wf.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">{wf.steps?.length || 0}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => handleRun(wf.id)}
                          disabled={running === wf.id}
                          className="p-1.5 bg-emerald-900/50 hover:bg-emerald-800 text-emerald-300 rounded transition-colors disabled:opacity-50"
                          title="Run workflow"
                        >
                          <Play size={14} />
                        </button>
                        <button
                          onClick={() => { setViewRuns(viewRuns === wf.id ? null : wf.id); }}
                          className="p-1.5 bg-blue-900/50 hover:bg-blue-800 text-blue-300 rounded transition-colors"
                          title="View run history"
                        >
                          <History size={14} />
                        </button>
                        <button
                          onClick={() => openEdit(wf)}
                          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(wf.id)}
                          className="p-1.5 bg-red-900/50 hover:bg-red-800 text-red-300 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Run History Panel */}
        {viewRuns !== null && (
          <div className="mt-6 p-4 bg-gray-800 border border-gray-700 rounded-xl">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <History size={18} className="text-blue-400" />
              Run History — Workflow #{viewRuns}
            </h3>
            {runs.length === 0 ? (
              <p className="text-gray-400 text-sm py-4 text-center">No runs yet. Click the play button to run this workflow.</p>
            ) : (
              <div className="space-y-2">
                {runs.map(run => (
                  <div key={run.id} className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
                    <div className="flex items-center gap-3">
                      {runStatusIcons[run.status]}
                      <div>
                        <div className="text-sm font-medium">Run #{run.id}</div>
                        <div className="text-xs text-gray-400">{run.started_at}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                        run.status === 'completed' ? 'bg-emerald-900/50 text-emerald-300' :
                        run.status === 'failed' ? 'bg-red-900/50 text-red-300' :
                        run.status === 'running' ? 'bg-blue-900/50 text-blue-300' :
                        'bg-gray-700 text-gray-400'
                      }`}>
                        {run.status}
                      </span>
                      {run.error_message && <div className="text-xs text-red-400 mt-1">{run.error_message}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm !== null && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-sm w-full mx-4">
              <h3 className="text-lg font-semibold mb-2">Delete Workflow</h3>
              <p className="text-sm text-gray-400 mb-4">Are you sure you want to delete workflow #{deleteConfirm}? This cannot be undone.</p>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">Cancel</button>
                <button onClick={() => handleDelete(deleteConfirm)} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors">Delete</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
