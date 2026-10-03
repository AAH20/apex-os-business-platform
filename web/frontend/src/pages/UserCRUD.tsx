import React, { useState, useEffect, useCallback } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  status: string;
  createdAt: string;
}

interface UserFormData {
  name: string;
  email: string;
  role: string;
  status: string;
}

const API_BASE = '/api/users';
const PAGE_SIZE = 10;

const emptyForm: UserFormData = { name: '', email: '', role: 'user', status: 'active' };

const UserCRUD: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [formData, setFormData] = useState<UserFormData>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { sortedData: sortedUsers, requestSort, getSortIndicator } = useSort(users);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(PAGE_SIZE),
        ...(search && { search }),
        ...(roleFilter && { role: roleFilter }),
        ...(statusFilter && { status: statusFilter }),
      });
      const res = await fetch(`${API_BASE}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setUsers(data.users || data.data || []);
      setTotal(data.total || (data.users || data.data || []).length);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter, statusFilter]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setFormData(emptyForm);
      setEditingId(null);
      setShowForm(false);
      fetchUsers();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    }
  };

  const handleEdit = (user: User) => {
    setFormData({ name: user.name, email: user.email, role: user.role, status: user.status });
    setEditingId(user.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    setError('');
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchUsers();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(users as Record<string, unknown>[], "user_export.csv"), onDelete: () => { if (users.length > 0) setShowDeleteConfirm(users[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">User Management</h1>

      {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

      {/* Search & Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search users..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"
         ref={searchRef}/>
        <select value={roleFilter} onChange={e => { setRoleFilter(e.target.value); setPage(1); }} className="border rounded px-3 py-2">
          <option value="">All Roles</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="moderator">Moderator</option>
        </select>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} className="border rounded px-3 py-2">
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        > title="Ctrl+N"
          + New User
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">{editingId ? 'Edit User' : 'Create User'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text" placeholder="Name" required value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <input
              type="email" placeholder="Email" required value={formData.email}
              onChange={e => setFormData({ ...formData, email: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <select value={formData.role} onChange={e => setFormData({ ...formData, role: e.target.value })} className="border rounded px-3 py-2">
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="moderator">Moderator</option>
            </select>
            <select value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} className="border rounded px-3 py-2">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <div className="mt-3 flex gap-2">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); }} className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"> title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {/* Users Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse bg-white shadow rounded">
          <thead>
            <tr className="bg-gray-100">
              <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('email')}>Email{getSortIndicator('email')}</th>
              <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('role')}>Role{getSortIndicator('role')}</th>
              <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="border px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="border px-4 py-4 text-center">Loading...</td></tr>
            ) : sortedUsers.length === 0 ? (
              <tr><td colSpan={6} className="border px-4 py-4 text-center">No users found</td></tr>
            ) : (
              sortedUsers.map(user => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="border px-4 py-2">{user.id}</td>
                  <td className="border px-4 py-2">{user.name}</td>
                  <td className="border px-4 py-2">{user.email}</td>
                  <td className="border px-4 py-2">{user.role}</td>
                  <td className="border px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs ${user.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {user.status}
                    </span>
                  </td>
                  <td className="border px-4 py-2">
                    <button onClick={() => handleEdit(user)} className="text-blue-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(user.id)} className="text-red-600 hover:underline"> title="Delete key to delete" Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Prev
          </button>
          <span className="px-3">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded p-6 shadow-lg max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="mb-4">Are you sure you want to delete user #{showDeleteConfirm}? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"> title="Escape to close" Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserCRUD;
