import React, { useState, useEffect, useCallback } from "react";

interface Dashboard {
  id: string;
  name: string;
  description: string;
  category: string;
  isPublic: boolean;
  createdAt: string;
}

interface DashboardForm {
  name: string;
  description: string;
  category: string;
  isPublic: boolean;
}

const EMPTY_FORM: DashboardForm = {
  name: "",
  description: "",
  category: "",
  isPublic: false,
};

const PAGE_SIZE = 10;

const AnalyticsCRUD: React.FC = () => {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [form, setForm] = useState<DashboardForm>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(PAGE_SIZE),
        ...(search && { search }),
        ...(categoryFilter && { category: categoryFilter }),
      });
      const res = await fetch(`/api/dashboards?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDashboards(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch dashboards");
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryFilter]);

  useEffect(() => {
    fetchDashboards();
  }, [fetchDashboards]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `/api/dashboards/${editingId}` : "/api/dashboards";
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm(EMPTY_FORM);
      setEditingId(null);
      setShowForm(false);
      fetchDashboards();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const handleEdit = (d: Dashboard) => {
    setForm({
      name: d.name,
      description: d.description,
      category: d.category,
      isPublic: d.isPublic,
    });
    setEditingId(d.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetch(`/api/dashboards/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchDashboards();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Analytics Dashboards</h1>

      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>
      )}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          placeholder="Search dashboards..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1"
        />
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="">All Categories</option>
          <option value="sales">Sales</option>
          <option value="marketing">Marketing</option>
          <option value="operations">Operations</option>
          <option value="finance">Finance</option>
        </select>
        <button
          onClick={() => { setForm(EMPTY_FORM); setEditingId(null); setShowForm(true); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Dashboard
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">
            {editingId ? "Edit Dashboard" : "Create Dashboard"}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="border rounded px-3 py-2"
            />
            <input
              type="text"
              placeholder="Category"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              required
              className="border rounded px-3 py-2"
            />
            <textarea
              placeholder="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="border rounded px-3 py-2 col-span-2"
              rows={3}
            />
            <label className="flex items-center gap-2 col-span-2">
              <input
                type="checkbox"
                checked={form.isPublic}
                onChange={(e) => setForm({ ...form, isPublic: e.target.checked })}
              />
              Public dashboard
            </label>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? "Update" : "Create"}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setForm(EMPTY_FORM); setEditingId(null); }}
              className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Dashboard List */}
      <div className="bg-white border rounded shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Category</th>
              <th className="text-left px-4 py-3">Description</th>
              <th className="text-left px-4 py-3">Visibility</th>
              <th className="text-left px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-8">Loading...</td></tr>
            ) : dashboards.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-8 text-gray-500">No dashboards found</td></tr>
            ) : (
              dashboards.map((d) => (
                <tr key={d.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{d.name}</td>
                  <td className="px-4 py-3 capitalize">{d.category}</td>
                  <td className="px-4 py-3 text-gray-600">{d.description}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${d.isPublic ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700"}`}>
                      {d.isPublic ? "Public" : "Private"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleEdit(d)}
                      className="text-blue-600 hover:underline mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(d.id)}
                      className="text-red-600 hover:underline"
                    >
                      Delete
                    </button>
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
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Prev
          </button>
          <span className="px-3 py-1">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to delete this dashboard? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(showDeleteConfirm)}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsCRUD;
