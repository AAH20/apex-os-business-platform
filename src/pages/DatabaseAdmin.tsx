import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Trash2, Plus } from 'lucide-react';
import { productApi, orderApi, customerApi, employeeApi } from '../api/client';

interface TableInfo {
  name: string;
  key: string;
  count: number;
}

const DatabaseAdmin: React.FC = () => {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableData, setTableData] = useState<Record<string, unknown>[]>([]);
  const [announcement, setAnnouncement] = useState('');

  const refreshTables = () => {
    const info: TableInfo[] = [
      { name: 'Products', key: 'products', count: productApi.getAll().length },
      { name: 'Orders', key: 'orders', count: orderApi.getAll().length },
      { name: 'Customers', key: 'customers', count: customerApi.getAll().length },
      { name: 'Employees', key: 'employees', count: employeeApi.getAll().length },
    ];
    setTables(info);
  };

  useEffect(() => {
    refreshTables();
  }, []);

  const loadTableData = (key: string) => {
    setSelectedTable(key);
    switch (key) {
      case 'products':
        setTableData(productApi.getAll() as unknown as Record<string, unknown>[]);
        break;
      case 'orders':
        setTableData(orderApi.getAll() as unknown as Record<string, unknown>[]);
        break;
      case 'customers':
        setTableData(customerApi.getAll() as unknown as Record<string, unknown>[]);
        break;
      case 'employees':
        setTableData(employeeApi.getAll() as unknown as Record<string, unknown>[]);
        break;
    }
    setAnnouncement(`Loaded ${key} table`);
  };

  const handleDeleteRecord = (id: number) => {
    if (!selectedTable) return;
    switch (selectedTable) {
      case 'products':
        productApi.delete(id);
        break;
      case 'orders':
        orderApi.delete(id);
        break;
      case 'customers':
        customerApi.delete(id);
        break;
      case 'employees':
        employeeApi.delete(id);
        break;
    }
    loadTableData(selectedTable);
    refreshTables();
    setAnnouncement(`Record ${id} deleted from ${selectedTable}`);
  };

  const handleClearTable = () => {
    if (!selectedTable) return;
    const data = tableData;
    data.forEach((record) => {
      switch (selectedTable) {
        case 'products':
          productApi.delete(record.id as number);
          break;
        case 'orders':
          orderApi.delete(record.id as number);
          break;
        case 'customers':
          customerApi.delete(record.id as number);
          break;
        case 'employees':
          employeeApi.delete(record.id as number);
          break;
      }
    });
    loadTableData(selectedTable);
    refreshTables();
    setAnnouncement(`${selectedTable} table cleared`);
  };

  const handleAddRecord = () => {
    if (!selectedTable) return;
    switch (selectedTable) {
      case 'products':
        productApi.create({ name: 'New Product', sku: 'NEW-001', price: 0, category: 'Uncategorized' });
        break;
      case 'orders':
        orderApi.create({ customerName: 'New Customer', productName: 'New Product', quantity: 1, total: 0, status: 'Pending', date: new Date().toISOString().split('T')[0] });
        break;
      case 'customers':
        customerApi.create({ name: 'New Customer', email: 'new@example.com', phone: '', company: '' });
        break;
      case 'employees':
        employeeApi.create({ name: 'New Employee', email: 'new@example.com', position: 'Staff', department: 'General' });
        break;
    }
    loadTableData(selectedTable);
    refreshTables();
    setAnnouncement(`New record added to ${selectedTable}`);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4 flex items-center gap-2">
        <Database className="w-6 h-6" />
        Database Administration
      </h1>

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {tables.map((table) => (
          <div
            key={table.key}
            className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
              selectedTable === table.key
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => loadTableData(table.key)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && loadTableData(table.key)}
            aria-label={`Select ${table.name} table`}
          >
            <h3 className="font-semibold text-lg">{table.name}</h3>
            <p className="text-gray-600">{table.count} records</p>
          </div>
        ))}
      </div>

      {selectedTable && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold capitalize">{selectedTable} Records</h2>
            <div className="flex gap-2">
              <button
                onClick={() => loadTableData(selectedTable)}
                className="flex items-center gap-1 bg-blue-600 text-white px-3 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                aria-label="Refresh table data"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              <button
                onClick={handleAddRecord}
                className="flex items-center gap-1 bg-green-600 text-white px-3 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                aria-label="Add new record"
              >
                <Plus className="w-4 h-4" />
                Add Record
              </button>
              <button
                onClick={handleClearTable}
                className="flex items-center gap-1 bg-red-600 text-white px-3 py-2 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                aria-label="Clear all records"
              >
                <Trash2 className="w-4 h-4" />
                Clear Table
              </button>
            </div>
          </div>

          {tableData.length === 0 ? (
            <p className="text-gray-500 py-8 text-center">No records in this table</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse border border-gray-300" role="table" aria-label={`${selectedTable} records`}>
                <thead>
                  <tr>
                    {Object.keys(tableData[0]).map((key) => (
                      <th key={key} className="border border-gray-300 px-4 py-2 bg-gray-100 text-left">
                        {key}
                      </th>
                    ))}
                    <th className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tableData.map((record, idx) => (
                    <tr key={(record.id as number) || idx}>
                      {Object.values(record).map((value, vIdx) => (
                        <td key={vIdx} className="border border-gray-300 px-4 py-2">
                          {String(value ?? '')}
                        </td>
                      ))}
                      <td className="border border-gray-300 px-4 py-2">
                        <button
                          onClick={() => handleDeleteRecord(record.id as number)}
                          aria-label={`Delete record ${record.id}`}
                          className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DatabaseAdmin;
