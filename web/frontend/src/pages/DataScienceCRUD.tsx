import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { api } from '../api/client';
import type { DataScienceModel, DataScienceModelInput } from '../api/client';

type Model = DataScienceModel;
type ModelFormData = DataScienceModelInput;

const EMPTY_FORM: ModelFormData = { name: "", type: "classification", version: "1.0.0", status: "training", accuracy: 0 };
const PAGE_SIZE = 10;

const DataScienceCRUD: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [formData, setFormData] = useState<ModelFormData>(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { sortedData: sortedModels, requestSort, getSortIndicator } = useSort(models);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDataScienceModels({
        page, limit: PAGE_SIZE,
        ...(search && { search }),
        ...(statusFilter !== "all" && { status: statusFilter }),
      });
      setModels(data.models || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch models");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => { fetchModels(); }, [fetchModels]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const openCreate = () => { setEditingModel(null); setFormData(EMPTY_FORM); setShowForm(true); };
  const openEdit = (m: Model) => {
    setEditingModel(m);
    setFormData({ name: m.name, type: m.type, version: m.version, status: m.status, accuracy: m.accuracy });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (editingModel) {
        await api.updateDataScienceModel(editingModel.id, formData);
      } else {
        await api.createDataScienceModel(formData);
      }
      setShowForm(false);
      setEditingModel(null);
      setFormData(EMPTY_FORM);
      fetchModels();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await api.deleteDataScienceModel(id);
      setDeleteConfirm(null);
      fetchModels();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const statusColor = (s: string) =>
    s === "active" ? "bg-green-900/50 text-green-200" : s === "training" ? "bg-yellow-900/50 text-yellow-200" : "bg-gray-700 text-gray-100";

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreate, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(models as unknown as Record<string, unknown>[], "datascience_export.csv"), onDelete: () => { if (models.length > 0) setDeleteConfirm(models[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Data Science Models</h1>
        <button onClick={openCreate} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"> title="Ctrl+N"+ New Model</button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-900/50 border border-red-700 text-red-200 rounded-lg">{error}</div>}

      <div className="flex gap-4 mb-4">
        <input type="text" placeholder="Search models..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="flex-1 px-3 py-2 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"  ref={searchRef}/>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="px-3 py-2 border border-gray-700 rounded-lg">
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="training">Training</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {showForm && (
        <div className="mb-6 p-6 bg-gray-800 border border-gray-700 rounded-lg shadow-sm">
          <h2 className="text-lg font-semibold mb-4">{editingModel ? "Edit Model" : "Create New Model"}</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
              <input type="text" required value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-gray-700 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
              <select value={formData.type} onChange={(e) => setFormData({ ...formData, type: e.target.value })} className="w-full px-3 py-2 border border-gray-700 rounded-lg">
                <option value="classification">Classification</option>
                <option value="regression">Regression</option>
                <option value="clustering">Clustering</option>
                <option value="nlp">NLP</option>
                <option value="vision">Computer Vision</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Version</label>
              <input type="text" required value={formData.version} onChange={(e) => setFormData({ ...formData, version: e.target.value })} className="w-full px-3 py-2 border border-gray-700 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
              <select value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value as ModelFormData["status"] })} className="w-full px-3 py-2 border border-gray-700 rounded-lg">
                <option value="training">Training</option>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Accuracy (0-1)</label>
              <input type="number" step="0.01" min="0" max="1" value={formData.accuracy} onChange={(e) => setFormData({ ...formData, accuracy: parseFloat(e.target.value) || 0 })} className="w-full px-3 py-2 border border-gray-700 rounded-lg" />
            </div>
            <div className="flex items-end gap-2">
              <button type="submit" disabled={submitting} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">{submitting ? "Saving..." : editingModel ? "Update" : "Create"}</button>
              <button type="button" onClick={() => { setShowForm(false); setEditingModel(null); setFormData(EMPTY_FORM); }} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600"> title="Escape to close" Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase cursor-pointer select-none" onClick={() => requestSort('type')}>Type{getSortIndicator('type')}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase cursor-pointer select-none" onClick={() => requestSort('version')}>Version{getSortIndicator('version')}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase cursor-pointer select-none" onClick={() => requestSort('accuracy')}>Accuracy{getSortIndicator('accuracy')}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedModels.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No models found</td></tr>
            ) : (
              sortedModels.map((model) => (
                <tr key={model.id} className="hover:bg-gray-800">
                  <td className="px-4 py-3 text-sm text-gray-100">{model.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{model.type}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{model.version}</td>
                  <td className="px-4 py-3"><span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusColor(model.status)}`}>{model.status}</span></td>
                  <td className="px-4 py-3 text-sm text-gray-400">{(model.accuracy * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(model)} className="px-3 py-1 text-sm bg-blue-900/50 text-blue-200 rounded hover:bg-blue-900/50">Edit</button>
                      <button onClick={() => setDeleteConfirm(model.id)} className="px-3 py-1 text-sm bg-red-900/50 text-red-200 rounded hover:bg-red-900/50"> title="Delete key to delete" Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-gray-400">Page {page} of {totalPages} ({total} total)</p>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 hover:bg-gray-800">Previous</button>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 hover:bg-gray-800">Next</button>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-100 mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this model? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600"> title="Escape to close" Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataScienceCRUD;
