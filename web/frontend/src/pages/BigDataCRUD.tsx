import React, { useState, useEffect, useCallback } from "react";

interface Dataset {
  id: string;
  name: string;
  description: string;
  source: string;
  size: number;
  format: string;
  createdAt: string;
  updatedAt: string;
}

interface DatasetFormData {
  name: string;
  description: string;
  source: string;
  size: number;
  format: string;
}

const EMPTY_FORM: DatasetFormData = {
  name: "",
  description: "",
  source: "",
  size: 0,
  format: "csv",
};

const PAGE_SIZE = 10;

const BigDataCRUD: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [formatFilter, setFormatFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null);
  const [formData, setFormData] = useState<DatasetFormData>(EMPTY_FORM);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(currentPage),
        limit: String(PAGE_SIZE),
      });
      if (searchQuery) params.set("search", searchQuery);
      if (formatFilter) params.set("format", formatFilter);

      const res = await fetch(`/api/datasets?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDatasets(data.items || []);
      setTotalPages(Math.max(1, Math.ceil((data.total || 0) / PAGE_SIZE)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch datasets");
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchQuery, formatFilter]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const openCreateForm = () => {
    setEditingDataset(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  };

  const openEditForm = (dataset: Dataset) => {
    setEditingDataset(dataset);
    setFormData({
      name: dataset.name,
      description: dataset.description,
      source: dataset.source,
      size: dataset.size,
      format: dataset.format,
    });
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingDataset(null);
    setFormData(EMPTY_FORM);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const url = editingDataset
        ? `/api/datasets/${editingDataset.id}`
        : "/api/datasets";
      const method = editingDataset ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      closeForm();
      fetchDatasets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetch(`/api/datasets/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirmId(null);
      fetchDatasets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">BigData Datasets</h1>
        <button
          onClick={openCreateForm}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          + New Dataset
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      <form onSubmit={handleSearch} className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="Search datasets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <select
          value={formatFilter}
          onChange={(e) => {
            setFormatFilter(e.target.value);
            setCurrentPage(1);
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Formats</option>
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
          <option value="parquet">Parquet</option>
          <option value="avro">Avro</option>
        </select>
        <button
          type="submit"
          className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700"
        >
          Search
        </button>
      </form>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-xl font-semibold mb-4">
              {editingDataset ? "Edit Dataset" : "Create Dataset"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Source
                </label>
                <input
                  type="text"
                  required
                  value={formData.source}
                  onChange={(e) =>
                    setFormData({ ...formData, source: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Size (bytes)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={formData.size}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        size: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Format
                  </label>
                  <select
                    value={formData.format}
                    onChange={(e) =>
                      setFormData({ ...formData, format: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                    <option value="parquet">Parquet</option>
                    <option value="avro">Avro</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeForm}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting
                    ? "Saving..."
                    : editingDataset
                      ? "Update"
                      : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading datasets...</div>
      ) : datasets.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No datasets found. Create one to get started.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Name
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Description
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Source
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Size
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Format
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Created
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {datasets.map((ds) => (
                <tr key={ds.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {ds.name}
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                    {ds.description}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{ds.source}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {formatSize(ds.size)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs uppercase">
                      {ds.format}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(ds.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => openEditForm(ds)}
                      className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
                    >
                      Edit
                    </button>
                    {deleteConfirmId === ds.id ? (
                      <>
                        <button
                          onClick={() => handleDelete(ds.id)}
                          className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setDeleteConfirmId(null)}
                          className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirmId(ds.id)}
                        className="px-3 py-1 text-red-600 hover:bg-red-50 rounded"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 hover:bg-gray-50"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default BigDataCRUD;
