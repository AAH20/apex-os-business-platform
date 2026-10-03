import { useState } from 'react';

interface Role {
  id: number;
  name: string;
  description: string;
  userCount: number;
}

const mockRoles: Role[] = [
  { id: 1, name: 'Admin', description: 'Full system access', userCount: 3 },
  { id: 2, name: 'Editor', description: 'Can edit content', userCount: 12 },
  { id: 3, name: 'Viewer', description: 'Read-only access', userCount: 45 },
];

export default function Roles() {
  const [roles] = useState<Role[]>(mockRoles);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Description', 'User Count'];
    const rows = roles.map(r => [r.id, r.name, r.description, r.userCount]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'roles.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Roles exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(roles, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'roles.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Roles exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Roles</h1>
        <div className="flex gap-2">
          <button onClick={exportCSV} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">Export CSV</button>
          <button onClick={exportJSON} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Export JSON</button>
        </div>
      </div>
      {exportMessage && <div className="mb-4 p-3 bg-green-100 text-green-800 rounded">{exportMessage}</div>}
      <table className="w-full border-collapse border">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2">ID</th>
            <th className="border p-2">Name</th>
            <th className="border p-2">Description</th>
            <th className="border p-2">User Count</th>
          </tr>
        </thead>
        <tbody>
          {roles.map(r => (
            <tr key={r.id}>
              <td className="border p-2">{r.id}</td>
              <td className="border p-2">{r.name}</td>
              <td className="border p-2">{r.description}</td>
              <td className="border p-2">{r.userCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
