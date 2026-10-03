import { useState, useEffect, useCallback } from "react";

// ── Types ──────────────────────────────────────────────────────────────────

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
}

interface UserFormData {
  name: string;
  email: string;
  role: string;
  is_active: boolean;
}

type ApiResponse = User[] | { items: User[] };

// ── Helpers ────────────────────────────────────────────────────────────────

function extractUsers(data: ApiResponse): User[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object" && "items" in data && Array.isArray(data.items)) {
    return data.items;
  }
  return [];
}

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Component ──────────────────────────────────────────────────────────────

const EMPTY_FORM: UserFormData = { name: "", email: "", role: "viewer", is_active: true };

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<UserFormData>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // ── Fetch users ─────────────────────────────────────────────────────────

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ApiResponse>("/api/users/");
      setUsers(extractUsers(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // ── Create / Update ─────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (editingId !== null) {
        await apiFetch(`/api/users/${editingId}/`, {
          method: "PUT",
          body: JSON.stringify(form),
        });
      } else {
        await apiFetch("/api/users/", {
          method: "POST",
          body: JSON.stringify(form),
        });
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save user");
    } finally {
      setSubmitting(false);
    }
  }

  function startEdit(user: User) {
    setEditingId(user.id);
    setForm({ name: user.name, email: user.email, role: user.role, is_active: user.is_active });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  // ── Delete ──────────────────────────────────────────────────────────────

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this user?")) return;
    setError(null);
    try {
      await apiFetch(`/api/users/${id}/`, { method: "DELETE" });
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    }
  }

  // ── Toggle active ───────────────────────────────────────────────────────

  async function toggleActive(user: User) {
    setError(null);
    try {
      await apiFetch(`/api/users/${user.id}/`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: !u.is_active } : u)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">User Management</h1>

      {/* Error banner */}
      {error && (
        <div className="mb-4 rounded-md bg-red-900/50 border border-red-700 px-4 py-3 text-red-200 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-300 hover:text-red-100 font-bold ml-4"
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}

      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="mb-8 rounded-lg bg-gray-800 p-4 flex flex-wrap gap-3 items-end"
      >
        <div className="flex flex-col">
          <label className="text-sm text-gray-400 mb-1">Name</label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded bg-gray-700 border border-gray-600 px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
            placeholder="Full name"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-sm text-gray-400 mb-1">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="rounded bg-gray-700 border border-gray-600 px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
            placeholder="user@example.com"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-sm text-gray-400 mb-1">Role</label>
          <select
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            className="rounded bg-gray-700 border border-gray-600 px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
          >
            <option value="admin">Admin</option>
            <option value="editor">Editor</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-300 pb-2">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            className="rounded bg-gray-700 border-gray-600"
          />
          Active
        </label>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 text-white font-medium"
          >
            {submitting ? "Saving…" : editingId !== null ? "Update" : "Create"}
          </button>
          {editingId !== null && (
            <button
              type="button"
              onClick={cancelEdit}
              className="rounded bg-gray-700 hover:bg-gray-600 px-4 py-2 text-gray-200"
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {/* Loading */}
      {loading && (
        <div className="text-center py-12 text-gray-400">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-600 border-t-blue-500" />
          <p className="mt-3">Loading users…</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && users.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg">No users found</p>
          <p className="text-sm mt-1">Create one using the form above.</p>
        </div>
      )}

      {/* Table */}
      {!loading && users.length > 0 && (
        <div className="overflow-x-auto rounded-lg bg-gray-800">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-sm text-gray-100">{user.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{user.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    <span className="inline-block rounded-full bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-200">
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <button
                      onClick={() => toggleActive(user)}
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        user.is_active
                          ? "bg-green-900/50 text-green-300"
                          : "bg-red-900/50 text-red-300"
                      }`}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right text-sm space-x-2">
                    <button
                      onClick={() => startEdit(user)}
                      className="text-blue-400 hover:text-blue-300"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(user.id)}
                      className="text-red-400 hover:text-red-300"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
