import { useState } from 'react';

interface Setting {
  id: number;
  key: string;
  value: string;
  description: string;
}

const mockSettings: Setting[] = [
  { id: 1, key: 'site_name', value: 'APEX-OS', description: 'Website name' },
  { id: 2, key: 'admin_email', value: 'admin@apex-os.com', description: 'Administrator email' },
  { id: 3, key: 'items_per_page', value: '25', description: 'Items per page in lists' },
];

export default function Settings() {
  const [settings] = useState<Setting[]>(mockSettings);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Key', 'Value', 'Description'];
    const rows = settings.map(s => [s.id, s.key, s.value, s.description]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'settings.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Settings exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'settings.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Settings exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
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
            <th className="border p-2">Key</th>
            <th className="border p-2">Value</th>
            <th className="border p-2">Description</th>
          </tr>
        </thead>
        <tbody>
          {settings.map(s => (
            <tr key={s.id}>
              <td className="border p-2">{s.id}</td>
              <td className="border p-2">{s.key}</td>
              <td className="border p-2">{s.value}</td>
              <td className="border p-2">{s.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
