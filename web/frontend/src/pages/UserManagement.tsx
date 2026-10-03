import React, { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────
type Role = 'admin' | 'manager' | 'editor' | 'viewer';
type Status = 'active' | 'inactive' | 'suspended';

interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: Status;
  createdAt: string;
  lastLogin: string;
  avatar?: string;
}

interface ActivityEntry {
  id: string;
  userId: string;
  action: string;
  timestamp: string;
  details?: string;
}

interface UserFormData {
  name: string;
  email: string;
  role: Role;
  status: Status;
}

// ─── Constants ───────────────────────────────────────────────────────────────
const ROLES: Role[] = ['admin', 'manager', 'editor', 'viewer'];
const STATUSES: Status[] = ['active', 'inactive', 'suspended'];
const PAGE_SIZE = 10;

const ROLE_PERMISSIONS: Record<Role, string[]> = {
  admin: ['Full access', 'Manage users', 'Manage roles', 'Delete data', 'System config'],
  manager: ['View all', 'Edit content', 'Manage editors', 'View reports'],
  editor: ['View assigned', 'Edit own content', 'Upload media'],
  viewer: ['View only', 'Read access'],
};

const ROLE_COLORS: Record<Role, string> = {
  admin: 'bg-red-100 text-red-800',
  manager: 'bg-blue-100 text-blue-800',
  editor: 'bg-green-100 text-green-800',
  viewer: 'bg-gray-100 text-gray-800',
};

const STATUS_COLORS: Record<Status, string> = {
  active: 'bg-emerald-100 text-emerald-800',
  inactive: 'bg-yellow-100 text-yellow-800',
  suspended: 'bg-red-100 text-red-800',
};

// ─── API helpers ─────────────────────────────────────────────────────────────
const api = {
  async list(params: Record<string, string | number>): Promise<{ users: User[]; total: number }> {
    const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
    const res = await fetch(`/api/users?${qs}`);
    if (!res.ok) throw new Error('Failed to fetch users');
    return res.json();
  },
  async get(id: string): Promise<User> {
    const res = await fetch(`/api/users/${id}`);
    if (!res.ok) throw new Error('Failed to fetch user');
    return res.json();
  },
  async create(data: UserFormData): Promise<User> {
    const res = await fetch('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!res.ok) throw new Error('Failed to create user');
    return res.json();
  },
  async update(id: string, data: Partial<UserFormData>): Promise<User> {
    const res = await fetch(`/api/users/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!res.ok) throw new Error('Failed to update user');
    return res.json();
  },
  async remove(id: string): Promise<void> {
    const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete user');
  },
  async activity(id: string): Promise<ActivityEntry[]> {
    const res = await fetch(`/api/users/${id}/activity`);
    if (!res.ok) return [];
    return res.json();
  },
};

// ─── Component ───────────────────────────────────────────────────────────────
export default function UserManagement() {
  // State
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<Role | ''>('');
  const [statusFilter, setStatusFilter] = useState<Status | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [modal, setModal] = useState<'create' | 'edit' | 'delete' | 'details' | 'activity' | 'bulk' | null>(null);
  const [activeUser, setActiveUser] = useState<User | null>(null);
  const [form, setForm] = useState<UserFormData>({ name: '', email: '', role: 'viewer', status: 'active' });
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>([]);
  const [bulkAction, setBulkAction] = useState<'delete' | 'activate' | 'deactivate'>('delete');

  // Fetch users
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.list({ page, limit: PAGE_SIZE, search, role: roleFilter, status: statusFilter });
      setUsers(data.users);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter, statusFilter]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  // Selection helpers
  const allSelected = users.length > 0 && users.every((u) => selected.has(u.id));
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(users.map((u) => u.id)));
  const toggleOne = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  // CRUD handlers
  const openCreate = () => { setForm({ name: '', email: '', role: 'viewer', status: 'active' }); setModal('create'); };
  const openEdit = (u: User) => { setActiveUser(u); setForm({ name: u.name, email: u.email, role: u.role, status: u.status }); setModal('edit'); };
  const openDelete = (u: User) => { setActiveUser(u); setModal('delete'); };
  const openDetails = (u: User) => { setActiveUser(u); setModal('details'); };
  const openActivity = async (u: User) => {
    setActiveUser(u);
    setActivityLog(await api.activity(u.id));
    setModal('activity');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (modal === 'create') await api.create(form);
      else if (modal === 'edit' && activeUser) await api.update(activeUser.id, form);
      setModal(null);
      fetchUsers();
    } catch (err: any) { setError(err.message); }
  };

  const handleDelete = async () => {
    if (!activeUser) return;
    setError('');
    try { await api.remove(activeUser.id); setModal(null); fetchUsers(); }
    catch (err: any) { setError(err.message); }
  };

  const handleBulk = async () => {
    setError('');
    try {
      if (bulkAction === 'delete') {
        await Promise.all([...selected].map((id) => api.remove(id)));
      } else {
        const status: Status = bulkAction === 'activate' ? 'active' : 'inactive';
        await Promise.all([...selected].map((id) => api.update(id, { status })));
      }
      setSelected(new Set());
      setModal(null);
      fetchUsers();
    } catch (err: any) { setError(err.message); }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        <button onClick={openCreate} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium">+ New User</button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search users…" className="border rounded-lg px-3 py-2 text-sm flex-1 min-w-[200px]" />
        <select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value as Role | ''); setPage(1); }} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">All Roles</option>
          {ROLES.map((r) => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value as Status | ''); setPage(1); }} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
        {selected.size > 0 && (
          <button onClick={() => setModal('bulk')} className="px-3 py-2 bg-gray-800 text-white rounded-lg text-sm hover:bg-gray-900">
            Bulk Actions ({selected.size})
          </button>
        )}
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left"><input type="checkbox" checked={allSelected} onChange={toggleAll} /></th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">User</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Role</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Last Login</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No users found</td></tr>
            ) : users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3"><input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleOne(u.id)} /></td>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{u.name}</div>
                  <div className="text-gray-500 text-xs">{u.email}</div>
                </td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${ROLE_COLORS[u.role]}`}>{u.role}</span></td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[u.status]}`}>{u.status}</span></td>
                <td className="px-4 py-3 text-gray-500">{new Date(u.lastLogin).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right space-x-1">
                  <button onClick={() => openDetails(u)} className="text-indigo-600 hover:text-indigo-800 text-xs font-medium">View</button>
                  <button onClick={() => openEdit(u)} className="text-gray-600 hover:text-gray-800 text-xs font-medium ml-2">Edit</button>
                  <button onClick={() => openActivity(u)} className="text-gray-600 hover:text-gray-800 text-xs font-medium ml-2">Log</button>
                  <button onClick={() => openDelete(u)} className="text-red-600 hover:text-red-800 text-xs font-medium ml-2">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-gray-500">Page {page} of {totalPages} ({total} users)</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-40">Prev</button>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-40">Next</button>
          </div>
        </div>
      )}

      {/* ─── Modals ─── */}
      {/* Create / Edit */}
      {(modal === 'create' || modal === 'edit') && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">{modal === 'create' ? 'Create User' : 'Edit User'}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div><label className="block text-sm font-medium mb-1">Name</label>
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium mb-1">Email</label>
                <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium mb-1">Role</label>
                <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select></div>
              <div><label className="block text-sm font-medium mb-1">Status</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as Status })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">{modal === 'create' ? 'Create' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {modal === 'delete' && activeUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-2">Delete User</h2>
            <p className="text-sm text-gray-600 mb-4">Are you sure you want to delete <strong>{activeUser.name}</strong>? This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Details */}
      {modal === 'details' && activeUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">User Details</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Name</span><span className="font-medium">{activeUser.name}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Email</span><span>{activeUser.email}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Role</span><span className={`px-2 py-1 rounded-full text-xs font-medium ${ROLE_COLORS[activeUser.role]}`}>{activeUser.role}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Status</span><span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[activeUser.status]}`}>{activeUser.status}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Created</span><span>{new Date(activeUser.createdAt).toLocaleDateString()}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Last Login</span><span>{new Date(activeUser.lastLogin).toLocaleDateString()}</span></div>
            </div>
            {/* RBAC display */}
            <div className="mt-5 border-t pt-4">
              <h3 className="text-sm font-semibold mb-2">Role Permissions</h3>
              <div className="flex flex-wrap gap-2">
                {ROLE_PERMISSIONS[activeUser.role].map((p) => (
                  <span key={p} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs">{p}</span>
                ))}
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-600">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Activity log */}
      {modal === 'activity' && activeUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Activity Log — {activeUser.name}</h2>
            {activityLog.length === 0 ? (
              <p className="text-sm text-gray-400">No activity recorded.</p>
            ) : (
              <div className="space-y-3">
                {activityLog.map((entry) => (
                  <div key={entry.id} className="border-l-2 border-indigo-200 pl-3">
                    <div className="text-sm font-medium">{entry.action}</div>
                    {entry.details && <div className="text-xs text-gray-500">{entry.details}</div>}
                    <div className="text-xs text-gray-400">{new Date(entry.timestamp).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            )}
            <div className="flex justify-end mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-600">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk actions */}
      {modal === 'bulk' && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Bulk Actions ({selected.size} selected)</h2>
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm"><input type="radio" name="bulk" checked={bulkAction === 'delete'} onChange={() => setBulkAction('delete')} /> Delete selected</label>
              <label className="flex items-center gap-2 text-sm"><input type="radio" name="bulk" checked={bulkAction === 'activate'} onChange={() => setBulkAction('activate')} /> Set active</label>
              <label className="flex items-center gap-2 text-sm"><input type="radio" name="bulk" checked={bulkAction === 'deactivate'} onChange={() => setBulkAction('deactivate')} /> Set inactive</label>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
              <button onClick={handleBulk} className={`px-4 py-2 text-white rounded-lg text-sm ${bulkAction === 'delete' ? 'bg-red-600 hover:bg-red-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>Apply</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
