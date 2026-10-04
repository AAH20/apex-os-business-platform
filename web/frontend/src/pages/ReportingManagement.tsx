import React, { useState, useEffect, useCallback } from 'react';
import { FileText, LayoutGrid, Clock, Users, Plus, Edit, Trash2, Search, Filter } from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Report {
  id: number;
  name: string;
  description?: string;
  report_type: string;
  config?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ReportTemplate {
  id: number;
  name: string;
  description?: string;
  category: string;
  query?: string;
  parameters?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface ScheduledReport {
  id: number;
  report_id: number;
  name: string;
  cron_expression: string;
  recipients: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ReportSubscription {
  id: number;
  user_id: number;
  report_id: number;
  delivery_method: string;
  frequency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type TabKey = 'reports' | 'templates' | 'scheduled' | 'subscriptions';

const API_BASE = '/api/reporting';
const API_KEY = 'test-api-key-12345';
const PAGE_SIZE = 10;

// ─── API Helpers ─────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY, ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

// ─── Main Component ──────────────────────────────────────────────────────────

const ReportingManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('reports');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reports state
  const [reports, setReports] = useState<Report[]>([]);
  const [reportsTotal, setReportsTotal] = useState(0);
  const [reportsPage, setReportsPage] = useState(1);

  // Templates state
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [templatesTotal, setTemplatesTotal] = useState(0);
  const [templatesPage, setTemplatesPage] = useState(1);

  // Scheduled state
  const [scheduled, setScheduled] = useState<ScheduledReport[]>([]);
  const [scheduledTotal, setScheduledTotal] = useState(0);
  const [scheduledPage, setScheduledPage] = useState(1);

  // Subscriptions state
  const [subscriptions, setSubscriptions] = useState<ReportSubscription[]>([]);
  const [subscriptionsTotal, setSubscriptionsTotal] = useState(0);
  const [subscriptionsPage, setSubscriptionsPage] = useState(1);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null);

  // Search
  const [search, setSearch] = useState('');

  // ─── Fetch Functions ──────────────────────────────────────────────────────

  const fetchReports = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ page: String(reportsPage), limit: String(PAGE_SIZE) });
      if (search) params.set('search', search);
      const data = await apiFetch<Report[] | { items: Report[]; total: number }>(`/reports?${params}`);
      if (Array.isArray(data)) { setReports(data); setReportsTotal(data.length); }
      else { setReports(data.items || []); setReportsTotal(data.total || 0); }
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, [reportsPage, search]);

  const fetchTemplates = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ page: String(templatesPage), limit: String(PAGE_SIZE) });
      const data = await apiFetch<ReportTemplate[] | { items: ReportTemplate[]; total: number }>(`/templates?${params}`);
      if (Array.isArray(data)) { setTemplates(data); setTemplatesTotal(data.length); }
      else { setTemplates(data.items || []); setTemplatesTotal(data.total || 0); }
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, [templatesPage]);

  const fetchScheduled = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ page: String(scheduledPage), limit: String(PAGE_SIZE) });
      const data = await apiFetch<ScheduledReport[] | { items: ScheduledReport[]; total: number }>(`/scheduled?${params}`);
      if (Array.isArray(data)) { setScheduled(data); setScheduledTotal(data.length); }
      else { setScheduled(data.items || []); setScheduledTotal(data.total || 0); }
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, [scheduledPage]);

  const fetchSubscriptions = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ page: String(subscriptionsPage), limit: String(PAGE_SIZE) });
      const data = await apiFetch<ReportSubscription[] | { items: ReportSubscription[]; total: number }>(`/subscriptions?${params}`);
      if (Array.isArray(data)) { setSubscriptions(data); setSubscriptionsTotal(data.length); }
      else { setSubscriptions(data.items || []); setSubscriptionsTotal(data.total || 0); }
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, [subscriptionsPage]);

  useEffect(() => { fetchReports(); }, [fetchReports]);
  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);
  useEffect(() => { fetchScheduled(); }, [fetchScheduled]);
  useEffect(() => { fetchSubscriptions(); }, [fetchSubscriptions]);

  // ─── CRUD Handlers ───────────────────────────────────────────────────────

  const handleCreate = () => {
    setEditingId(null);
    setFormData(getDefaultFormData(activeTab));
    setShowForm(true);
  };

  const handleEdit = (item: any) => {
    setEditingId(item.id);
    setFormData({ ...item });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `${activeTab}/${editingId}` : activeTab;
      const method = editingId ? 'PUT' : 'POST';
      await apiFetch(`/${url}`, { method, body: JSON.stringify(formData) });
      setShowForm(false);
      refreshActiveTab();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setError(null);
    try {
      await apiFetch(`/${activeTab}/${deleteConfirm.id}`, { method: 'DELETE' });
      setDeleteConfirm(null);
      refreshActiveTab();
    } catch (e: any) { setError(e.message); }
  };

  const refreshActiveTab = () => {
    switch (activeTab) {
      case 'reports': fetchReports(); break;
      case 'templates': fetchTemplates(); break;
      case 'scheduled': fetchScheduled(); break;
      case 'subscriptions': fetchSubscriptions(); break;
    }
  };

  const getDefaultFormData = (tab: TabKey): Record<string, unknown> => {
    switch (tab) {
      case 'reports': return { name: '', description: '', report_type: 'sales', is_active: true };
      case 'templates': return { name: '', description: '', category: 'general', query: '' };
      case 'scheduled': return { report_id: 1, name: '', cron_expression: '0 8 * * *', recipients: [], is_active: true };
      case 'subscriptions': return { user_id: 1, report_id: 1, delivery_method: 'email', frequency: 'weekly', is_active: true };
    }
  };

  // ─── Render Helpers ──────────────────────────────────────────────────────

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'reports', label: 'Reports', icon: <FileText size={16} /> },
    { key: 'templates', label: 'Templates', icon: <LayoutGrid size={16} /> },
    { key: 'scheduled', label: 'Scheduled', icon: <Clock size={16} /> },
    { key: 'subscriptions', label: 'Subscriptions', icon: <Users size={16} /> },
  ];

  const getCurrentData = () => {
    switch (activeTab) {
      case 'reports': return { data: reports, total: reportsTotal, page: reportsPage, setPage: setReportsPage };
      case 'templates': return { data: templates, total: templatesTotal, page: templatesPage, setPage: setTemplatesPage };
      case 'scheduled': return { data: scheduled, total: scheduledTotal, page: scheduledPage, setPage: setScheduledPage };
      case 'subscriptions': return { data: subscriptions, total: subscriptionsTotal, page: subscriptionsPage, setPage: setSubscriptionsPage };
    }
  };

  const { data: currentData, total: currentTotal, page: currentPage, setPage: setCurrentPage } = getCurrentData();
  const totalPages = Math.max(1, Math.ceil(currentTotal / PAGE_SIZE));

  const renderTable = () => {
    if (loading) return <div className="py-12 text-center text-gray-400">Loading...</div>;
    if (currentData.length === 0) return <div className="py-12 text-center text-gray-400">No {activeTab} found</div>;

    return (
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Name</th>
              {activeTab === 'reports' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Type</th>}
              {activeTab === 'templates' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Category</th>}
              {activeTab === 'scheduled' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Cron</th>}
              {activeTab === 'subscriptions' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Method</th>}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {currentData.map((item: any) => (
              <tr key={item.id} className="hover:bg-gray-800/30">
                <td className="px-4 py-3 text-sm text-gray-300">{item.id}</td>
                <td className="px-4 py-3 text-sm text-gray-100 font-medium">{item.name}</td>
                {activeTab === 'reports' && <td className="px-4 py-3 text-sm text-gray-300">{item.report_type}</td>}
                {activeTab === 'templates' && <td className="px-4 py-3 text-sm text-gray-300">{item.category}</td>}
                {activeTab === 'scheduled' && <td className="px-4 py-3 text-sm text-gray-300 font-mono text-xs">{item.cron_expression}</td>}
                {activeTab === 'subscriptions' && <td className="px-4 py-3 text-sm text-gray-300">{item.delivery_method}</td>}
                <td className="px-4 py-3 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${item.is_active ? 'bg-green-900/30 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                    {item.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm space-x-2">
                  <button onClick={() => handleEdit(item)} className="text-cyan-400 hover:text-cyan-300 font-medium">Edit</button>
                  <button onClick={() => setDeleteConfirm({ id: item.id, name: item.name })} className="text-red-400 hover:text-red-300 font-medium">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderForm = () => {
    if (!showForm) return null;
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-lg p-6 max-w-lg w-full mx-4 space-y-4 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-100">{editingId ? 'Edit' : 'Create'} {activeTab.slice(0, -1)}</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
              <input type="text" value={(formData.name as string) || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} required
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
            </div>
            {activeTab === 'reports' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                  <textarea value={(formData.description as string) || ''} onChange={e => setFormData({ ...formData, description: e.target.value })} rows={2}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Report Type</label>
                  <select value={(formData.report_type as string) || 'sales'} onChange={e => setFormData({ ...formData, report_type: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500">
                    <option value="sales">Sales</option>
                    <option value="inventory">Inventory</option>
                    <option value="financial">Financial</option>
                    <option value="customer">Customer</option>
                  </select>
                </div>
              </>
            )}
            {activeTab === 'templates' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Category</label>
                  <select value={(formData.category as string) || 'general'} onChange={e => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500">
                    <option value="general">General</option>
                    <option value="sales">Sales</option>
                    <option value="marketing">Marketing</option>
                    <option value="operations">Operations</option>
                    <option value="finance">Finance</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Query</label>
                  <textarea value={(formData.query as string) || ''} onChange={e => setFormData({ ...formData, query: e.target.value })} rows={3}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 font-mono text-sm focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
              </>
            )}
            {activeTab === 'scheduled' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Report ID</label>
                  <input type="number" value={(formData.report_id as number) || 1} onChange={e => setFormData({ ...formData, report_id: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Cron Expression *</label>
                  <input type="text" value={(formData.cron_expression as string) || ''} onChange={e => setFormData({ ...formData, cron_expression: e.target.value })} required
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 font-mono text-sm focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
              </>
            )}
            {activeTab === 'subscriptions' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">User ID</label>
                  <input type="number" value={(formData.user_id as number) || 1} onChange={e => setFormData({ ...formData, user_id: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Report ID</label>
                  <input type="number" value={(formData.report_id as number) || 1} onChange={e => setFormData({ ...formData, report_id: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Delivery Method</label>
                  <select value={(formData.delivery_method as string) || 'email'} onChange={e => setFormData({ ...formData, delivery_method: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500">
                    <option value="email">Email</option>
                    <option value="slack">Slack</option>
                    <option value="webhook">Webhook</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Frequency</label>
                  <select value={(formData.frequency as string) || 'weekly'} onChange={e => setFormData({ ...formData, frequency: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500">
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
              </>
            )}
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input type="checkbox" checked={(formData.is_active as boolean) ?? true} onChange={e => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded bg-gray-700 border-gray-600 text-cyan-500 focus:ring-cyan-500" />
                Active
              </label>
            </div>
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition">{editingId ? 'Update' : 'Create'}</button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  // ─── Main Render ─────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Reporting Management</h1>
        <button onClick={handleCreate} className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition flex items-center gap-2">
          <Plus size={16} /> New {activeTab.slice(0, -1)}
        </button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-900/20 border border-red-800 text-red-400 rounded-lg">{error}</div>}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-gray-800 rounded-lg p-1">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => { setActiveTab(tab.key); setSearch(''); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${activeTab === tab.key ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'}`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input type="text" placeholder={`Search ${activeTab}...`} value={search} onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
            className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-800 rounded-lg shadow overflow-hidden">
        {renderTable()}
        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-gray-700 bg-gray-800 px-4 py-3">
          <div className="text-sm text-gray-400">Page {currentPage} of {totalPages}</div>
          <div className="flex gap-2">
            <button onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage <= 1}
              className="px-3 py-1 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed">Previous</button>
            <button onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage >= totalPages}
              className="px-3 py-1 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed">Next</button>
          </div>
        </div>
      </div>

      {/* Form Modal */}
      {renderForm()}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 space-y-4 border border-gray-700">
            <h3 className="text-lg font-semibold text-gray-100">Confirm Delete</h3>
            <p className="text-gray-400">Are you sure you want to delete "{deleteConfirm.name}"? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportingManagement;
