import React, { useState, useRef, useEffect } from 'react';
import { userApi, type User } from '../api/client';

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setUsers(userApi.getAll());
  }, []);

  useEffect(() => {
    if (isModalOpen && firstFieldRef.current) {
      firstFieldRef.current.focus();
    }
  }, [isModalOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      setIsModalOpen(false);
    }
  };

  const openCreateModal = () => {
    setEditingUser(null);
    setIsModalOpen(true);
    setAnnouncement('Create user dialog opened');
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setIsModalOpen(true);
    setAnnouncement(`Edit user dialog opened for ${user.name}`);
  };

  const handleDelete = (user: User) => {
    userApi.delete(user.id);
    setUsers(userApi.getAll());
    setAnnouncement(`User ${user.name} deleted`);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    const name = formData.get('name') as string;
    const email = formData.get('email') as string;
    const role = formData.get('role') as string;
    const status = 'Active';

    if (editingUser) {
      userApi.update(editingUser.id, { name, email, role, status });
    } else {
      userApi.create({ name, email, role, status });
    }
    setUsers(userApi.getAll());
    setAnnouncement(editingUser ? 'User updated successfully' : 'User created successfully');
    setIsModalOpen(false);
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">User Management</h1>

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={openCreateModal}
        aria-label="Create new user"
        className="bg-blue-600 text-white px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
      >
        Create User
      </button>

      <div className="mt-4 overflow-x-auto">
        <table
          role="table"
          aria-label="Users list"
          className="min-w-full border-collapse border border-gray-300"
        >
          <thead>
            <tr>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Name</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Email</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Role</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Status</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td className="border border-gray-300 px-4 py-2">{user.name}</td>
                <td className="border border-gray-300 px-4 py-2">{user.email}</td>
                <td className="border border-gray-300 px-4 py-2">{user.role}</td>
                <td className="border border-gray-300 px-4 py-2">{user.status}</td>
                <td className="border border-gray-300 px-4 py-2">
                  <button
                    onClick={() => openEditModal(user)}
                    aria-label={`Edit user ${user.name}`}
                    className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(user)}
                    aria-label={`Delete user ${user.name}`}
                    className="bg-red-600 text-white px-3 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="user-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          ref={modalRef}
        >
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 id="user-modal-title" className="text-xl font-bold mb-4">
              {editingUser ? 'Edit User' : 'Create User'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="user-name" className="block text-sm font-medium mb-1">
                  Name
                </label>
                <input
                  ref={firstFieldRef}
                  id="user-name"
                  name="name"
                  type="text"
                  aria-label="User name"
                  aria-required="true"
                  defaultValue={editingUser?.name || ''}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="user-email" className="block text-sm font-medium mb-1">
                  Email
                </label>
                <input
                  id="user-email"
                  name="email"
                  type="email"
                  aria-label="User email"
                  aria-required="true"
                  defaultValue={editingUser?.email || ''}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="user-role" className="block text-sm font-medium mb-1">
                  Role
                </label>
                <select
                  id="user-role"
                  name="role"
                  aria-label="User role"
                  aria-required="true"
                  defaultValue={editingUser?.role || 'Viewer'}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  <option value="Admin">Admin</option>
                  <option value="Editor">Editor</option>
                  <option value="Viewer">Viewer</option>
                </select>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  aria-label="Cancel"
                  className="bg-gray-300 text-gray-800 px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  aria-label={editingUser ? 'Save user changes' : 'Create user'}
                  className="bg-blue-600 text-white px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  {editingUser ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
