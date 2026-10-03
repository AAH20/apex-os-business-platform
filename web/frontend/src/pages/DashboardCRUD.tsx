import React, { useState, useEffect, useCallback , useRef} from "react";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Dashboard {
  id: string;
  name: string;
  description: string;
  widgets: number;
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

interface DashboardFormData {
  name: string;
  description: string;
  isPublic: boolean;
}

interface PaginatedResponse {
  data: Dashboard[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

const DashboardCRUD: React.FC = () => {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [filterPublic, setFilterPublic] = useState<'all' | 'public' | 'private'>('all');
  const [showForm, setShowForm] = useState(false);
  const [editingDashboard, setEditingDashboard] = useState<Dashboard | null>(null);
  const [formData, setFormData] = useState<DashboardFormData>({ name: '', description: '', isPublic: false });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<Partial<DashboardFormData>>({});
  const [submitting, setSubmitting] = useState(false);

  const limit = 10;

  const fetchDashboards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { page: String(page), limit: String(limit) };
      if (search) params.search = search;
      if (filterPublic !== 'all') params.isPublic = String(filterPublic === 'public');
      const qs = new URLSearchParams(params).toString();
      const res = await fetch(`/dashboard${qs ? `?${qs}` : ''}`);
      if (!res.ok) throw new Error(`Failed to load dashboards: ${res.status}`);
      const json = await res.json() as PaginatedResponse;
      setDashboards(json.data);
      setTotalPages(json.totalPages);
      setTotal(json.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboards');
    } finally {
      setLoading(false);
    }
  }, [page, search, filterPublic]);

  useEffect(() => { fetchDashboards(); }, [fetchDashboards]);

  const validateForm = (): boolean => {
    const errors: Partial<DashboardFormData> = {};
    if (!formData.name.trim()) errors.name = 'Name is required';
    else if (formData.name.length > 100) errors.name = 'Name must be under 100 characters';
    if (formData.description.length > 500) errors.description = 'Description must be under 500 characters';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const resetForm = () => {
    setFormData({ name: '', description: '', isPublic: false });
    setFormErrors({});
    setEditingDashboard(null);
    setShowForm(false);
  };

  const openCreateForm = () => {
    setFormData({ name: '', description: '', isPublic: false });
    setFormErrors({});
    setEditingDashboard(null);
    setShowForm(true);
  };

  const openCreate = openCreateForm;

  const openEditForm = (dashboard: Dashboard) => {
    setFormData({ name: dashboard.name, description: dashboard.description, isPublic: dashboard.isPublic });
    setFormErrors({});
    setEditingDashboard(dashboard);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    setSubmitting(true);
    setError(null);
    try {
      if (editingDashboard) {
        const res = await fetch(`/dashboard/${editingDashboard.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData) });
        if (!res.ok) throw new Error(`Failed to update dashboard: ${res.status}`);
      } else {
        const res = await fetch('/dashboard', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData) });
        if (!res.ok) throw new Error(`Failed to create dashboard: ${res.status}`);
      }
      await fetchDashboards();
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save dashboard');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/dashboard/${deletingId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Failed to delete dashboard: ${res.status}`);
      if (dashboards.length === 1 && page > 1) setPage(page - 1);
      await fetchDashboards();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete dashboard');
    } finally {
      setLoading(false);
      setShowDeleteConfirm(false);
      setDeletingId(null);
    }
  };

  const openDeleteConfirm = (id: string) => { setDeletingId(id); setShowDeleteConfirm(true); };

  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString();

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreate, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(dashboards as unknown as Record<string, unknown>[], "dashboard_export.csv"), onDelete: () => { if (dashboards.length > 0) { setDeletingId(dashboards[0].id); setShowDeleteConfirm(true); } }, onClose: resetForm });

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboards</h1>
        <button onClick={openCreateForm} disabled={loading || submitting} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"> title="Ctrl+N"
          + New Dashboard
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <input
          type="text" placeholder="Search dashboards..." value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
         ref={searchRef}/>
        <select
          value={filterPublic} onChange={(e) => { setFilterPublic(e.target.value as 'all' | 'public' | 'private'); setPage(1); }}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="all">All</option>
          <option value="public">Public</option>
          <option value="private">Private</option>
        </select>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">{error}</div>}

      {showForm && (
        <div className="mb-6 p-6 bg-white border border-gray-200 rounded-lg shadow-sm">
          <h2 className="text-lg font-semibold mb-4">{editingDashboard ? 'Edit Dashboard' : 'Create Dashboard'}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text" value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className={`w-full px-3 py-2 border rounded-lg ${formErrors.name ? 'border-red-500' : 'border-gray-300'}`}
              />
              {formErrors.name && <p className="mt-1 text-sm text-red-600">{formErrors.name}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={formData.description} rows={3}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className={`w-full px-3 py-2 border rounded-lg ${formErrors.description ? 'border-red-500' : 'border-gray-300'}`}
              />
              {formErrors.description && <p className="mt-1 text-sm text-red-600">{formErrors.description}</p>}
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox" checked={formData.isPublic}
                onChange={(e) => setFormData({ ...formData, isPublic: e.target.checked })}
                className="w-4 h-4 text-blue-600"
              />
              <label className="text-sm text-gray-700">Public dashboard</label>
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={submitting} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {submitting ? 'Saving...' : editingDashboard ? 'Update' : 'Create'}
              </button>
              <button type="button" onClick={resetForm} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"> title="Escape to close" Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Delete Dashboard</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to delete this dashboard? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => { setShowDeleteConfirm(false); setDeletingId(null); }} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"> title="Escape to close" Cancel
              </button>
              <button onClick={handleDelete} disabled={loading} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : dashboards.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No dashboards found.</div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-6">
            {dashboards.map((dashboard) => (
              <div key={dashboard.id} className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-gray-900 truncate">{dashboard.name}</h3>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${dashboard.isPublic ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                    {dashboard.isPublic ? 'Public' : 'Private'}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{dashboard.description || 'No description'}</p>
                <div className="text-xs text-gray-500 mb-3">
                  {dashboard.widgets} widgets · Updated {formatDate(dashboard.updatedAt)}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => openEditForm(dashboard)} className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                    Edit
                  </button>
                  <button onClick={() => openDeleteConfirm(dashboard.id)} className="px-3 py-1.5 text-sm bg-red-50 text-red-600 rounded hover:bg-red-100"> title="Delete key to delete" Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600">Showing {dashboards.length} of {total} dashboards</p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1 || loading}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="px-3 py-1.5 text-sm text-gray-700">Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages || loading}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DashboardCRUD;
