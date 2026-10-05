import React, { useState, useEffect, useCallback } from 'react';

interface Integration {
  id: number;
  name: string;
  type: string;
  description: string;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ApiKey {
  id: number;
  name: string;
  integration_id: number;
  scopes: string[];
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

interface Webhook {
  id: number;
  integration_id: number;
  url: string;
  events: string[];
  secret: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface SyncJob {
  id: number;
  integration_id: number;
  job_type: string;
  config: Record<string, unknown>;
  status: string;
  started_at: string;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
}

const IntegrationManagement: React.FC = () => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [syncJobs, setSyncJobs] = useState<SyncJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'integrations' | 'api-keys' | 'webhooks' | 'sync-jobs'>('integrations');
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<Integration | ApiKey | Webhook | SyncJob | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; type: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [integrationsRes, apiKeysRes, webhooksRes, syncJobsRes] = await Promise.all([
        fetch('/api/integrations/', { headers: { 'X-API-Key': 'test-api-key-12345' } }),
        fetch('/api/integrations/api-keys/', { headers: { 'X-API-Key': 'test-api-key-12345' } }),
        fetch('/api/integrations/webhooks/', { headers: { 'X-API-Key': 'test-api-key-12345' } }),
        fetch('/api/integrations/sync-jobs/', { headers: { 'X-API-Key': 'test-api-key-12345' } }),
      ]);
      if (!integrationsRes.ok) throw new Error(`Integrations: HTTP ${integrationsRes.status}`);
      if (!apiKeysRes.ok) throw new Error(`API Keys: HTTP ${apiKeysRes.status}`);
      if (!webhooksRes.ok) throw new Error(`Webhooks: HTTP ${webhooksRes.status}`);
      if (!syncJobsRes.ok) throw new Error(`Sync Jobs: HTTP ${syncJobsRes.status}`);
      setIntegrations(await integrationsRes.json());
      setApiKeys(await apiKeysRes.json());
      setWebhooks(await webhooksRes.json());
      setSyncJobs(await syncJobsRes.json());
    } catch (e: any) {
      setError(e.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setSaving(true);
    setError(null);
    try {
      const endpoint = deleteConfirm.type === 'integration' ? `/api/integrations/${deleteConfirm.id}/`
        : deleteConfirm.type === 'api-key' ? `/api/integrations/api-keys/${deleteConfirm.id}/`
        : deleteConfirm.type === 'webhook' ? `/api/integrations/webhooks/${deleteConfirm.id}/`
        : `/api/integrations/sync-jobs/${deleteConfirm.id}/`;
      const res = await fetch(endpoint, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      await fetchAll();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setSaving(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': case 'active': return 'text-emerald-400';
      case 'running': case 'pending': return 'text-amber-400';
      case 'failed': case 'inactive': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'completed': case 'active': return 'bg-emerald-400/10';
      case 'running': case 'pending': return 'bg-amber-400/10';
      case 'failed': case 'inactive': return 'bg-red-400/10';
      default: return 'bg-gray-400/10';
    }
  };

  const inputClass = 'w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';
  const btnPrimary = 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';
  const btnSecondary = 'bg-gray-700 hover:bg-gray-600 text-gray-100 px-4 py-2 rounded font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';
  const btnDanger = 'bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';

  const tabs = [
    { key: 'integrations' as const, label: 'Integrations', count: integrations.length },
    { key: 'api-keys' as const, label: 'API Keys', count: apiKeys.length },
    { key: 'webhooks' as const, label: 'Webhooks', count: webhooks.length },
    { key: 'sync-jobs' as const, label: 'Sync Jobs', count: syncJobs.length },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-gray-100 p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading integrations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Integration Management</h1>
          <button onClick={() => { setEditingItem(null); setFormData({}); setShowForm(true); }} className={btnPrimary}>
            + New {activeTab === 'integrations' ? 'Integration' : activeTab === 'api-keys' ? 'API Key' : activeTab === 'webhooks' ? 'Webhook' : 'Sync Job'}
          </button>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-4" role="alert">
            {error}
            <button onClick={() => setError(null)} className="float-right font-bold" aria-label="Dismiss error">&times;</button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-700 pb-2">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-t font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-gray-800 text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab.label} <span className="ml-1 text-xs bg-gray-700 px-2 py-0.5 rounded-full">{tab.count}</span>
            </button>
          ))}
        </div>

        {/* Integrations Tab */}
        {activeTab === 'integrations' && (
          <div className="grid gap-4">
            {integrations.map(item => (
              <div key={item.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{item.name}</h3>
                    <p className="text-sm text-gray-400">{item.description}</p>
                    <div className="flex gap-2 mt-2">
                      <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded">{item.type}</span>
                      <span className={`text-xs px-2 py-1 rounded ${getStatusBg(item.is_active ? 'active' : 'inactive')} ${getStatusColor(item.is_active ? 'active' : 'inactive')}`}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setEditingItem(item); setFormData(item); setShowForm(true); }} className={btnSecondary}>Edit</button>
                    <button onClick={() => setDeleteConfirm({ id: item.id, type: 'integration' })} className={btnDanger}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
            {integrations.length === 0 && <p className="text-gray-500 text-center py-8">No integrations configured</p>}
          </div>
        )}

        {/* API Keys Tab */}
        {activeTab === 'api-keys' && (
          <div className="grid gap-4">
            {apiKeys.map(item => (
              <div key={item.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{item.name}</h3>
                    <p className="text-sm text-gray-400 font-mono">{item.key_prefix}...</p>
                    <div className="flex gap-2 mt-2">
                      {item.scopes.map(s => (
                        <span key={s} className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded">{s}</span>
                      ))}
                      <span className={`text-xs px-2 py-1 rounded ${getStatusBg(item.is_active ? 'active' : 'inactive')} ${getStatusColor(item.is_active ? 'active' : 'inactive')}`}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setEditingItem(item); setFormData(item); setShowForm(true); }} className={btnSecondary}>Edit</button>
                    <button onClick={() => setDeleteConfirm({ id: item.id, type: 'api-key' })} className={btnDanger}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
            {apiKeys.length === 0 && <p className="text-gray-500 text-center py-8">No API keys configured</p>}
          </div>
        )}

        {/* Webhooks Tab */}
        {activeTab === 'webhooks' && (
          <div className="grid gap-4">
            {webhooks.map(item => (
              <div key={item.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold font-mono text-sm">{item.url}</h3>
                    <div className="flex gap-2 mt-2">
                      {item.events.map(e => (
                        <span key={e} className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-1 rounded">{e}</span>
                      ))}
                      <span className={`text-xs px-2 py-1 rounded ${getStatusBg(item.is_active ? 'active' : 'inactive')} ${getStatusColor(item.is_active ? 'active' : 'inactive')}`}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setEditingItem(item); setFormData(item); setShowForm(true); }} className={btnSecondary}>Edit</button>
                    <button onClick={() => setDeleteConfirm({ id: item.id, type: 'webhook' })} className={btnDanger}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
            {webhooks.length === 0 && <p className="text-gray-500 text-center py-8">No webhooks configured</p>}
          </div>
        )}

        {/* Sync Jobs Tab */}
        {activeTab === 'sync-jobs' && (
          <div className="grid gap-4">
            {syncJobs.map(item => (
              <div key={item.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Job #{item.id} — {item.job_type}</h3>
                    <p className="text-sm text-gray-400">Integration: {item.integration_id}</p>
                    <div className="flex gap-2 mt-2">
                      <span className={`text-xs px-2 py-1 rounded ${getStatusBg(item.status)} ${getStatusColor(item.status)}`}>
                        {item.status}
                      </span>
                      {item.error_message && (
                        <span className="text-xs bg-red-500/20 text-red-300 px-2 py-1 rounded">{item.error_message}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setEditingItem(item); setFormData(item); setShowForm(true); }} className={btnSecondary}>Edit</button>
                    <button onClick={() => setDeleteConfirm({ id: item.id, type: 'sync-job' })} className={btnDanger}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
            {syncJobs.length === 0 && <p className="text-gray-500 text-center py-8">No sync jobs found</p>}
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4">
              <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
              <p className="text-gray-400 mb-4">Are you sure you want to delete this {deleteConfirm.type}? This action cannot be undone.</p>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setDeleteConfirm(null)} className={btnSecondary}>Cancel</button>
                <button onClick={handleDelete} className={btnDanger} disabled={saving}>
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

export default IntegrationManagement;
