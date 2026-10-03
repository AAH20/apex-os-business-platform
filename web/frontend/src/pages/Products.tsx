import { useState } from 'react';

interface Product {
  id: number;
  name: string;
  sku: string;
  price: number;
  stock: number;
  category: string;
}

const mockProducts: Product[] = [
  { id: 1, name: 'Widget A', sku: 'WID-001', price: 29.99, stock: 150, category: 'Widgets' },
  { id: 2, name: 'Gadget B', sku: 'GAD-002', price: 49.99, stock: 75, category: 'Gadgets' },
  { id: 3, name: 'Tool C', sku: 'TOL-003', price: 19.99, stock: 200, category: 'Tools' },
];

export default function Products() {
  const [products] = useState<Product[]>(mockProducts);
  const [exportMessage, setExportMessage] = useState('');

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'SKU', 'Price', 'Stock', 'Category'];
    const rows = products.map(p => [p.id, p.name, p.sku, p.price, p.stock, p.category]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'products.csv';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Products exported as CSV successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(products, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'products.json';
    a.click();
    URL.revokeObjectURL(url);
    setExportMessage('Products exported as JSON successfully!');
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Products</h1>
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
            <th className="border p-2">SKU</th>
            <th className="border p-2">Price</th>
            <th className="border p-2">Stock</th>
            <th className="border p-2">Category</th>
          </tr>
        </thead>
        <tbody>
          {products.map(p => (
            <tr key={p.id}>
              <td className="border p-2">{p.id}</td>
              <td className="border p-2">{p.name}</td>
              <td className="border p-2">{p.sku}</td>
              <td className="border p-2">${p.price}</td>
              <td className="border p-2">{p.stock}</td>
              <td className="border p-2">{p.category}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
