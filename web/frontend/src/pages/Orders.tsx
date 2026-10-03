import { useState } from 'react';

interface Order {
  id: number;
  customer: string;
  total: number;
  status: string;
  date: string;
}

const mockOrders: Order[] = [
  { id: 1, customer: 'Alice Brown', total: 150.00, status: 'Completed', date: '2024-03-01' },
  { id: 2, customer: 'Charlie Davis', total: 89.50, status: 'Pending', date: '2024-03-05' },
  { id: 3, customer: 'Eve Johnson', total: 230.00, status: 'Shipped', date: '2024-03-10' },
];

export default function Orders() {
  const [orders] = useState<Order[]>(mockOrders);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Customer', 'Total', 'Status', 'Date'];
    const rows = orders.map(o => [o.id, o.customer, o.total, o.status, o.date]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'orders.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Orders exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(orders, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'orders.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Orders exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Orders</h1>
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
            <th className="border p-2">Customer</th>
            <th className="border p-2">Total</th>
            <th className="border p-2">Status</th>
            <th className="border p-2">Date</th>
          </tr>
        </thead>
        <tbody>
          {orders.map(o => (
            <tr key={o.id}>
              <td className="border p-2">{o.id}</td>
              <td className="border p-2">{o.customer}</td>
              <td className="border p-2">${o.total}</td>
              <td className="border p-2">{o.status}</td>
              <td className="border p-2">{o.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
