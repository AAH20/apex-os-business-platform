import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Project {
  id: number;
  name: string;
  description: string;
  status: "active" | "inactive" | "completed";
  createdAt: string;
}

interface ProjectFormData {
  name: string;
  description: string;
  status: "active" | "inactive" | "completed";
}

const API_BASE = "/api/projects";
const PAGE_SIZE = 10;

const emptyForm: ProjectFormData = { name: "", description: "", status: "active" };

const ProjectCRUD: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [formData, setFormData] = useState<ProjectFormData>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sortedData: sortedProjects, requestSort, getSortIndicator } = useSort(projects);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(PAGE_SIZE),
        ...(search && { search }),
        ...(statusFilter !== "all" && { status: statusFilter }),
      });
      const res = await fetch(`${API_BASE}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProjects(data.projects || data.data || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch projects");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setFormData(emptyForm);
      setEditingId(null);
      setShowForm(false);
      fetchProjects();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const handleEdit = (project: Project) => {
    setFormData({
      name: project.name,
      description: project.description,
      status: project.status,
    });
    setEditingId(project.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchProjects();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(projects as unknown as Record<string, unknown>[], "project_export.csv"), onDelete: () => { if (projects.length > 0) setShowDeleteConfirm(projects[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Projects</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1"
         ref={searchRef}/>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="completed">Completed</option>
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        > title="Ctrl+N"
          + New Project
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">
            {editingId ? "Edit Project" : "Create Project"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="border rounded px-3 py-2 w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as ProjectFormData["status"] })}
                className="border rounded px-3 py-2 w-full"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="completed">Completed</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                rows={3}
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? "Update" : "Create"}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setEditingId(null); setFormData(emptyForm); }}
              className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
            > title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {/* Projects Table */}
      <div className="bg-white border rounded shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('description')}>Description{getSortIndicator('description')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 cursor-pointer select-none" onClick={() => requestSort('createdAt')}>Created{getSortIndicator('createdAt')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : sortedProjects.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No projects found</td></tr>
            ) : (
              sortedProjects.map((project) => (
                <tr key={project.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{project.name}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{project.description}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      project.status === "active" ? "bg-green-100 text-green-800" :
                      project.status === "completed" ? "bg-blue-100 text-blue-800" :
                      "bg-gray-100 text-gray-800"
                    }`}>
                      {project.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-sm">
                    {new Date(project.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleEdit(project)}
                      className="text-blue-600 hover:text-blue-800 mr-3 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(project.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    > title="Delete key to delete" Delete
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
        <div className="flex justify-center items-center gap-2 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-100"
          >
            Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages} ({total} total)
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-100"
          >
            Next
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-600 mb-4">
              Are you sure you want to delete this project? This action cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              > title="Escape to close" Cancel
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

export default ProjectCRUD;
