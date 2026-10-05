import React, { useState, useEffect, useCallback } from 'react';
import { exportToCSV } from '../hooks/useKeyboardShortcuts';

interface Project {
  id: number;
  name: string;
  status: string;
  description: string;
}

const STATUSES = ['active', 'inactive', 'archived'];
const PAGE_SIZE = 10;

const ProjectManagement: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form, setForm] = useState({ name: '', status: 'active', description: '' });
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/projects/', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProjects(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const filtered = projects.filter(p => {
    const q = search.toLowerCase();
    const matchSearch = !q || p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q);
    const matchStatus = !statusFilter || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', status: 'active', description: '' });
    setShowForm(true);
  };

  const openEdit = (p: Project) => {
    setEditing(p);
    setForm({ name: p.name, status: p.status, description: p.description });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const url = editing ? `/api/projects/${editing.id}/` : '/api/projects/';
      const method = editing ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      fetchProjects();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${deleteTarget.id}/`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteTarget(null);
      fetchProjects();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setSaving(false);
    }
  };

  const inputClass = "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900";
  const btnPrimary = "px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 disabled:opacity-50";
  const btnSecondary = "px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 disabled:opacity-40";
  const btnDanger = "px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900";

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Projects</h1>
          <button onClick={openCreate} className={btnPrimary} aria-label="Create new project">
            + New Project
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm" role="alert" aria-live="assertive">{error}</div>
        )}

        <div className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className={`flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500 ${inputClass.split(' ').filter(c => c.startsWith('focus-visible:')).join(' ')}`}
            aria-label="Search projects"
          />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            aria-label="Filter by status"
          >
            <option value="">All Statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button
            onClick={() => exportToCSV(projects as unknown as Record<string, unknown>[], 'projects_export.csv')}
            className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Export CSV
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm" role="table" aria-label="Projects table">
            <thead className="bg-gray-700">
              <tr>
                <th className="text-left px-4 py-3" scope="col">Name</th>
                <th className="text-left px-4 py-3" scope="col">Status</th>
                <th className="text-left px-4 py-3" scope="col">Description</th>
                <th className="text-right px-4 py-3" scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400" role="status" aria-live="polite">Loading...</td></tr>
              ) : paginated.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-16 text-center">
                  <div className="text-5xl mb-4">📋</div>
                  <h3 className="text-lg font-semibold text-gray-100 mb-2">No projects yet</h3>
                  <p className="text-gray-400 mb-4">Get started by creating your first project.</p>
                  <button onClick={openCreate} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                    + New Project
                  </button>
                </td></tr>
              ) : (
                paginated.map(p => (
                  <tr key={p.id} className="border-t border-gray-700 hover:bg-gray-600">
                    <td className="px-4 py-3 font-medium">{p.name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        p.status === 'active' ? 'bg-green-900/50 text-green-300' :
                        p.status === 'inactive' ? 'bg-yellow-900/50 text-yellow-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>{p.status}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{p.description}</td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button onClick={() => openEdit(p)} className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900" aria-label={`Edit project ${p.name}`}>Edit</button>
                      <button onClick={() => setDeleteTarget(p)} className="px-3 py-1 bg-red-900/50 hover:bg-red-800 text-red-200 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900" aria-label={`Delete project ${p.name}`}>Delete</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              aria-label="Go to previous page"
            >Prev</button>
            <span className="text-sm text-gray-400" aria-live="polite">Page {safePage} of {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
              aria-label="Go to next page"
            >Next</button>
          </div>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="project-form-title">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700">
              <h2 className="text-lg font-semibold mb-4" id="project-form-title">{editing ? 'Edit Project' : 'New Project'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1" htmlFor="project-name">Name</label>
                  <input
                    id="project-name"
                    type="text"
                    required
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    className={inputClass}
                    aria-label="Project name"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1" htmlFor="project-status">Status</label>
                  <select
                    id="project-status"
                    value={form.status}
                    onChange={e => setForm({ ...form, status: e.target.value })}
                    className={inputClass}
                    aria-label="Project status"
                  >
                    {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1" htmlFor="project-description">Description</label>
                  <textarea
                    id="project-description"
                    rows={3}
                    value={form.description}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                    className={inputClass}
                    aria-label="Project description"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button type="button" onClick={() => setShowForm(false)} className={btnSecondary} aria-label="Cancel project form">Cancel</button>
                  <button type="submit" disabled={saving} className={btnPrimary} aria-label={editing ? 'Update project' : 'Create project'}>
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteTarget && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="delete-project-title">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm border border-gray-700">
              <h2 className="text-lg font-semibold mb-2" id="delete-project-title">Delete Project</h2>
              <p className="text-sm text-gray-400 mb-4">Are you sure you want to delete "{deleteTarget.name}"? This action cannot be undone.</p>
              <div className="flex justify-end gap-2">
                <button onClick={() => setDeleteTarget(null)} className={btnSecondary} aria-label="Cancel delete">Cancel</button>
                <button onClick={handleDelete} disabled={saving} className={btnDanger} aria-label={`Confirm delete project ${deleteTarget.name}`}>
                  {saving ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectManagement;
