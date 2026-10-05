import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { api } from '../api/client';
import type { ContinuousBIReport, ContinuousBIReportInput } from '../api/client';

type Report = ContinuousBIReport;
type ReportFormData = ContinuousBIReportInput;

const PAGE_SIZE = 10;

const emptyForm: ReportFormData = {
  name: '',
  description: '',
  report_type: 'dashboard',
  owner: 'system',
  is_active: true,
};

const REPORT_TYPES = ['dashboard', 'chart', 'table', 'funnel', 'pivot', 'kpi'];

const FALLBACK_REPORTS: Report[] = [
  { id: 1, name: 'Executive Summary', description: 'High-level KPIs', report_type: 'dashboard', owner: 'system', is_active: true, updated_at: '2026-10-01' },
  { id: 2, name: 'Sales Performance', description: 'Sales metrics', report_type: 'chart', owner: 'system', is_active: true, updated_at: '2026-10-01' },
  { id: 3, name: 'Marketing Analytics', description: 'Campaign data', report_type: 'table', owner: 'system', is_active: true, updated_at: '2026-10-01' },
  { id: 4, name: 'Operations Monitor', description: 'Ops dashboard', report_type: 'kpi', owner: 'system', is_active: false, updated_at: '2026-10-01' },
];

const ContinuousBICRUD: React.FC = () => {
  const [reports, setReports] = useState<Report[]>(FALLBACK_REPORTS);
  const [total, setTotal] = useState(FALLBACK_REPORTS.length);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [formData, setFormData] = useState<ReportFormData>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sortedData: sortedReports, requestSort, getSortIndicator } = useSort(reports);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getContinuousBIReports({
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        ...(typeFilter !== 'all' && { report_type: typeFilter }),
        ...(search && { search }),
      });
      const items = Array.isArray(data) ? data : [];
      if (items.length > 0) {
        setReports(items);
        setTotal(items.length);
      } else {
        setReports(FALLBACK_REPORTS);
        setTotal(FALLBACK_REPORTS.length);
      }
    } catch (e: any) {
      setReports(FALLBACK_REPORTS);
      setTotal(FALLBACK_REPORTS.length);
      setError(e.message || 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter, search]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (editingId) {
        await api.updateContinuousBIReport(editingId, formData);
      } else {
        await api.createContinuousBIReport(formData);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForm);
      fetchReports();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (report: Report) => {
    setFormData({
      name: report.name,
      description: report.description || '',
      report_type: report.report_type,
      owner: report.owner,
      is_active: report.is_active,
    });
    setEditingId(report.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      await api.deleteContinuousBIReport(id);
      setShowDeleteConfirm(null);
      fetchReports();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(reports as unknown as Record<string, unknown>[], "continuousbi_export.csv"), onDelete: () => { if (reports.length > 0) setShowDeleteConfirm(reports[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">ContinuousBI Reports</h1>
      {error && <div className="bg-red-900/50 text-red-200 p-3 rounded mb-4">{error}</div>}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          placeholder="Search reports..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1"
         ref={searchRef}/>
        <select
          value={typeFilter}
          onChange={e => { setTypeFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="all">All Types</option>
          {REPORT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
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
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">{editingId ? 'Edit Report' : 'Create Report'}</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="Name"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <select
              value={formData.report_type}
              onChange={e => setFormData({ ...formData, report_type: e.target.value })}
              className="border rounded px-3 py-2"
            >
              {REPORT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <input
              placeholder="Owner"
              value={formData.owner}
              onChange={e => setFormData({ ...formData, owner: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <label className="flex items-center gap-2 border rounded px-3 py-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={e => setFormData({ ...formData, is_active: e.target.checked })}
              />
              Active
            </label>
            <textarea
              placeholder="Description"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              className="border rounded px-3 py-2 col-span-2"
              rows={2}
            />
          </div>
          <div className="flex gap-2 mt-3">
            <button
              type="submit"
              disabled={submitting}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : editingId ? 'Update' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setEditingId(null); }}
              className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600"
            title="Escape to close">Cancel
            </button>
          </div>
        </form>
      )}

      {/* Reports Table */}
      <div className="bg-gray-800 border border-gray-700 rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('report_type')}>Type{getSortIndicator('report_type')}</th>
              <th className="px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('owner')}>Owner{getSortIndicator('owner')}</th>
              <th className="px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('is_active')}>Status{getSortIndicator('is_active')}</th>
              <th className="px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('updated_at')}>Updated{getSortIndicator('updated_at')}</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedReports.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No reports found</td></tr>
            ) : (
              sortedReports.map(r => (
                <tr key={r.id} className="border-t hover:bg-gray-800">
                  <td className="px-4 py-2 font-medium">{r.name}</td>
                  <td className="px-4 py-2">
                    <span className="px-2 py-1 rounded text-xs font-medium bg-blue-900/50 text-blue-200">
                      {r.report_type}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-400">{r.owner}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${r.is_active ? 'bg-green-900/50 text-green-200' : 'bg-gray-700 text-gray-400'}`}>
                      {r.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-400">
                    {new Date(r.updated_at ?? '').toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleEdit(r)} className="text-blue-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(r.id)} className="text-red-600 hover:underline" title="Delete key to delete">Delete</button>
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
          <div className="bg-gray-800 border border-gray-700 rounded p-6 shadow-lg max-w-sm w-full">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this report? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600" title="Escape to close">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContinuousBICRUD;
