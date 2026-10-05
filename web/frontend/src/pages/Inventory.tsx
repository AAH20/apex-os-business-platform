import { useState } from 'react';

interface InventoryItem {
  id: number;
  product: string;
  warehouse: string;
  quantity: number;
  reorderLevel: number;
}

const mockInventory: InventoryItem[] = [
  { id: 1, product: 'Widget A', warehouse: 'Main', quantity: 150, reorderLevel: 50 },
  { id: 2, product: 'Gadget B', warehouse: 'East', quantity: 75, reorderLevel: 30 },
  { id: 3, product: 'Tool C', warehouse: 'West', quantity: 200, reorderLevel: 40 },
];

export default function Inventory() {
  const [inventory] = useState<InventoryItem[]>(mockInventory);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Product', 'Warehouse', 'Quantity', 'Reorder Level'];
    const rows = inventory.map(i => [i.id, i.product, i.warehouse, i.quantity, i.reorderLevel]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'inventory.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Inventory exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(inventory, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'inventory.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Inventory exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Inventory</h1>
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
            <th className="border p-2">Product</th>
            <th className="border p-2">Warehouse</th>
            <th className="border p-2">Quantity</th>
            <th className="border p-2">Reorder Level</th>
          </tr>
        </thead>
        <tbody>
          {inventory.map(i => (
            <tr key={i.id}>
              <td className="border p-2">{i.id}</td>
              <td className="border p-2">{i.product}</td>
              <td className="border p-2">{i.warehouse}</td>
              <td className="border p-2">{i.quantity}</td>
              <td className="border p-2">{i.reorderLevel}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
