import React, { useState, useEffect, useCallback } from 'react';

interface Report {
  id: string;
  name: string;
  description: string;
  query: string;
  schedule: string;
  status: 'active' | 'paused' | 'draft';
  createdAt: string;
  updatedAt: string;
}

interface ReportFormData {
  name: string;
  description: string;
  query: string;
  schedule: string;
  status: 'active' | 'paused' | 'draft';
}

const API_BASE = '/api/reports';
const PAGE_SIZE = 10;

const emptyForm: ReportFormData = { name: '', description: '', query: '', schedule: '', status: 'draft' };

const ContinuousBICRUD: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [formData, setFormData] = useState<ReportFormData>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) });
      if (search) params.set('search', search);
      if (statusFilter !== 'all') params.set('status', statusFilter);
      const res = await fetch(`${API_BASE}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setReports(data.reports || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForm);
      fetchReports();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    }
  };

  const handleEdit = (report: Report) => {
    setFormData({ name: report.name, description: report.description, query: report.query, schedule: report.schedule, status: report.status });
    setEditingId(report.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchReports();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">ContinuousBI Reports</h1>
      {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          placeholder="Search reports..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1"
        />
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="draft">Draft</option>
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Report
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">{editingId ? 'Edit Report' : 'Create Report'}</h2>
          <div className="grid grid-cols-2 gap-3">
            <input required placeholder="Name" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="border rounded px-3 py-2" />
            <input placeholder="Schedule (cron)" value={formData.schedule} onChange={e => setFormData({ ...formData, schedule: e.target.value })} className="border rounded px-3 py-2" />
            <textarea placeholder="Description" value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="border rounded px-3 py-2 col-span-2" rows={2} />
            <textarea required placeholder="SQL Query" value={formData.query} onChange={e => setFormData({ ...formData, query: e.target.value })} className="border rounded px-3 py-2 col-span-2 font-mono" rows={3} />
            <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value as ReportFormData['status'] })} className="border rounded px-3 py-2">
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
            </select>
          </div>
          <div className="flex gap-2 mt-3">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); }} className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Reports Table */}
      <div className="bg-white border rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Schedule</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Updated</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : reports.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No reports found</td></tr>
            ) : (
              reports.map(r => (
                <tr key={r.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{r.name}</td>
                  <td className="px-4 py-2 font-mono text-xs">{r.schedule || '—'}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${r.status === 'active' ? 'bg-green-100 text-green-700' : r.status === 'paused' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500">{new Date(r.updatedAt).toLocaleDateString()}</td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleEdit(r)} className="text-blue-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(r.id)} className="text-red-600 hover:underline">Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
          <span className="px-3 py-1">Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded p-6 shadow-lg max-w-sm w-full">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to delete this report? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContinuousBICRUD;
