import { useState } from 'react';

interface Payment {
  id: number;
  invoice: string;
  amount: number;
  method: string;
  date: string;
}

const mockPayments: Payment[] = [
  { id: 1, invoice: 'INV-001', amount: 1500.00, method: 'Credit Card', date: '2024-03-10' },
  { id: 2, invoice: 'INV-002', amount: 890.50, method: 'Bank Transfer', date: '2024-03-12' },
  { id: 3, invoice: 'INV-003', amount: 2300.00, method: 'PayPal', date: '2024-03-15' },
];

export default function Payments() {
  const [payments] = useState<Payment[]>(mockPayments);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Invoice', 'Amount', 'Method', 'Date'];
    const rows = payments.map(p => [p.id, p.invoice, p.amount, p.method, p.date]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'payments.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Payments exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(payments, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'payments.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Payments exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Payments</h1>
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
            <th className="border p-2">Invoice</th>
            <th className="border p-2">Amount</th>
            <th className="border p-2">Method</th>
            <th className="border p-2">Date</th>
          </tr>
        </thead>
        <tbody>
          {payments.map(p => (
            <tr key={p.id}>
              <td className="border p-2">{p.id}</td>
              <td className="border p-2">{p.invoice}</td>
              <td className="border p-2">${p.amount}</td>
              <td className="border p-2">{p.method}</td>
              <td className="border p-2">{p.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
