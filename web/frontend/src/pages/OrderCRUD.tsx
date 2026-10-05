import React, { useState, useEffect, useCallback, useRef } from "react"
import { fetchWithTimeout } from '../api/fallback'
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts"

interface Order {
  id: string;
  customerName: string;
  product: string;
  quantity: number;
  total: number;
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  createdAt: string;
}

interface OrderItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

interface OrderFormData {
  customer_id: number;
  items: OrderItem[];
  status: Order['status'];
  notes: string;
  customerName: string;
  product: string;
  quantity: number;
  total: number;
}

const API_BASE = '/api/orders';
const PAGE_SIZE = 10;

const emptyForm: OrderFormData = {
  customer_id: 0,
  items: [],
  status: 'pending',
  notes: '',
  customerName: '',
  product: '',
  quantity: 0,
  total: 0,
};

const OrderCRUD: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [formData, setFormData] = useState<OrderFormData>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sortedData: sortedFilteredOrders, requestSort, getSortIndicator } = useSort(filteredOrders);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(API_BASE, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Order[] = await res.json();
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  useEffect(() => {
    let result = orders;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (o) =>
          o.customerName.toLowerCase().includes(term) ||
          o.product.toLowerCase().includes(term) ||
          o.id.toLowerCase().includes(term)
      );
    }
    if (statusFilter !== 'all') {
      result = result.filter((o) => o.status === statusFilter);
    }
    setFilteredOrders(result);
    setTotalPages(Math.max(1, Math.ceil(result.length / PAGE_SIZE)));
    setCurrentPage(1);
  }, [orders, searchTerm, statusFilter]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'customer_id' ? Number(value) : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? 'PUT' : 'POST';
      const res = await fetchWithTimeout(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchOrders();
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save order');
    }
  };

  const handleEdit = (order: Order) => {
    setEditingId(order.id);
    setFormData({
      customer_id: 0,
      items: [],
      status: order.status,
      notes: '',
      customerName: order.customerName,
      product: order.product,
      quantity: order.quantity,
      total: order.total,
    });
    setIsFormOpen(true);
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetchWithTimeout(`${API_BASE}/${id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirmId(null);
      await fetchOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete order');
    }
  };

  const resetForm = () => {
    setFormData(emptyForm);
    setEditingId(null);
    setIsFormOpen(false);
  };

  const statusColors: Record<Order['status'], string> = {
    pending: 'bg-yellow-900/50 text-yellow-200',
    processing: 'bg-blue-900/50 text-blue-200',
    shipped: 'bg-purple-900/50 text-purple-200',
    delivered: 'bg-green-900/50 text-green-200',
    cancelled: 'bg-red-900/50 text-red-200',
  };

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: () => setIsFormOpen(true), onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(orders as unknown as Record<string, unknown>[], "order_export.csv"), onDelete: () => { if (orders.length > 0) setDeleteConfirmId(orders[0].id); }, onClose: resetForm });

  return (
    <div className="p-6 max-w-7xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Order Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-800 text-red-200 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex flex-wrap gap-4 mb-6">
        <input
          type="text"
          placeholder="Search orders..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px] bg-gray-800 text-gray-100"
         ref={searchRef}/>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100"
        >
          <option value="all">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="shipped">Shipped</option>
          <option value="delivered">Delivered</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button
          onClick={() => setIsFormOpen(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Order
        </button>
      </div>

      {/* Form Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">
              {editingId ? 'Edit Order' : 'Create Order'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                name="customerName"
                placeholder="Customer Name"
                value={formData.customerName}
                onChange={handleInputChange}
                required
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              />
              <input
                name="product"
                placeholder="Product"
                value={formData.product}
                onChange={handleInputChange}
                required
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              />
              <input
                name="quantity"
                type="number"
                min="1"
                placeholder="Quantity"
                value={formData.quantity}
                onChange={handleInputChange}
                required
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              />
              <input
                name="total"
                type="number"
                min="0"
                step="0.01"
                placeholder="Total"
                value={formData.total}
                onChange={handleInputChange}
                required
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              />
              <select
                name="status"
                value={formData.status}
                onChange={handleInputChange}
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              >
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="shipped">Shipped</option>
                <option value="delivered">Delivered</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2 border border-gray-700 rounded hover:bg-gray-700 bg-gray-800 text-gray-100"
                title="Escape to close">Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  {editingId ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Orders Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-900">
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('customerName')}>Customer{getSortIndicator('customerName')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('product')}>Product{getSortIndicator('product')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('quantity')}>Qty{getSortIndicator('quantity')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('total')}>Total{getSortIndicator('total')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left cursor-pointer select-none text-gray-300" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
              <th className="border border-gray-700 px-4 py-2 text-left text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="border px-4 py-8 text-center text-gray-400">
                  Loading...
                </td>
              </tr>
            ) : sortedFilteredOrders.length === 0 ? (
              <tr>
                <td colSpan={7} className="border px-4 py-8 text-center text-gray-400">
                  No orders found
                </td>
              </tr>
            ) : (
              sortedFilteredOrders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-900">
                  <td className="border border-gray-700 px-4 py-2 text-sm text-gray-300">{order.id.slice(0, 8)}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-300">{order.customerName}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-300">{order.product}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-300">{order.quantity}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-300">${order.total.toFixed(2)}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-300">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${statusColors[order.status]}`}
                    >
                      {order.status}
                    </span>
                  </td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-300">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(order)}
                        className="text-blue-400 hover:underline text-sm"
                      >
                        Edit
                      </button>
                      {deleteConfirmId === order.id ? (
                        <>
                          <button
                            onClick={() => handleDelete(order.id)}
                            className="text-red-400 hover:underline text-sm font-medium"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="text-gray-400 hover:underline text-sm"
                          title="Escape to close">Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(order.id)}
                          className="text-red-400 hover:underline text-sm"
                        title="Delete key to delete">Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 hover:bg-gray-700 bg-gray-800 text-gray-100"
          >
            Previous
          </button>
          <span className="text-sm">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 hover:bg-gray-700 bg-gray-800 text-gray-100"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default OrderCRUD;