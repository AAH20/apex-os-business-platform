import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from '../hooks/useKeyboardShortcuts';
import { api } from '../api/client'
import type { Opportunity, OpportunityInput } from '../api/client';



const PAGE_SIZE = 10;
const emptyForm: OpportunityInput = { name: '', stage: 'prospecting', value: 0, probability: 0, expectedClose: '', owner: '' };

const OpportunitiesCRUD: React.FC = () => {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState<OpportunityInput>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sortedData: sortedOpportunities, requestSort, getSortIndicator } = useSort(opportunities);

  const fetchOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getOpportunities();
      const filtered = search
        ? data.filter(o => o.name.toLowerCase().includes(search.toLowerCase()) || o.stage?.toLowerCase().includes(search.toLowerCase()))
        : data;
      setTotal(filtered.length);
      const start = (page - 1) * PAGE_SIZE;
      setOpportunities(filtered.slice(start, start + PAGE_SIZE));
    } catch (e: any) {
      setError(e.message || 'Failed to fetch opportunities');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchOpportunities(); }, [fetchOpportunities]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        await api.updateOpportunity(editingId, formData);
      } else {
        await api.createOpportunity(formData);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForm);
      fetchOpportunities();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (opportunity: Opportunity) => {
    setFormData({ name: opportunity.name, stage: opportunity.stage, value: opportunity.value, probability: opportunity.probability, expectedClose: opportunity.expectedClose, owner: opportunity.owner });
    setEditingId(opportunity.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    setDeleting(true);
    try {
      await api.deleteOpportunity(id);
      setShowDeleteConfirm(null);
      fetchOpportunities();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(opportunities as unknown as Record<string, unknown>[], 'opportunities_export.csv'), onDelete: () => { if (opportunities.length > 0) setShowDeleteConfirm(opportunities[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Opportunities Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search opportunities..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px] text-gray-100 placeholder-gray-500"
          ref={searchRef}
        />
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Opportunity
        </button>
        <button
          onClick={() => exportToCSV(opportunities as unknown as Record<string, unknown>[], 'opportunities_export.csv')}
          className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Export CSV
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Opportunity' : 'Create New Opportunity'}</h2>
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
              <label className="block text-sm font-medium mb-1 text-gray-300">Stage</label>
              <select
                value={formData.stage}
                onChange={e => setFormData({ ...formData, stage: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              >
                <option value="prospecting">Prospecting</option>
                <option value="qualification">Qualification</option>
                <option value="proposal">Proposal</option>
                <option value="negotiation">Negotiation</option>
                <option value="closed_won">Closed Won</option>
                <option value="closed_lost">Closed Lost</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Value ($)</label>
              <input
                type="number"
                value={formData.value}
                onChange={e => setFormData({ ...formData, value: parseFloat(e.target.value) || 0 })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Probability (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                value={formData.probability}
                onChange={e => setFormData({ ...formData, probability: parseInt(e.target.value) || 0 })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Expected Close</label>
              <input
                type="date"
                value={formData.expectedClose}
                onChange={e => setFormData({ ...formData, expectedClose: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Owner</label>
              <input
                value={formData.owner}
                onChange={e => setFormData({ ...formData, owner: e.target.value })}
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
            <p className="text-gray-400 mb-4">Are you sure you want to delete this opportunity? This action cannot be undone.</p>
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
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('stage')}>Stage{getSortIndicator('stage')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => requestSort('value')}>Value{getSortIndicator('value')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Probability</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Owner</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : sortedOpportunities.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No opportunities found</td></tr>
            ) : sortedOpportunities.map(opportunity => (
              <tr key={opportunity.id} className="border-t border-gray-700 hover:bg-gray-600">
                <td className="px-4 py-3">{opportunity.id}</td>
                <td className="px-4 py-3 font-medium">{opportunity.name}</td>
                <td className="px-4 py-3">
                  <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-blue-900/50 text-blue-300">{opportunity.stage}</span>
                </td>
                <td className="px-4 py-3">${opportunity.value?.toLocaleString() ?? '0'}</td>
                <td className="px-4 py-3">{opportunity.probability}%</td>
                <td className="px-4 py-3 text-gray-400">{opportunity.owner}</td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(opportunity)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(opportunity.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
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

export default OpportunitiesCRUD;
