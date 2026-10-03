import { useState } from 'react';

interface Invoice {
  id: number;
  number: string;
  customer: string;
  amount: number;
  status: string;
  dueDate: string;
}

const mockInvoices: Invoice[] = [
  { id: 1, number: 'INV-001', customer: 'Alice Brown', amount: 1500.00, status: 'Paid', dueDate: '2024-03-15' },
  { id: 2, number: 'INV-002', customer: 'Charlie Davis', amount: 890.50, status: 'Pending', dueDate: '2024-03-20' },
  { id: 3, number: 'INV-003', customer: 'Eve Johnson', amount: 2300.00, status: 'Overdue', dueDate: '2024-02-28' },
];

export default function Invoices() {
  const [invoices] = useState<Invoice[]>(mockInvoices);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Number', 'Customer', 'Amount', 'Status', 'Due Date'];
    const rows = invoices.map(i => [i.id, i.number, i.customer, i.amount, i.status, i.dueDate]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'invoices.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Invoices exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(invoices, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'invoices.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Invoices exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Invoices</h1>
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
            <th className="border p-2">Number</th>
            <th className="border p-2">Customer</th>
            <th className="border p-2">Amount</th>
            <th className="border p-2">Status</th>
            <th className="border p-2">Due Date</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map(i => (
            <tr key={i.id}>
              <td className="border p-2">{i.id}</td>
              <td className="border p-2">{i.number}</td>
              <td className="border p-2">{i.customer}</td>
              <td className="border p-2">${i.amount}</td>
              <td className="border p-2">{i.status}</td>
              <td className="border p-2">{i.dueDate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
