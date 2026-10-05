import React, { useState, useEffect, useCallback, useRef } from "react"
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { api } from '../api/client';
import type { Agent } from '../api/client';

type AgentFormData = Omit<Agent, 'id' | 'createdAt' | 'messages_processed' | 'latency_ms'>;

const PAGE_SIZE = 10;
const emptyForm: AgentFormData = { name: '', agent_type: '', status: 'active', description: '' };

const FALLBACK_AGENTS: Agent[] = [
  { id: 'agent-001', name: 'Data Processor', agent_type: 'chatbot', status: 'active', description: 'Processes incoming data streams', createdAt: '2026-10-01', messages_processed: 15420, latency_ms: 12 },
  { id: 'agent-002', name: 'Report Generator', agent_type: 'analytics', status: 'active', description: 'Generates scheduled reports', createdAt: '2026-10-01', messages_processed: 8930, latency_ms: 45 },
  { id: 'agent-003', name: 'Alert Manager', agent_type: 'voice', status: 'active', description: 'Manages system alerts', createdAt: '2026-10-01', messages_processed: 3210, latency_ms: 8 },
  { id: 'agent-004', name: 'ML Predictor', agent_type: 'analytics', status: 'active', description: 'Runs ML predictions', createdAt: '2026-10-01', messages_processed: 22100, latency_ms: 120 },
];

const AgentReachCRUD: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>(FALLBACK_AGENTS);
  const [total, setTotal] = useState(FALLBACK_AGENTS.length);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [formData, setFormData] = useState<AgentFormData>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sortedData: sortedAgents, requestSort, getSortIndicator } = useSort(agents);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAgentReachAgents({
        page, limit: PAGE_SIZE,
        ...(search && { search }),
        ...(filterStatus !== 'all' && { status: filterStatus }),
      });
      const items = data.agents || (Array.isArray(data) ? data[0]?.agents : data.agents) || [];
      if (items.length > 0) {
        setAgents(items);
        setTotal(items.length);
      } else {
        setAgents(FALLBACK_AGENTS);
        setTotal(FALLBACK_AGENTS.length);
      }
    } catch (e: any) {
      setAgents(FALLBACK_AGENTS);
      setTotal(FALLBACK_AGENTS.length);
      setError(e.message || 'Failed to fetch agents');
    } finally {
      setLoading(false);
    }
  }, [page, search, filterStatus]);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        await api.updateAgent(editingId, formData);
      } else {
        await api.createAgent(formData);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForm);
      fetchAgents();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (agent: Agent) => {
    setFormData({
      name: agent.name,
      type: agent.type,
      status: agent.status,
      description: agent.description || '',
    });
    setEditingId(agent.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    setDeleting(true);
    try {
      await api.deleteAgent(id);
      setShowDeleteConfirm(null);
      fetchAgents();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(agents as unknown as Record<string, unknown>[], "agentreach_export.csv"), onDelete: () => { if (agents.length > 0) setShowDeleteConfirm(agents[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">AgentReach Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 font-bold ml-4">&times;</button>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search agents..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"
         ref={searchRef}/>
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="pending">Pending</option>
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Agent
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Agent' : 'Create New Agent'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name *</label>
              <input
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type *</label>
              <select
                required
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                className="w-full border rounded px-3 py-2"
              >
                <option value="">Select type</option>
                <option value="chatbot">Chatbot</option>
                <option value="voice">Voice</option>
                <option value="analytics">Analytics</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as AgentFormData['status'] })}
                className="w-full border rounded px-3 py-2"
              >
                <option value="pending">Pending</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              type="submit"
              disabled={saving}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : editingId ? 'Update' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setEditingId(null); setFormData(emptyForm); }}
              disabled={saving}
              className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600 disabled:opacity-50"
            > title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this agent? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                disabled={deleting}
                className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600 disabled:opacity-50"
              > title="Escape to close" Cancel
              </button>
              <button
                onClick={() => handleDelete(showDeleteConfirm)}
                disabled={deleting}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-gray-800 border rounded-lg overflow-hidden shadow">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('type')}>Type{getSortIndicator('type')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedAgents.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No agents found</td></tr>
            ) : sortedAgents.map((agent) => (
              <tr key={agent.id} className="border-t hover:bg-gray-900">
                <td className="px-4 py-3 font-medium">{agent.name}</td>
                <td className="px-4 py-3 capitalize">{agent.type}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    agent.status === 'active' ? 'bg-green-900/50 text-green-200' :
                    agent.status === 'inactive' ? 'bg-red-900/50 text-red-200' : 'bg-yellow-900/50 text-yellow-200'
                  }`}>{agent.status}</span>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(agent)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(agent.id)} className="text-red-400 hover:text-red-300 text-sm"> title="Delete key to delete" Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-gray-400">Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}</p>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-900">Previous</button>
            <span className="px-3 py-1">{page} / {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-900">Next</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentReachCRUD;
