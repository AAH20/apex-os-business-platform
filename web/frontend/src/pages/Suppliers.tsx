import { useState } from 'react';

interface Supplier {
  id: number;
  name: string;
  contact: string;
  email: string;
  country: string;
}

const mockSuppliers: Supplier[] = [
  { id: 1, name: 'Global Parts', contact: 'Mike Lee', email: 'mike@globalparts.com', country: 'USA' },
  { id: 2, name: 'Euro Supplies', contact: 'Anna Schmidt', email: 'anna@eurosupplies.de', country: 'Germany' },
  { id: 3, name: 'Asia Manufacturing', contact: 'Kenji Tanaka', email: 'kenji@asiamfg.jp', country: 'Japan' },
];

export default function Suppliers() {
  const [suppliers] = useState<Supplier[]>(mockSuppliers);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Contact', 'Email', 'Country'];
    const rows = suppliers.map(s => [s.id, s.name, s.contact, s.email, s.country]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'suppliers.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Suppliers exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(suppliers, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'suppliers.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Suppliers exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Suppliers</h1>
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
            <th className="border p-2">Contact</th>
            <th className="border p-2">Email</th>
            <th className="border p-2">Country</th>
          </tr>
        </thead>
        <tbody>
          {suppliers.map(s => (
            <tr key={s.id}>
              <td className="border p-2">{s.id}</td>
              <td className="border p-2">{s.name}</td>
              <td className="border p-2">{s.contact}</td>
              <td className="border p-2">{s.email}</td>
              <td className="border p-2">{s.country}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
