import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Task {
  id: string;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "done";
  priority: "low" | "medium" | "high";
  dueDate: string;
}

interface TaskFormData {
  title: string;
  description: string;
  status: Task["status"];
  priority: Task["priority"];
  dueDate: string;
}

const EMPTY_FORM: TaskFormData = {
  title: "",
  description: "",
  status: "todo",
  priority: "medium",
  dueDate: "",
};

const API_BASE = "/api/tasks";

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export default function TaskCRUD() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [formData, setFormData] = useState<TaskFormData>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const { sortedData: sortedTasks, requestSort, getSortIndicator } = useSort(tasks);

  const limit = 10;

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
        search,
        status: filterStatus,
      });
      const data = await apiFetch<{ tasks: Task[]; totalPages: number }>(
        `${API_BASE}?${params}`
      );
      setTasks(data.tasks);
      setTotalPages(data.totalPages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterStatus]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  function openCreate() {
    setFormData(EMPTY_FORM);
    setEditingId(null);
    setShowForm(true);
  }

  function openEdit(task: Task) {
    setFormData({
      title: task.title,
      description: task.description,
      status: task.status,
      priority: task.priority,
      dueDate: task.dueDate,
    });
    setEditingId(task.id);
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (editingId) {
        await apiFetch(`${API_BASE}/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(formData),
        });
      } else {
        await apiFetch(API_BASE, {
          method: "POST",
          body: JSON.stringify(formData),
        });
      }
      setShowForm(false);
      setFormData(EMPTY_FORM);
      setEditingId(null);
      fetchTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function handleDelete(id: string) {
    setError(null);
    try {
      await apiFetch(`${API_BASE}/${id}`, { method: "DELETE" });
      setShowDeleteConfirm(null);
      fetchTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function handleCancel() {
    setShowForm(false);
    setEditingId(null);
    setFormData(EMPTY_FORM);
  }

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreate, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(tasks as unknown as Record<string, unknown>[], "task_export.csv"), onDelete: () => { if (tasks.length > 0) setShowDeleteConfirm(tasks[0].id); }, onClose: handleCancel });

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Task Management</h1>

      {error && (
        <div className="bg-red-900/50 text-red-200 p-3 rounded mb-4">{error}</div>
      )}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          placeholder="Search tasks..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="border border-gray-700 rounded px-3 py-2 flex-1 bg-gray-800 text-gray-100"
         ref={searchRef}/>
        <select
          value={filterStatus}
          onChange={(e) => {
            setFilterStatus(e.target.value);
            setPage(1);
          }}
          className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100"
        >
          <option value="all">All Status</option>
          <option value="todo">To Do</option>
          <option value="in_progress">In Progress</option>
          <option value="done">Done</option>
        </select>
        <button
          onClick={openCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Task
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-gray-800 border border-gray-700 rounded p-4 mb-6 shadow"
        >
          <h2 className="text-lg font-semibold mb-3 text-gray-100">
            {editingId ? "Edit Task" : "Create Task"}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-300 font-medium text-gray-100 mb-1 text-gray-300">Title</label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100 w-full"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-300 font-medium text-gray-100 mb-1 text-gray-300">
                Due Date
              </label>
              <input
                type="date"
                value={formData.dueDate}
                onChange={(e) =>
                  setFormData({ ...formData, dueDate: e.target.value })
                }
                className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100 w-full"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-300 font-medium text-gray-100 mb-1 text-gray-300">Status</label>
              <select
                value={formData.status}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    status: e.target.value as Task["status"],
                  })
                }
                className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100 w-full"
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="done">Done</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-300 font-medium text-gray-100 mb-1 text-gray-300">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    priority: e.target.value as Task["priority"],
                  })
                }
                className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100 w-full"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-gray-300 font-medium text-gray-100 mb-1 text-gray-300">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100 w-full"
                rows={3}
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              type="submit"
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              {editingId ? "Update" : "Create"}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600"
            > title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {/* Task List */}
      <div className="bg-gray-800 border border-gray-700 rounded shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="text-left px-4 py-3 text-gray-100 cursor-pointer select-none text-gray-300" onClick={() => requestSort('title')}>Title{getSortIndicator('title')}</th>
              <th className="text-left px-4 py-3 text-gray-100 cursor-pointer select-none text-gray-300" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="text-left px-4 py-3 text-gray-100 cursor-pointer select-none text-gray-300" onClick={() => requestSort('priority')}>Priority{getSortIndicator('priority')}</th>
              <th className="text-left px-4 py-3 text-gray-100 cursor-pointer select-none text-gray-300" onClick={() => requestSort('dueDate')}>Due Date{getSortIndicator('dueDate')}</th>
              <th className="text-left px-4 py-3 text-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="text-center py-8">
                  Loading...
                </td>
              </tr>
            ) : sortedTasks.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">
                  No tasks found
                </td>
              </tr>
            ) : (
              sortedTasks.map((task) => (
                <tr key={task.id} className="border-t border-gray-700 hover:bg-gray-800">
                  <td className="px-4 py-3 text-gray-100">
                    <div className="font-medium text-gray-100">{task.title}</div>
                    {task.description && (
                      <div className="text-sm text-gray-300 text-gray-400 truncate max-w-xs">
                        {task.description}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-100">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium text-gray-100 ${
                        task.status === "done"
                          ? "bg-green-900/50 text-green-200"
                          : task.status === "in_progress"
                          ? "bg-yellow-900/50 text-yellow-200"
                          : "bg-gray-800 text-gray-100"
                      }`}
                    >
                      {task.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-100">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium text-gray-100 ${
                        task.priority === "high"
                          ? "bg-red-900/50 text-red-200"
                          : task.priority === "medium"
                          ? "bg-orange-900/50 text-orange-200"
                          : "bg-blue-900/50 text-blue-200"
                      }`}
                    >
                      {task.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-100 text-sm text-gray-300">
                    {task.dueDate || "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-100">
                    <div className="flex gap-2">
                      <button
                        onClick={() => openEdit(task)}
                        className="text-blue-400 hover:underline text-sm text-gray-300"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(task.id)}
                        className="text-red-400 hover:underline text-sm text-gray-300"
                      > title="Delete key to delete" Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-center items-center gap-4 mt-4 text-gray-300">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 bg-gray-800 text-gray-100"
        >
          Prev
        </button>
        <span className="text-sm text-gray-300">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 bg-gray-800 text-gray-100"
        >
          Next
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 shadow-xl max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2 text-gray-100">Confirm Delete</h3>
            <p className="text-gray-300 mb-4">
              Are you sure you want to delete this task? This action cannot be
              undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 border border-gray-700 rounded hover:bg-gray-800 bg-gray-800 text-gray-100"
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
}
