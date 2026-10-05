import React, { useState, useEffect, useCallback } from 'react';
import { exportToCSV } from '../hooks/useKeyboardShortcuts';

interface Task {
  id: number;
  title: string;
  assignee: string;
  done: boolean;
  project_id: number;
}

interface TaskFormData {
  title: string;
  assignee: string;
  done: boolean;
  project_id: number;
}

const EMPTY_FORM: TaskFormData = { title: '', assignee: '', done: false, project_id: 0 };
const PAGE_SIZE = 10;

export default function TaskManagement() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'done' | 'pending'>('all');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [formData, setFormData] = useState<TaskFormData>(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/tasks/', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTasks(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const filtered = tasks.filter(t => {
    const q = search.toLowerCase();
    const matchSearch = !q || t.title.toLowerCase().includes(q) || t.assignee.toLowerCase().includes(q);
    const matchStatus = statusFilter === 'all' || (statusFilter === 'done' ? t.done : !t.done);
    return matchSearch && matchStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function openCreate() {
    setEditingTask(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(task: Task) {
    setEditingTask(task);
    setFormData({ title: task.title, assignee: task.assignee, done: task.done, project_id: task.project_id });
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const url = editingTask ? `/api/tasks/${editingTask.id}/` : '/api/tasks/';
      const method = editingTask ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      await fetchTasks();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    try {
      const res = await fetch(`/api/tasks/${id}/`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      await fetchTasks();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  }

  function handleToggleDone(task: Task) {
    fetch(`/api/tasks/${task.id}/`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
      body: JSON.stringify({ done: !task.done }),
    }).then(() => fetchTasks());
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Task Management</h1>
          <button onClick={openCreate} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium">
            + New Task
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>
        )}

        <div className="flex flex-wrap gap-3 mb-4">
          <input
            type="text"
            placeholder="Search tasks..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="flex-1 min-w-[200px] px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
          />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value as any); setPage(1); }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="all">All</option>
            <option value="done">Done</option>
            <option value="pending">Pending</option>
          </select>
          <button
            onClick={() => exportToCSV(tasks as unknown as Record<string, unknown>[], 'tasks_export.csv')}
            className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Export CSV
          </button>
        </div>

        {showForm && (
          <div className="mb-6 p-4 bg-gray-800 border border-gray-700 rounded">
            <h2 className="text-lg font-semibold mb-3">{editingTask ? 'Edit Task' : 'Create Task'}</h2>
            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                required
                placeholder="Title"
                value={formData.title || ''}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
                className="px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              />
              <input
                placeholder="Assignee"
                value={formData.assignee || ''}
                onChange={e => setFormData({ ...formData, assignee: e.target.value })}
                className="px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              />
              <input
                type="number"
                placeholder="Project ID"
                value={formData.project_id || ''}
                onChange={e => setFormData({ ...formData, project_id: parseInt(e.target.value) || 0 })}
                className="px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.done}
                  onChange={e => setFormData({ ...formData, done: e.target.checked })}
                  className="rounded"
                />
                Done
              </label>
              <div className="md:col-span-2 flex gap-2">
                <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium">
                  {saving ? 'Saving...' : editingTask ? 'Update' : 'Create'}
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="overflow-x-auto bg-gray-800 border border-gray-700 rounded">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-gray-400">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Assignee</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : paginated.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-16 text-center">
                  <div className="text-5xl mb-4">✅</div>
                  <h3 className="text-lg font-semibold text-gray-100 mb-2">No tasks yet</h3>
                  <p className="text-gray-400 mb-4">Get started by creating your first task.</p>
                  <button onClick={openCreate} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                    + New Task
                  </button>
                </td></tr>
              ) : (
                paginated.map(task => (
                  <tr key={task.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="px-4 py-3 text-gray-400">{task.id}</td>
                    <td className="px-4 py-3">{task.title}</td>
                    <td className="px-4 py-3">{task.assignee}</td>
                    <td className="px-4 py-3">{task.project_id}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => handleToggleDone(task)} className={`px-2 py-1 rounded text-xs font-medium ${task.done ? 'bg-green-900/50 text-green-300' : 'bg-yellow-900/50 text-yellow-300'}`}>
                        {task.done ? 'Done' : 'Pending'}
                      </button>
                    </td>
                    <td className="px-4 py-3 flex gap-2">
                      <button onClick={() => openEdit(task)} className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs">Edit</button>
                      <button onClick={() => setDeleteConfirm(task.id)} className="px-2 py-1 bg-red-900/50 hover:bg-red-800 text-red-300 rounded text-xs">Delete</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-gray-400">
              Page {safePage} of {totalPages} ({filtered.length} tasks)
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={safePage <= 1}
                className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50"
              >
                Prev
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={safePage >= totalPages}
                className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {deleteConfirm !== null && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded p-6 max-w-sm w-full mx-4">
              <h3 className="text-lg font-semibold mb-2">Delete Task</h3>
              <p className="text-sm text-gray-400 mb-4">Are you sure you want to delete task #{deleteConfirm}? This cannot be undone.</p>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">Cancel</button>
                <button onClick={() => handleDelete(deleteConfirm)} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-medium">Delete</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
