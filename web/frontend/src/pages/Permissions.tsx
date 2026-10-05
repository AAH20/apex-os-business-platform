import { useState } from 'react';

interface Permission {
  id: number;
  name: string;
  description: string;
  module: string;
}

const mockPermissions: Permission[] = [
  { id: 1, name: 'users.read', description: 'View users', module: 'Users' },
  { id: 2, name: 'users.write', description: 'Create and edit users', module: 'Users' },
  { id: 3, name: 'products.read', description: 'View products', module: 'Products' },
];

export default function Permissions() {
  const [permissions, setPermissions] = useState<Permission[]>(mockPermissions);
  const [editingPermission, setEditingPermission] = useState<Permission | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [exportMessage, setExportMessage] = useState('');

  const handleEdit = (permission: Permission) => {
    setEditingPermission({ ...permission });
  };

  const handleSaveEdit = () => {
    if (!editingPermission) return;
    setPermissions(prev => prev.map(p => p.id === editingPermission.id ? editingPermission : p));
    setEditingPermission(null);
  };

  const handleDelete = (id: number) => {
    setPermissions(prev => prev.filter(p => p.id !== id));
    setShowDeleteConfirm(null);
  };

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Description', 'Module'];
    const rows = permissions.map(p => [p.id, p.name, p.description, p.module]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'permissions.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Permissions exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(permissions, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'permissions.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Permissions exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Permissions</h1>
        <div className="flex gap-2">
          <button onClick={exportCSV} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">Export CSV</button>
          <button onClick={exportJSON} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Export JSON</button>
        </div>
      </div>
      {exportMessage && <div className="mb-4 p-3 bg-green-100 text-green-800 rounded">{exportMessage}</div>}
      <table className="w-full border-collapse border">
        <thead>
          <tr className="bg-gray-800">
            <th className="border p-2">ID</th>
            <th className="border p-2">Name</th>
            <th className="border p-2">Description</th>
            <th className="border p-2">Module</th>
            <th className="border p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {permissions.map(p => (
            <tr key={p.id}>
              <td className="border p-2">{p.id}</td>
              <td className="border p-2">{p.name}</td>
              <td className="border p-2">{p.description}</td>
              <td className="border p-2">{p.module}</td>
              <td className="border p-2">
                <button onClick={() => handleEdit(p)} className="text-blue-600 hover:underline mr-3">Edit</button>
                <button onClick={() => setShowDeleteConfirm(p.id)} className="text-red-600 hover:underline">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editingPermission && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Edit Permission</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={editingPermission.name}
                  onChange={e => setEditingPermission({ ...editingPermission, name: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <input
                  type="text"
                  value={editingPermission.description}
                  onChange={e => setEditingPermission({ ...editingPermission, description: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Module</label>
                <input
                  type="text"
                  value={editingPermission.module}
                  onChange={e => setEditingPermission({ ...editingPermission, module: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setEditingPermission(null)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600">Cancel</button>
              <button onClick={handleSaveEdit} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Save</button>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this permission? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
