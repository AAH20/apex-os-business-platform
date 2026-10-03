import React, { useState, useEffect, useCallback } from "react";

interface Dataset {
  id: string;
  name: string;
  description: string;
  size: number;
  format: string;
  createdAt: string;
}

const API = "/api/bigdata";
const PAGE_SIZE = 10;

const BigDataCRUD: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [formatFilter, setFormatFilter] = useState("");
  const [editing, setEditing] = useState<Dataset | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Dataset | null>(null);
  const [form, setForm] = useState({ name: "", description: "", size: 0, format: "csv" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(PAGE_SIZE),
        ...(search && { search }),
        ...(formatFilter && { format: formatFilter }),
      });
      const res = await fetch(`${API}?${params}`);
      if (!res.ok) throw new Error("Failed to fetch datasets");
      const data = await res.json();
      setDatasets(data.items || []);
      setTotal(data.total || 0);
    } catch (e: any) {
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
      const url = editing ? `${API}/${editing.id}` : API;
      const method = editing ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(editing ? "Update failed" : "Create failed");
      resetForm();
      fetchDatasets();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    setError("");
    try {
      const res = await fetch(`${API}/${confirmDelete.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");
      setConfirmDelete(null);
      fetchDatasets();
    } catch (e: any) { setError(e.message); }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">BigData Datasets</h1>
      {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input type="text" placeholder="Search datasets..." value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1" />
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
        <form onSubmit={handleSubmit} className="bg-white border rounded p-4 mb-4 shadow">
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
              className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400">Cancel</button>
          </div>
        </form>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded p-6 shadow-lg max-w-sm">
            <p className="mb-4">Delete dataset &quot;{confirmDelete.name}&quot;? This cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmDelete(null)} className="bg-gray-300 px-4 py-2 rounded">Cancel</button>
              <button onClick={handleDelete}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Dataset List */}
      <div className="bg-white border rounded shadow overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Format</th>
              <th className="px-4 py-3">Size</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : datasets.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No datasets found</td></tr>
            ) : (
              datasets.map((ds) => (
                <tr key={ds.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{ds.name}</div>
                    {ds.description && <div className="text-sm text-gray-500">{ds.description}</div>}
                  </td>
                  <td className="px-4 py-3 uppercase text-sm">{ds.format}</td>
                  <td className="px-4 py-3 text-sm">{(ds.size / 1024 / 1024).toFixed(2)} MB</td>
                  <td className="px-4 py-3 text-sm">{new Date(ds.createdAt).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(ds)} className="text-blue-600 hover:underline mr-3 text-sm">Edit</button>
                    <button onClick={() => setConfirmDelete(ds)} className="text-red-600 hover:underline text-sm">Delete</button>
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
