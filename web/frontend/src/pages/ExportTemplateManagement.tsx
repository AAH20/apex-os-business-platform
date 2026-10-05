import React, { useState, useEffect, useCallback } from 'react';
import { FileText, Download, Clock, Plus, Search, Eye, Trash2, Edit, Play } from 'lucide-react';
import { api } from '../api/client';
import { exportToCSV } from '../hooks/useKeyboardShortcuts';
import type { ExportTemplate, ExportJob, ExportSchedule } from '../api/client';

type TabKey = 'templates' | 'jobs' | 'schedules';

const PAGE_SIZE = 10;

const ExportTemplateManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('templates');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Data state
  const [templates, setTemplates] = useState<ExportTemplate[]>([]);
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  const [schedules, setSchedules] = useState<ExportSchedule[]>([]);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  // Preview state
  const [previewTemplate, setPreviewTemplate] = useState<ExportTemplate | null>(null);

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null);

  // ─── Fetch Functions ──────────────────────────────────────────────────────

  const fetchTemplates = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.getExportTemplates({ page: 1, limit: PAGE_SIZE });
      setTemplates(data);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, []);

  const fetchJobs = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.getExportJobs({ page: 1, limit: PAGE_SIZE });
      setJobs(data);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, []);

  const fetchSchedules = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.getExportSchedules({ page: 1, limit: PAGE_SIZE });
      setSchedules(data);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);
  useEffect(() => { fetchJobs(); }, [fetchJobs]);
  useEffect(() => { fetchSchedules(); }, [fetchSchedules]);

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
      if (activeTab === 'templates') {
        if (editingId) await api.updateExportTemplate(editingId, formData);
        else await api.createExportTemplate(formData as any);
      } else if (activeTab === 'jobs') {
        if (editingId) await api.updateExportJob(editingId, formData);
        else await api.createExportJob(formData as any);
      } else {
        if (editingId) await api.updateExportSchedule(editingId, formData);
        else await api.createExportSchedule(formData as any);
      }
      setShowForm(false);
      refreshActiveTab();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setError(null);
    try {
      if (activeTab === 'templates') await api.deleteExportTemplate(deleteConfirm.id);
      else if (activeTab === 'jobs') await api.deleteExportJob(deleteConfirm.id);
      else await api.deleteExportSchedule(deleteConfirm.id);
      setDeleteConfirm(null);
      refreshActiveTab();
    } catch (e: any) { setError(e.message); }
  };

  const handlePreview = (template: ExportTemplate) => {
    setPreviewTemplate(template);
  };

  const handleRunExport = async (template: ExportTemplate) => {
    setError(null);
    try {
      await api.createExportJob({
        template_id: template.id,
        name: `Run: ${template.name}`,
        status: 'pending',
      });
      fetchJobs();
    } catch (e: any) { setError(e.message); }
  };

  const refreshActiveTab = () => {
    switch (activeTab) {
      case 'templates': fetchTemplates(); break;
      case 'jobs': fetchJobs(); break;
      case 'schedules': fetchSchedules(); break;
    }
  };

  const getDefaultFormData = (tab: TabKey): Record<string, unknown> => {
    switch (tab) {
      case 'templates': return { name: '', description: '', category: 'general', format: 'csv', query: '', is_active: true };
      case 'jobs': return { template_id: 1, name: '', status: 'pending' };
      case 'schedules': return { template_id: 1, name: '', cron_expression: '0 8 * * *', recipients: [], is_active: true };
    }
  };

  // ─── Render Helpers ──────────────────────────────────────────────────────

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'templates', label: 'Templates', icon: <FileText size={16} /> },
    { key: 'jobs', label: 'Jobs', icon: <Download size={16} /> },
    { key: 'schedules', label: 'Schedules', icon: <Clock size={16} /> },
  ];

  const getCurrentData = (): any[] => {
    let data: any[] = [];
    switch (activeTab) {
      case 'templates': data = templates; break;
      case 'jobs': data = jobs; break;
      case 'schedules': data = schedules; break;
    }
    if (search) {
      data = data.filter((item: any) =>
        item.name?.toLowerCase().includes(search.toLowerCase()) ||
        item.category?.toLowerCase().includes(search.toLowerCase()) ||
        item.status?.toLowerCase().includes(search.toLowerCase())
      );
    }
    return data;
  };

  const currentData = getCurrentData();

  const renderTable = () => {
    if (loading) return <div className="py-12 text-center text-gray-400"><div className="flex items-center justify-center gap-2"><div className="animate-spin rounded-full border-2 border-gray-600 border-t-cyan-500 h-8 w-8"></div><span>Loading...</span></div></div>;
    if (currentData.length === 0) return <div className="py-12 text-center text-gray-400">No {activeTab} found</div>;

    return (
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Name</th>
              {activeTab === 'templates' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Category</th>}
              {activeTab === 'templates' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Format</th>}
              {activeTab === 'jobs' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>}
              {activeTab === 'jobs' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Rows</th>}
              {activeTab === 'schedules' && <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Cron</th>}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Active</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {currentData.map((item: any) => (
              <tr key={item.id} className="hover:bg-gray-800/30">
                <td className="px-4 py-3 text-sm text-gray-300">{item.id}</td>
                <td className="px-4 py-3 text-sm text-gray-100 font-medium">{item.name}</td>
                {activeTab === 'templates' && <td className="px-4 py-3 text-sm text-gray-300">{item.category}</td>}
                {activeTab === 'templates' && <td className="px-4 py-3 text-sm text-gray-300">{item.format}</td>}
                {activeTab === 'jobs' && (
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      item.status === 'completed' ? 'bg-green-900/30 text-green-400' :
                      item.status === 'running' ? 'bg-blue-900/30 text-blue-400' :
                      item.status === 'failed' ? 'bg-red-900/30 text-red-400' :
                      'bg-gray-700 text-gray-400'
                    }`}>{item.status}</span>
                  </td>
                )}
                {activeTab === 'jobs' && <td className="px-4 py-3 text-sm text-gray-300">{item.row_count ?? '-'}</td>}
                {activeTab === 'schedules' && <td className="px-4 py-3 text-sm text-gray-300 font-mono text-xs">{item.cron_expression}</td>}
                <td className="px-4 py-3 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${item.is_active ? 'bg-green-900/30 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                    {item.is_active ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm space-x-2">
                  {activeTab === 'templates' && (
                    <>
                      <button onClick={() => handlePreview(item)} className="text-cyan-400 hover:text-cyan-300" title="Preview"><Eye size={14} /></button>
                      <button onClick={() => handleRunExport(item)} className="text-green-400 hover:text-green-300" title="Run Export"><Play size={14} /></button>
                    </>
                  )}
                  <button onClick={() => handleEdit(item)} className="text-cyan-400 hover:text-cyan-300" title="Edit"><Edit size={14} /></button>
                  <button onClick={() => setDeleteConfirm({ id: item.id, name: item.name })} className="text-red-400 hover:text-red-300" title="Delete"><Trash2 size={14} /></button>
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
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowForm(false)}>
        <div className="bg-gray-800 rounded-lg p-6 max-w-lg w-full mx-4 space-y-4 border border-gray-700" onClick={e => e.stopPropagation()}>
          <h3 className="text-lg font-semibold text-gray-100">{editingId ? 'Edit' : 'Create'} {activeTab.slice(0, -1)}</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
              <input type="text" value={(formData.name as string) || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} required
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
            </div>
            {activeTab === 'templates' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                  <textarea value={(formData.description as string) || ''} onChange={e => setFormData({ ...formData, description: e.target.value })} rows={2}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
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
                  <label className="block text-sm font-medium text-gray-300 mb-1">Format</label>
                  <select value={(formData.format as string) || 'csv'} onChange={e => setFormData({ ...formData, format: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500">
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                    <option value="xlsx">XLSX</option>
                    <option value="pdf">PDF</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Query</label>
                  <textarea value={(formData.query as string) || ''} onChange={e => setFormData({ ...formData, query: e.target.value })} rows={3}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 font-mono text-sm focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
              </>
            )}
            {activeTab === 'jobs' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Template ID</label>
                  <input type="number" value={(formData.template_id as number) || 1} onChange={e => setFormData({ ...formData, template_id: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                  <select value={(formData.status as string) || 'pending'} onChange={e => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500">
                    <option value="pending">Pending</option>
                    <option value="running">Running</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>
              </>
            )}
            {activeTab === 'schedules' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Template ID</label>
                  <input type="number" value={(formData.template_id as number) || 1} onChange={e => setFormData({ ...formData, template_id: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Cron Expression *</label>
                  <input type="text" value={(formData.cron_expression as string) || ''} onChange={e => setFormData({ ...formData, cron_expression: e.target.value })} required
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 font-mono text-sm focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Recipients (comma-separated)</label>
                  <input type="text" value={(formData.recipients as string[])?.join(', ') || ''} onChange={e => setFormData({ ...formData, recipients: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
                </div>
              </>
            )}
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={(formData.is_active as boolean) ?? true} onChange={e => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded bg-gray-700 border-gray-600 text-cyan-500 focus:ring-cyan-500" />
              <label className="text-sm text-gray-300">Active</label>
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

  const renderPreview = () => {
    if (!previewTemplate) return null;
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setPreviewTemplate(null)}>
        <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 space-y-4 border border-gray-700" onClick={e => e.stopPropagation()}>
          <h3 className="text-lg font-semibold text-gray-100">Preview: {previewTemplate.name}</h3>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-gray-400">Category:</span> <span className="text-gray-200">{previewTemplate.category}</span></div>
              <div><span className="text-gray-400">Format:</span> <span className="text-gray-200">{previewTemplate.format}</span></div>
              <div><span className="text-gray-400">Active:</span> <span className="text-gray-200">{previewTemplate.is_active ? 'Yes' : 'No'}</span></div>
              <div><span className="text-gray-400">Created:</span> <span className="text-gray-200">{previewTemplate.created_at}</span></div>
            </div>
            {previewTemplate.description && (
              <div><span className="text-gray-400 text-sm">Description:</span><p className="text-gray-200 text-sm mt-1">{previewTemplate.description}</p></div>
            )}
            {previewTemplate.query && (
              <div>
                <span className="text-gray-400 text-sm">Query:</span>
                <pre className="mt-1 p-3 bg-gray-900 rounded text-xs text-green-400 font-mono overflow-x-auto">{previewTemplate.query}</pre>
              </div>
            )}
            {previewTemplate.parameters && (
              <div>
                <span className="text-gray-400 text-sm">Parameters:</span>
                <pre className="mt-1 p-3 bg-gray-900 rounded text-xs text-cyan-400 font-mono overflow-x-auto">{JSON.stringify(previewTemplate.parameters, null, 2)}</pre>
              </div>
            )}
          </div>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setPreviewTemplate(null)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition">Close</button>
            <button onClick={() => { handleRunExport(previewTemplate); setPreviewTemplate(null); }} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition flex items-center gap-2"><Play size={14} /> Run Export</button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Export Templates</h1>
          <p className="text-gray-400 text-sm mt-1">Manage export templates, jobs, and schedules</p>
        </div>
        <button onClick={handleCreate} className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition">
          <Plus size={16} /> Create {activeTab.slice(0, -1)}
        </button>
        <button onClick={() => exportToCSV(currentData() as unknown as Record<string, unknown>[], `${activeTab}_export.csv`)} className="flex items-center gap-2 px-4 py-2 bg-green-700 text-white rounded-lg hover:bg-green-600 transition">
          <Download size={16} /> Export CSV
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-800/50 p-1 rounded-lg">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${activeTab === tab.key ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'}`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input type="text" placeholder={`Search ${activeTab}...`} value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500" />
      </div>

      {/* Error */}
      {error && <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">{error}</div>}

      {/* Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700">
        {renderTable()}
      </div>

      {/* Form Modal */}
      {renderForm()}

      {/* Preview Modal */}
      {renderPreview()}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setDeleteConfirm(null)}>
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 space-y-4 border border-gray-700" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-gray-100">Confirm Delete</h3>
            <p className="text-gray-400">Are you sure you want to delete &quot;{deleteConfirm.name}&quot;? This action cannot be undone.</p>
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

export default ExportTemplateManagement;
