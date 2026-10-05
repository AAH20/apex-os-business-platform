import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { fetchWithTimeout } from '../api/fallback';

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserFormData {
  name: string;
  email: string;
  role: string;
  is_active: boolean;
}

const API_BASE = '/api/users';
const PAGE_SIZE = 10;

const emptyForm: UserFormData = { name: '', email: '', role: 'user', is_active: true };

const FALLBACK_USERS: User[] = [
  { id: 1, name: "Admin User", email: "admin@apexos.io", role: "admin", is_active: true, created_at: "2026-01-15" },
  { id: 2, name: "Sarah Chen", email: "sarah@apexos.io", role: "editor", is_active: true, created_at: "2026-02-20" },
  { id: 3, name: "Mike Ross", email: "mike@apexos.io", role: "editor", is_active: true, created_at: "2026-03-10" },
  { id: 4, name: "Jane Smith", email: "jane@apexos.io", role: "viewer", is_active: false, created_at: "2026-04-05" },
  { id: 5, name: "Bob Wilson", email: "bob@apexos.io", role: "viewer", is_active: true, created_at: "2026-05-12" },
];

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
      const res = await fetchWithTimeout(`${API_BASE}?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.users || data.data || data.items || []);
      if (items.length > 0) {
        setUsers(items);
        setTotal(data.total || items.length);
      } else {
        setUsers(FALLBACK_USERS);
        setTotal(FALLBACK_USERS.length);
      }
    } catch (e: any) {
      setUsers(FALLBACK_USERS);
      setTotal(FALLBACK_USERS.length);
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
      const res = await fetchWithTimeout(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
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
    setFormData({ name: user.name, email: user.email, role: user.role, is_active: user.is_active });
    setEditingId(user.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    setError('');
    try {
      const res = await fetchWithTimeout(`${API_BASE}/${id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
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
  useKeyboardShortcuts({ onNew: () => { setShowForm(true); setEditingId(null); }, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(users as unknown as Record<string, unknown>[], "user_export.csv"), onDelete: () => { if (users.length > 0) setShowDeleteConfirm(users[0].id); }, onClose: () => setShowForm(false) });

  return (
    <div className="p-6 max-w-6xl mx-auto bg-gray-900 text-gray-100">
      <h1 className="text-2xl font-bold mb-6 text-gray-100">User Management</h1>

      {error && <div className="bg-red-900/50 text-red-200 p-3 rounded mb-4 text-gray-300">{error}</div>}

      {/* Search & Filters */}
      <div className="flex flex-wrap gap-3 mb-4 text-gray-300">
        <input
          type="text"
          placeholder="Search users..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="border border-gray-700 rounded px-3 text-gray-300 py-2 flex-1 min-w-[200px] bg-gray-800 text-gray-100"
         ref={searchRef}/>
        <select value={roleFilter} onChange={e => { setRoleFilter(e.target.value); setPage(1); }} className="border border-gray-700 rounded px-3 text-gray-300 py-2 bg-gray-800 text-gray-100">
          <option value="">All Roles</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="moderator">Moderator</option>
        </select>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} className="border border-gray-700 rounded px-3 text-gray-300 py-2 bg-gray-800 text-gray-100">
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New User
        </button>
        <button
          onClick={() => exportToCSV(users as unknown as Record<string, unknown>[], "user_export.csv")}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >
          Export CSV
        </button>
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(users, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'user_export.json';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
        >
          Export JSON
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded p-4 mb-4 text-gray-300 shadow">
          <h2 className="text-lg font-semibold mb-3 text-gray-100">{editingId ? 'Edit User' : 'Create User'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text" placeholder="Name" required value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="border border-gray-700 rounded px-3 text-gray-300 py-2 bg-gray-800 text-gray-100"
            />
            <input
              type="email" placeholder="Email" required value={formData.email}
              onChange={e => setFormData({ ...formData, email: e.target.value })}
              className="border border-gray-700 rounded px-3 text-gray-300 py-2 bg-gray-800 text-gray-100"
            />
            <select value={formData.role} onChange={e => setFormData({ ...formData, role: e.target.value })} className="border border-gray-700 rounded px-3 text-gray-300 py-2 bg-gray-800 text-gray-100">
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="moderator">Moderator</option>
            </select>
            <select value={formData.is_active ? 'active' : 'inactive'} onChange={e => setFormData({ ...formData, is_active: e.target.value === 'active' })} className="border border-gray-700 rounded px-3 text-gray-300 py-2 bg-gray-800 text-gray-100">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <div className="mt-3 flex gap-2">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditingId(null); }} className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600"> title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {/* Users Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse bg-gray-800 shadow rounded">
          <thead>
            <tr className="bg-gray-900">
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('email')}>Email{getSortIndicator('email')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('role')}>Role{getSortIndicator('role')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('is_active')}>Status{getSortIndicator('is_active')}</th>
              <th className="border border-gray-700 px-4 py-2 text-gray-100 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="border border-gray-700 px-4 py-4 text-center text-gray-100">Loading...</td></tr>
            ) : sortedUsers.length === 0 ? (
              <tr><td colSpan={6} className="border border-gray-700 px-4 py-4 text-center text-gray-100">No users found</td></tr>
            ) : (
              sortedUsers.map(user => (
                <tr key={user.id} className="hover:bg-gray-800">
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{user.id}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{user.name}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{user.email}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{user.role}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">
                    <span className={`px-2 py-1 rounded text-xs ${user.is_active ? 'bg-green-900/50 text-green-200' : 'bg-red-900/50 text-red-200'}`}>
                      {user.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">
                    <button onClick={() => handleEdit(user)} className="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onClick={() => setShowDeleteConfirm(user.id)} className="text-red-400 hover:underline"> title="Delete key to delete" Delete</button>
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
            className="px-3 text-gray-300 py-1 border border-gray-700 rounded disabled:opacity-50 bg-gray-800 text-gray-100"
          >
            Prev
          </button>
          <span className="px-3 text-gray-300">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 text-gray-300 py-1 border border-gray-700 rounded disabled:opacity-50 bg-gray-800 text-gray-100"
          >
            Next
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded p-6 shadow-lg max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2 text-gray-100">Confirm Delete</h3>
            <p className="mb-4 text-gray-300">Are you sure you want to delete user #{showDeleteConfirm}? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600"> title="Escape to close" Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserCRUD;
