import { useState } from 'react';

interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string;
  company: string;
}

const mockCustomers: Customer[] = [
  { id: 1, name: 'Alice Brown', email: 'alice@corp.com', phone: '555-0101', company: 'Corp Inc' },
  { id: 2, name: 'Charlie Davis', email: 'charlie@tech.com', phone: '555-0102', company: 'Tech LLC' },
  { id: 3, name: 'Eve Johnson', email: 'eve@shop.com', phone: '555-0103', company: 'Shop Co' },
];

export default function Customers() {
  const [customers] = useState<Customer[]>(mockCustomers);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Email', 'Phone', 'Company'];
    const rows = customers.map(c => [c.id, c.name, c.email, c.phone, c.company]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'customers.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Customers exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(customers, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'customers.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Customers exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Customers</h1>
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
            <th className="border p-2">Email</th>
            <th className="border p-2">Phone</th>
            <th className="border p-2">Company</th>
          </tr>
        </thead>
        <tbody>
          {customers.map(c => (
            <tr key={c.id}>
              <td className="border p-2">{c.id}</td>
              <td className="border p-2">{c.name}</td>
              <td className="border p-2">{c.email}</td>
              <td className="border p-2">{c.phone}</td>
              <td className="border p-2">{c.company}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
