import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { api } from '../api/client';

interface Dataset {
  id: string;
  name: string;
  description: string;
  size: number;
  format: string;
  createdAt: string;
}

const PAGE_SIZE = 10;

const FALLBACK_DATASETS: Dataset[] = [
  { id: "1", name: "transactions", description: "All transaction records", size: 2576980377, format: "parquet", createdAt: "2026-10-01" },
  { id: "2", name: "user_events", description: "User behavior events", size: 956301312, format: "json", createdAt: "2026-10-01" },
  { id: "3", name: "product_catalog", description: "Product information", size: 12884901888, format: "csv", createdAt: "2026-10-01" },
];

const BigDataCRUD: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>(FALLBACK_DATASETS);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(FALLBACK_DATASETS.length);
  const [search, setSearch] = useState("");
  const [formatFilter, setFormatFilter] = useState("");
  const [editing, setEditing] = useState<Dataset | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Dataset | null>(null);
  const [form, setForm] = useState({ name: "", description: "", size: 0, format: "csv" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { sortedData: sortedDatasets, requestSort, getSortIndicator } = useSort(datasets);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getBigDataDatasets({
        page, limit: PAGE_SIZE,
        ...(search && { search }),
        ...(formatFilter && { format: formatFilter }),
      });
      const items = data.items || [];
      if (items.length > 0) {
        setDatasets(items);
        setTotal(items.length);
      } else {
        setDatasets(FALLBACK_DATASETS);
        setTotal(FALLBACK_DATASETS.length);
      }
    } catch (e: any) {
      setDatasets(FALLBACK_DATASETS);
      setTotal(FALLBACK_DATASETS.length);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [page, search, formatFilter]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const resetForm = () => {
    setForm({ name: "", description: "", size: 0, format: "csv" });
    setEditing(null);
    setShowForm(false);
  };

  const openCreate = () => { resetForm(); setShowForm(true); };
  const openEdit = (ds: Dataset) => {
    setForm({ name: ds.name, description: ds.description, size: ds.size, format: ds.format });
    setEditing(ds);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (editing) {
        await api.updateBigDataDataset(editing.id, form);
      } else {
        await api.createBigDataDataset(form);
      }
      resetForm();
      fetchDatasets();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    setError("");
    try {
      await api.deleteBigDataDataset(confirmDelete.id);
      setConfirmDelete(null);
      fetchDatasets();
    } catch (e: any) { setError(e.message); }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreate, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(datasets as unknown as Record<string, unknown>[], "bigdata_export.csv"), onDelete: () => { if (datasets.length > 0) setConfirmDelete(datasets[0]); }, onClose: resetForm });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">BigData Datasets</h1>
      {error && <div className="bg-red-900/50 text-red-200 p-3 rounded mb-4">{error}</div>}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input type="text" placeholder="Search datasets..." value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1"  ref={searchRef}/>
        <select value={formatFilter}
          onChange={(e) => { setFormatFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2">
          <option value="">All Formats</option>
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
          <option value="parquet">Parquet</option>
        </select>
        <button onClick={openCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          + New Dataset
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">{editing ? "Edit Dataset" : "Create Dataset"}</h2>
          <div className="grid grid-cols-2 gap-3">
            <input required placeholder="Name" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="border rounded px-3 py-2" />
            <select value={form.format}
              onChange={(e) => setForm({ ...form, format: e.target.value })}
              className="border rounded px-3 py-2">
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
              <option value="parquet">Parquet</option>
            </select>
            <input type="number" placeholder="Size (bytes)" value={form.size}
              onChange={(e) => setForm({ ...form, size: Number(e.target.value) })}
              className="border rounded px-3 py-2" />
            <input placeholder="Description" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="border rounded px-3 py-2" />
          </div>
          <div className="flex gap-2 mt-3">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editing ? "Update" : "Create"}
            </button>
            <button type="button" onClick={resetForm}
              className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600" title="Escape to close">Cancel</button>
          </div>
        </form>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded p-6 shadow-lg max-w-sm">
            <p className="mb-4">Delete dataset &quot;{confirmDelete.name}&quot;? This cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmDelete(null)} className="bg-gray-700 px-4 py-2 rounded" title="Escape to close">Cancel</button>
              <button onClick={handleDelete}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Dataset List */}
      <div className="bg-gray-800 border border-gray-700 rounded shadow overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-3 cursor-pointer select-none" onClick={() => requestSort('format')}>Format{getSortIndicator('format')}</th>
              <th className="px-4 py-3 cursor-pointer select-none" onClick={() => requestSort('size')}>Size{getSortIndicator('size')}</th>
              <th className="px-4 py-3 cursor-pointer select-none" onClick={() => requestSort('createdAt')}>Created{getSortIndicator('createdAt')}</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : sortedDatasets.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No datasets found</td></tr>
            ) : (
              sortedDatasets.map((ds) => (
                <tr key={ds.id} className="border-t hover:bg-gray-800">
                  <td className="px-4 py-3">
                    <div className="font-medium">{ds.name}</div>
                    {ds.description && <div className="text-sm text-gray-400">{ds.description}</div>}
                  </td>
                  <td className="px-4 py-3 uppercase text-sm">{ds.format}</td>
                  <td className="px-4 py-3 text-sm">{(ds.size / 1024 / 1024).toFixed(2)} MB</td>
                  <td className="px-4 py-3 text-sm">{new Date(ds.createdAt).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(ds)} className="text-blue-600 hover:underline mr-3 text-sm">Edit</button>
                    <button onClick={() => setConfirmDelete(ds)} className="text-red-600 hover:underline text-sm" title="Delete key to delete">Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-4">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
          <span className="text-sm">Page {page} of {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
        </div>
      )}
    </div>
  );
};

export default BigDataCRUD;
