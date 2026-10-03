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
  const [permissions] = useState<Permission[]>(mockPermissions);
  const [exportMessage, setExportMessage] = useState('');

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
          <tr className="bg-gray-100">
            <th className="border p-2">ID</th>
            <th className="border p-2">Name</th>
            <th className="border p-2">Description</th>
            <th className="border p-2">Module</th>
          </tr>
        </thead>
        <tbody>
          {permissions.map(p => (
            <tr key={p.id}>
              <td className="border p-2">{p.id}</td>
              <td className="border p-2">{p.name}</td>
              <td className="border p-2">{p.description}</td>
              <td className="border p-2">{p.module}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
