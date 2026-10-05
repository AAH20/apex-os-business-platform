import React, { useState, useEffect, useCallback } from 'react';
import { FALLBACK_REPORTS } from '../api/fallback';

interface Report {
  id: string;
  name: string;
  type: 'sales' | 'inventory' | 'financial' | 'customer' | 'custom';
  description: string;
  schedule: 'daily' | 'weekly' | 'monthly' | 'none';
  recipients: string[];
  status: 'active' | 'paused' | 'draft';
  deliveryStatus: 'delivered' | 'pending' | 'failed';
  views: number;
  downloads: number;
  lastRun?: string;
  createdAt: string;
}

interface ReportFormData {
  name: string;
  type: Report['type'];
  description: string;
  schedule: Report['schedule'];
  recipients: string[];
  status: Report['status'];
}

const API_BASE = '/api/reporting/reports';
const PAGE_SIZE = 10;

const defaultFormData: ReportFormData = {
  name: '', type: 'sales', description: '', schedule: 'weekly', recipients: [], status: 'draft',
};

const typeLabels: Record<Report['type'], string> = {
  sales: 'Sales', inventory: 'Inventory', financial: 'Financial', customer: 'Customer', custom: 'Custom',
};
const scheduleLabels: Record<Report['schedule'], string> = {
  daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly', none: 'None',
};
const statusColors: Record<Report['status'], string> = {
  active: 'bg-green-900/50 text-green-200', paused: 'bg-yellow-900/50 text-yellow-200', draft: 'bg-gray-800 text-gray-200',
};
const deliveryColors: Record<Report['deliveryStatus'], string> = {
  delivered: 'bg-green-900/50 text-green-200', pending: 'bg-blue-900/50 text-blue-200', failed: 'bg-red-900/50 text-red-200',
};

const ReportManagement: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingReport, setEditingReport] = useState<Report | null>(null);
  const [formData, setFormData] = useState<ReportFormData>(defaultFormData);
  const [recipientInput, setRecipientInput] = useState('');
  const [showPreview, setShowPreview] = useState<Report | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<Report | null>(null);

  const fetchReports = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) });
      if (search) params.set('search', search);
      if (filterType !== 'all') params.set('type', filterType);
      if (filterStatus !== 'all') params.set('status', filterStatus);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${API_BASE}?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' }, signal: controller.signal });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`Failed to fetch reports: ${res.status}`);
      const data = await res.json();
      // Handle both bare arrays and object-wrapped responses
      if (Array.isArray(data)) {
        setReports(data);
        setTotal(data.length);
      } else if (data && typeof data === 'object') {
        setReports(data.items || data.data || data.reports || []);
        setTotal(data.total || (data.items || data.data || data.reports || []).length);
      } else {
        setReports([]);
        setTotal(0);
      }
    } catch (e: any) {
      // Fallback to synthetic data when API is unreachable
      setReports(FALLBACK_REPORTS);
      setTotal(FALLBACK_REPORTS.length);
      setError('API unavailable — showing sample data');
    } finally { setLoading(false); }
  }, [page, search, filterType, filterStatus]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const openCreate = () => { setEditingReport(null); setFormData(defaultFormData); setRecipientInput(''); setShowForm(true); };
  const openEdit = (r: Report) => {
    setEditingReport(r);
    setFormData({ name: r.name, type: r.type, description: r.description, schedule: r.schedule, recipients: [...r.recipients], status: r.status });
    setRecipientInput(''); setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingReport ? `${API_BASE}/${editingReport.id}` : API_BASE;
      const method = editingReport ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method, headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' }, body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`Failed to ${editingReport ? 'update' : 'create'} report: ${res.status}`);
      setShowForm(false); fetchReports();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async () => {
    if (!showDeleteConfirm) return;
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/${showDeleteConfirm.id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`Failed to delete report: ${res.status}`);
      setShowDeleteConfirm(null); fetchReports();
    } catch (e: any) { setError(e.message); }
  };

  const addRecipient = () => {
    const email = recipientInput.trim();
    if (email && !formData.recipients.includes(email)) {
      setFormData(prev => ({ ...prev, recipients: [...prev.recipients, email] }));
    }
    setRecipientInput('');
  };

  const removeRecipient = (email: string) => {
    setFormData(prev => ({ ...prev, recipients: prev.recipients.filter(r => r !== email) }));
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Report Management</h1>
        <button onClick={openCreate} className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition">
          + New Report
        </button>
        <button
          onClick={() => {
            const headers = ['ID', 'Name', 'Type', 'Schedule', 'Status', 'Delivery', 'Views', 'Downloads'];
            const rows = reports.map(r => [r.id, r.name, r.type, r.schedule, r.status, r.deliveryStatus, r.views, r.downloads]);
            const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'reports_export.csv';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
        >
          Export CSV
        </button>
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(reports, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'reports_export.json';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
        >
          Export JSON
        </button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-900/20 border border-red-800 text-red-400 rounded-lg">{error}</div>}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input type="text" placeholder="Search reports..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-700 rounded-lg flex-1 min-w-[200px] focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
        <select value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-700 rounded-lg">
          <option value="all">All Types</option>
          {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-700 rounded-lg">
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="draft">Draft</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Schedule</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Delivery</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Views</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Downloads</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : reports.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-16 text-center">
                  <div className="text-5xl mb-4">📊</div>
                  <h3 className="text-lg font-semibold text-gray-100 mb-2">No reports yet</h3>
                  <p className="text-gray-400 mb-4">Get started by creating your first report.</p>
                  <button onClick={openCreate} className="bg-cyan-600 hover:bg-cyan-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                    + New Report
                  </button>
                </td></tr>
              ) : reports.map(r => (
                <tr key={r.id} className="hover:bg-gray-700">
                  <td className="px-4 py-3 font-medium text-gray-100">{r.name}</td>
                  <td className="px-4 py-3 text-gray-400">{typeLabels[r.type]}</td>
                  <td className="px-4 py-3 text-gray-400">{scheduleLabels[r.schedule]}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[r.status]}`}>{r.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${deliveryColors[r.deliveryStatus]}`}>{r.deliveryStatus}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{r.views}</td>
                  <td className="px-4 py-3 text-gray-400">{r.downloads}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => setShowPreview(r)} className="text-blue-400 hover:text-blue-300 text-sm">Preview</button>
                      <button onClick={() => openEdit(r)} className="text-green-400 hover:text-green-300 text-sm">Edit</button>
                      <button onClick={() => setShowDeleteConfirm(r)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        <div className="flex justify-between items-center px-4 py-3 bg-gray-800/50 border-t">
          <span className="text-sm text-gray-400">Showing {reports.length} of {total} reports</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
              className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-700">Previous</button>
            <span className="px-3 py-1 text-sm">Page {page} of {totalPages || 1}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-700">Next</button>
          </div>
        </div>
      </div>

      {/* Create/Edit Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-xl font-bold mb-4">{editingReport ? 'Edit Report' : 'Create New Report'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
                  <input type="text" required value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
                  <select value={formData.type} onChange={e => setFormData(p => ({ ...p, type: e.target.value as Report['type'] }))}
                    className="w-full px-3 py-2 border border-gray-700 rounded-lg">
                    {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                  <textarea value={formData.description} onChange={e => setFormData(p => ({ ...p, description: e.target.value }))} rows={3}
                    className="w-full px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Schedule</label>
                  <select value={formData.schedule} onChange={e => setFormData(p => ({ ...p, schedule: e.target.value as Report['schedule'] }))}
                    className="w-full px-3 py-2 border border-gray-700 rounded-lg">
                    {Object.entries(scheduleLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                  <select value={formData.status} onChange={e => setFormData(p => ({ ...p, status: e.target.value as Report['status'] }))}
                    className="w-full px-3 py-2 border border-gray-700 rounded-lg">
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="paused">Paused</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Recipients</label>
                  <div className="flex gap-2">
                    <input type="email" value={recipientInput} onChange={e => setRecipientInput(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addRecipient(); } }}
                      placeholder="email@example.com" className="flex-1 px-3 py-2 border border-gray-700 rounded-lg" />
                    <button type="button" onClick={addRecipient} className="px-3 py-2 bg-gray-700 rounded-lg hover:bg-gray-600">Add</button>
                  </div>
                  {formData.recipients.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {formData.recipients.map(email => (
                        <span key={email} className="px-2 py-1 bg-blue-900/50 text-blue-200 text-sm rounded-full flex items-center gap-1">
                          {email}
                          <button type="button" onClick={() => removeRecipient(email)} className="text-blue-400 hover:text-red-400">&times;</button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-3 pt-4">
                  <button type="submit" className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700">
                    {editingReport ? 'Update Report' : 'Create Report'}
                  </button>
                  <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border border-gray-700 rounded-lg hover:bg-gray-700">Cancel</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-bold">{showPreview.name}</h2>
                <button onClick={() => setShowPreview(null)} className="text-gray-400 hover:text-gray-400 text-2xl">&times;</button>
              </div>
              <div className="space-y-3 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div><span className="font-medium text-gray-400">Type:</span> <span className="ml-1">{typeLabels[showPreview.type]}</span></div>
                  <div><span className="font-medium text-gray-400">Schedule:</span> <span className="ml-1">{scheduleLabels[showPreview.schedule]}</span></div>
                  <div><span className="font-medium text-gray-400">Status:</span> <span className={`ml-1 px-2 py-0.5 text-xs rounded-full ${statusColors[showPreview.status]}`}>{showPreview.status}</span></div>
                  <div><span className="font-medium text-gray-400">Delivery:</span> <span className={`ml-1 px-2 py-0.5 text-xs rounded-full ${deliveryColors[showPreview.deliveryStatus]}`}>{showPreview.deliveryStatus}</span></div>
                </div>
                {showPreview.description && <div><span className="font-medium text-gray-400">Description:</span><p className="mt-1 text-gray-300">{showPreview.description}</p></div>}
                <div><span className="font-medium text-gray-400">Recipients:</span> {showPreview.recipients.length > 0 ? (
                  <div className="mt-1 flex flex-wrap gap-1">{showPreview.recipients.map(e => <span key={e} className="px-2 py-0.5 bg-gray-800 rounded text-xs">{e}</span>)}</div>
                ) : <span className="text-gray-400 ml-1">None</span>}</div>
                <div className="border-t pt-3 mt-3">
                  <h3 className="font-medium text-gray-300 mb-2">Analytics</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-900/30 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-blue-400">{showPreview.views}</div>
                      <div className="text-xs text-gray-400">Views</div>
                    </div>
                    <div className="bg-green-900/30 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-green-400">{showPreview.downloads}</div>
                      <div className="text-xs text-gray-400">Downloads</div>
                    </div>
                  </div>
                </div>
                {showPreview.lastRun && <div><span className="font-medium text-gray-400">Last Run:</span> <span className="ml-1">{new Date(showPreview.lastRun).toLocaleString()}</span></div>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-2">Delete Report</h2>
            <p className="text-gray-400 mb-6">Are you sure you want to delete <strong>{showDeleteConfirm.name}</strong>? This action cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={handleDelete} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Delete</button>
              <button onClick={() => setShowDeleteConfirm(null)} className="flex-1 px-4 py-2 border border-gray-700 rounded-lg hover:bg-gray-700">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportManagement;
