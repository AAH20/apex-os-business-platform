import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { Monitor, AlertRule, Dashboard, Metric, MonitorInput, AlertRuleInput, DashboardInput, MetricInput } from '../api/client';
import {
  Activity, AlertTriangle, BarChart3, Bell, Cpu, Database,
  Globe, HardDrive, Plus, RefreshCw, Server, Trash2, Edit,
  Eye, Zap, Clock,
} from 'lucide-react';

type Tab = 'monitors' | 'alerts' | 'dashboards' | 'metrics';

const FETCH_TIMEOUT_MS = 10_000;

const MonitoringManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('monitors');
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<{ type: Tab; id: number } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async (tab?: Tab) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    setLoading(true);
    setError(null);
    try {
      if (tab === 'monitors') {
        setMonitors(await api.getMonitors({ signal: controller.signal }));
      } else if (tab === 'alerts') {
        setAlertRules(await api.getAlertRules({ signal: controller.signal }));
      } else if (tab === 'dashboards') {
        setDashboards(await api.getDashboards({ signal: controller.signal }));
      } else {
        setMetrics(await api.getMetrics({ signal: controller.signal }));
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setError(e.message || 'Failed to fetch monitoring data');
      }
    } finally {
      clearTimeout(timer);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(activeTab);
    return () => { abortRef.current?.abort(); };
  }, [activeTab, fetchData]);

  const handleDelete = async (type: Tab, id: number) => {
    setError(null);
    try {
      if (type === 'monitors') await api.deleteMonitor(id);
      else if (type === 'alerts') await api.deleteAlertRule(id);
      else if (type === 'dashboards') await api.deleteDashboard(id);
      else await api.deleteMetric(id);
      setShowDeleteConfirm(null);
      fetchData(activeTab);
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  };

  const handleEdit = (_type: Tab, item: any) => {
    setFormData({ ...item });
    setEditingId(item.id);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (activeTab === 'monitors') {
        if (editingId) await api.updateMonitor(editingId, formData as unknown as MonitorInput);
        else await api.createMonitor(formData as unknown as MonitorInput);
      } else if (activeTab === 'alerts') {
        if (editingId) await api.updateAlertRule(editingId, formData as unknown as AlertRuleInput);
        else await api.createAlertRule(formData as unknown as AlertRuleInput);
      } else if (activeTab === 'dashboards') {
        if (editingId) await api.updateDashboard(editingId, formData as unknown as DashboardInput);
        else await api.createDashboard(formData as unknown as DashboardInput);
      } else {
        if (editingId) await api.updateMetric(editingId, formData as unknown as MetricInput);
        else await api.createMetric(formData as unknown as MetricInput);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData({});
      fetchData(activeTab);
    } catch (e: any) {
      setError(e.message || 'Save failed');
    }
  };

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: 'monitors', label: 'Monitors', icon: Server },
    { key: 'alerts', label: 'Alert Rules', icon: Bell },
    { key: 'dashboards', label: 'Dashboards', icon: BarChart3 },
    { key: 'metrics', label: 'Metrics', icon: Activity },
  ];

  const statusColor = (s: string) =>
    s === 'up' ? 'text-emerald-400 bg-emerald-900/30' :
    s === 'down' ? 'text-red-400 bg-red-900/30' :
    s === 'warning' ? 'text-amber-400 bg-amber-900/30' :
    'text-slate-400 bg-slate-700/30';

  const severityColor = (s: string) =>
    s === 'critical' ? 'text-red-400 bg-red-900/30' :
    s === 'warning' ? 'text-amber-400 bg-amber-900/30' :
    s === 'info' ? 'text-blue-400 bg-blue-900/30' :
    'text-slate-400 bg-slate-700/30';

  const metricIcon = (name: string) => {
    if (name.includes('cpu')) return Cpu;
    if (name.includes('mem')) return Database;
    if (name.includes('disk')) return HardDrive;
    if (name.includes('network')) return Globe;
    if (name.includes('response')) return Clock;
    if (name.includes('error')) return AlertTriangle;
    return Zap;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="text-cyan-400" size={28} />
            Monitoring Management
          </h1>
          <p className="text-gray-400 text-sm mt-1">Manage monitors, alert rules, dashboards, and metrics</p>
        </div>
        <button
          onClick={() => fetchData(activeTab)}
          className="flex items-center gap-2 bg-gray-800 border border-gray-700 px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-800 p-1 rounded-lg">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setActiveTab(key); setShowForm(false); setEditingId(null); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === key
                ? 'bg-cyan-600 text-white shadow-lg'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
            }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">
          {activeTab === 'monitors' && `${monitors.length} monitors`}
          {activeTab === 'alerts' && `${alertRules.length} alert rules`}
          {activeTab === 'dashboards' && `${dashboards.length} dashboards`}
          {activeTab === 'metrics' && `${metrics.length} metrics`}
        </p>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData({}); }}
          className="flex items-center gap-2 bg-cyan-600 text-white px-4 py-2 rounded-lg hover:bg-cyan-700 transition-colors"
        >
          <Plus size={16} /> New {activeTab === 'monitors' ? 'Monitor' : activeTab === 'alerts' ? 'Alert Rule' : activeTab === 'dashboards' ? 'Dashboard' : 'Metric'}
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit' : 'Create'} {activeTab}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeTab === 'monitors' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
                  <input required value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Type</label>
                  <select value={formData.type || 'http'} onChange={e => setFormData({ ...formData, type: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                    <option value="http">HTTP</option><option value="tcp">TCP</option><option value="metric">Metric</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1 text-gray-300">Target *</label>
                  <input required value={formData.target || ''} onChange={e => setFormData({ ...formData, target: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Interval (seconds)</label>
                  <input type="number" value={formData.interval || 60} onChange={e => setFormData({ ...formData, interval: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm text-gray-300">
                    <input type="checkbox" checked={formData.is_active ?? true} onChange={e => setFormData({ ...formData, is_active: e.target.checked })} className="rounded" /> Active
                  </label>
                </div>
              </>
            )}
            {activeTab === 'alerts' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
                  <input required value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Severity</label>
                  <select value={formData.severity || 'warning'} onChange={e => setFormData({ ...formData, severity: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                    <option value="info">Info</option><option value="warning">Warning</option><option value="critical">Critical</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1 text-gray-300">Condition *</label>
                  <input required value={formData.condition || ''} onChange={e => setFormData({ ...formData, condition: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Monitor ID</label>
                  <input type="number" value={formData.monitor_id || ''} onChange={e => setFormData({ ...formData, monitor_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm text-gray-300">
                    <input type="checkbox" checked={formData.is_active ?? true} onChange={e => setFormData({ ...formData, is_active: e.target.checked })} className="rounded" /> Active
                  </label>
                </div>
              </>
            )}
            {activeTab === 'dashboards' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
                  <input required value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Widgets</label>
                  <input type="number" value={formData.widgets || 6} onChange={e => setFormData({ ...formData, widgets: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
                  <input value={formData.description || ''} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Refresh Rate (s)</label>
                  <input type="number" value={formData.refresh_rate || 30} onChange={e => setFormData({ ...formData, refresh_rate: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm text-gray-300">
                    <input type="checkbox" checked={formData.is_active ?? true} onChange={e => setFormData({ ...formData, is_active: e.target.checked })} className="rounded" /> Active
                  </label>
                </div>
              </>
            )}
            {activeTab === 'metrics' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
                  <input required value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Unit</label>
                  <input value={formData.unit || ''} onChange={e => setFormData({ ...formData, unit: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Value</label>
                  <input type="number" step="any" value={formData.value || 0} onChange={e => setFormData({ ...formData, value: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-gray-300">Monitor ID</label>
                  <input type="number" value={formData.monitor_id || ''} onChange={e => setFormData({ ...formData, monitor_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
                </div>
              </>
            )}
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" className="bg-cyan-600 text-white px-4 py-2 rounded hover:bg-cyan-700">
              {editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); setFormData({}); }} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Content */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : (
        <>
          {/* Monitors Tab */}
          {activeTab === 'monitors' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {monitors.map(m => (
                <div key={m.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-cyan-600/50 transition-colors">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Server size={18} className="text-cyan-400" />
                      <h3 className="font-semibold text-sm">{m.name}</h3>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor(m.status)}`}>{m.status}</span>
                  </div>
                  <div className="text-xs text-gray-400 space-y-1">
                    <p>Type: {m.type} | Target: {m.target}</p>
                    <p>Interval: {m.interval}s | Last check: {new Date(m.last_check).toLocaleString()}</p>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handleEdit('monitors', m)} className="text-blue-400 hover:text-blue-300 text-xs flex items-center gap-1"><Edit size={12} /> Edit</button>
                    <button onClick={() => setShowDeleteConfirm({ type: 'monitors', id: m.id })} className="text-red-400 hover:text-red-300 text-xs flex items-center gap-1"><Trash2 size={12} /> Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Alert Rules Tab */}
          {activeTab === 'alerts' && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-750">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Condition</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Severity</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Monitor</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Active</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {alertRules.map(r => (
                    <tr key={r.id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="px-4 py-3 font-medium text-sm">{r.name}</td>
                      <td className="px-4 py-3 text-gray-400 text-sm font-mono">{r.condition}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs font-medium ${severityColor(r.severity)}`}>{r.severity}</span></td>
                      <td className="px-4 py-3 text-gray-400 text-sm">{r.monitor_id || '—'}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs font-medium ${r.is_active ? 'bg-emerald-900/30 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{r.is_active ? 'Yes' : 'No'}</span></td>
                      <td className="px-4 py-3">
                        <button onClick={() => handleEdit('alerts', r)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                        <button onClick={() => setShowDeleteConfirm({ type: 'alerts', id: r.id })} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Dashboards Tab */}
          {activeTab === 'dashboards' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {dashboards.map(d => (
                <div key={d.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-cyan-600/50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <BarChart3 size={18} className="text-purple-400" />
                      <h3 className="font-semibold">{d.name}</h3>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${d.is_active ? 'bg-emerald-900/30 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{d.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">{d.description}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                    <span className="flex items-center gap-1"><Eye size={12} /> {d.widgets} widgets</span>
                    <span className="flex items-center gap-1"><Clock size={12} /> {d.refresh_rate}s refresh</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleEdit('dashboards', d)} className="text-blue-400 hover:text-blue-300 text-xs flex items-center gap-1"><Edit size={12} /> Edit</button>
                    <button onClick={() => setShowDeleteConfirm({ type: 'dashboards', id: d.id })} className="text-red-400 hover:text-red-300 text-xs flex items-center gap-1"><Trash2 size={12} /> Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Metrics Tab */}
          {activeTab === 'metrics' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {metrics.map(m => {
                const Icon = metricIcon(m.name);
                return (
                  <div key={m.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-cyan-600/50 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <Icon size={18} className="text-cyan-400" />
                      <span className="text-xs text-gray-500">#{m.id}</span>
                    </div>
                    <p className="text-xs text-gray-400 mb-1">{m.name}</p>
                    <p className="text-2xl font-bold text-white">{m.value}<span className="text-sm text-gray-400 ml-1">{m.unit}</span></p>
                    <p className="text-xs text-gray-500 mt-1">{new Date(m.timestamp).toLocaleString()}</p>
                    <div className="flex gap-2 mt-3">
                      <button onClick={() => handleEdit('metrics', m)} className="text-blue-400 hover:text-blue-300 text-xs flex items-center gap-1"><Edit size={12} /> Edit</button>
                      <button onClick={() => setShowDeleteConfirm({ type: 'metrics', id: m.id })} className="text-red-400 hover:text-red-300 text-xs flex items-center gap-1"><Trash2 size={12} /> Delete</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-100 mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this item? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm.type, showDeleteConfirm.id)} className="px-4 py-2 text-sm rounded bg-red-600 text-white hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MonitoringManagement;
