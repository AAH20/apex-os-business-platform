import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from '../hooks/useKeyboardShortcuts';
import { api } from '../api/client';
import type { Campaign, CampaignInput } from '../api/client';
import { FALLBACK_CAMPAIGNS } from '../api/fallback';
import { NoticeStrip } from '../components/NoticeStrip';
import { useFallbackNotice } from '../hooks/useFallbackNotice';



const PAGE_SIZE = 10;
const emptyForm: CampaignInput = { name: '', type: 'email', status: 'draft', startDate: '', endDate: '', budget: 0, spent: 0 };

const CampaignsCRUD: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState<CampaignInput>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notice, noteFailure, noteSuccess, requestRetry, dismissNotice } = useFallbackNotice();
  const { sortedData: sortedCampaigns, requestSort, getSortIndicator } = useSort(campaigns);

  const fetchCampaigns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCampaigns() as any;
      const items: Campaign[] = Array.isArray(data) ? data : (data.items || data.data || []);
      const filtered = search
        ? items.filter((c: Campaign) => c.name.toLowerCase().includes(search.toLowerCase()) || c.type?.toLowerCase().includes(search.toLowerCase()) || c.status?.toLowerCase().includes(search.toLowerCase()))
        : items;
      if (filtered.length > 0) {
        setTotal(filtered.length);
        const start = (page - 1) * PAGE_SIZE;
        setCampaigns(filtered.slice(start, start + PAGE_SIZE));
        noteSuccess();
      } else {
        setTotal(FALLBACK_CAMPAIGNS.length);
        setCampaigns(FALLBACK_CAMPAIGNS);
      }
    } catch (e: any) {
      // Fallback to synthetic data when API is unreachable
      const fallback = FALLBACK_CAMPAIGNS as unknown as Campaign[];
      const filtered = search
        ? fallback.filter(c => c.name.toLowerCase().includes(search.toLowerCase()) || c.type?.toLowerCase().includes(search.toLowerCase()) || c.status?.toLowerCase().includes(search.toLowerCase()))
        : fallback;
      setTotal(filtered.length);
      const start = (page - 1) * PAGE_SIZE;
      setCampaigns(filtered.slice(start, start + PAGE_SIZE));
      noteFailure(e);
    } finally {
      setLoading(false);
    }
  }, [page, search, noteFailure, noteSuccess]);

  useEffect(() => { fetchCampaigns(); }, [fetchCampaigns]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        await api.updateCampaign(editingId, formData);
      } else {
        await api.createCampaign(formData);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForm);
      fetchCampaigns();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (campaign: Campaign) => {
    setFormData({ name: campaign.name, type: campaign.type, status: campaign.status, startDate: campaign.startDate, endDate: campaign.endDate, budget: campaign.budget, spent: campaign.spent });
    setEditingId(campaign.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    setDeleting(true);
    try {
      await api.deleteCampaign(id);
      setShowDeleteConfirm(null);
      fetchCampaigns();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(campaigns as unknown as Record<string, unknown>[], 'campaigns_export.csv'), onDelete: () => { if (campaigns.length > 0) setShowDeleteConfirm(campaigns[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Campaigns Management</h1>

      {notice && (
        <NoticeStrip message={notice} onRetry={() => { requestRetry(); fetchCampaigns(); }} onDismiss={dismissNotice} />
      )}

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search campaigns..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px] text-gray-100 placeholder-gray-500"
          ref={searchRef}
        />
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Campaign
        </button>
        <button
          onClick={() => { requestRetry(); fetchCampaigns(); }}
          title="Reload campaigns from the API"
          className="bg-gray-700 text-gray-100 px-4 py-2 rounded hover:bg-gray-600"
        >
          Refresh
        </button>
        <button
          onClick={() => exportToCSV(campaigns as unknown as Record<string, unknown>[], 'campaigns_export.csv')}
          className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Export CSV
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Campaign' : 'Create New Campaign'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input
                required
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Type</label>
              <select
                value={formData.type}
                onChange={e => setFormData({ ...formData, type: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              >
                <option value="email">Email</option>
                <option value="social">Social</option>
                <option value="ppc">PPC</option>
                <option value="display">Display</option>
                <option value="content">Content</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select
                value={formData.status}
                onChange={e => setFormData({ ...formData, status: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="completed">Completed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Start Date</label>
              <input
                type="date"
                value={formData.startDate}
                onChange={e => setFormData({ ...formData, startDate: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">End Date</label>
              <input
                type="date"
                value={formData.endDate}
                onChange={e => setFormData({ ...formData, endDate: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Budget ($)</label>
              <input
                type="number"
                value={formData.budget}
                onChange={e => setFormData({ ...formData, budget: parseFloat(e.target.value) || 0 })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Spent ($)</label>
              <input
                type="number"
                value={formData.spent}
                onChange={e => setFormData({ ...formData, spent: parseFloat(e.target.value) || 0 })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
              {saving ? 'Saving...' : editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); setFormData(emptyForm); }} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">
              Cancel
            </button>
          </div>
        </form>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this campaign? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} disabled={deleting} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} disabled={deleting} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50">
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden shadow">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('type')}>Type{getSortIndicator('type')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('budget')}>Budget{getSortIndicator('budget')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Spent</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedCampaigns.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No campaigns found</td></tr>
            ) : sortedCampaigns.map(campaign => (
              <tr key={campaign.id} className="border-t border-gray-700 hover:bg-gray-600">
                <td className="px-4 py-3">{campaign.id}</td>
                <td className="px-4 py-3 font-medium">{campaign.name}</td>
                <td className="px-4 py-3 capitalize">{campaign.type}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    campaign.status === 'active' ? 'bg-green-900/50 text-green-300' :
                    campaign.status === 'completed' ? 'bg-blue-900/50 text-blue-300' :
                    campaign.status === 'paused' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-gray-700 text-gray-300'
                  }`}>{campaign.status}</span>
                </td>
                <td className="px-4 py-3">${(campaign.budget ?? 0).toLocaleString()}</td>
                <td className="px-4 py-3">${(campaign.spent ?? 0).toLocaleString()}</td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(campaign)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(campaign.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
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
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border border-gray-600 rounded disabled:opacity-50 hover:bg-gray-700 text-gray-300">Previous</button>
            <span className="px-3 py-1 text-gray-400">{page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 border border-gray-600 rounded disabled:opacity-50 hover:bg-gray-700 text-gray-300">Next</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CampaignsCRUD;
