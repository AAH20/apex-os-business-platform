import React, { useState, useRef, useEffect } from 'react';
import { ShoppingCart, Search, Download } from 'lucide-react';
import { orderApi, type Order } from '../api/client';

const OrderManagement: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [formData, setFormData] = useState({ customerName: '', productName: '', quantity: 1, total: 0, status: 'Pending', date: '' });
  const [searchQuery, setSearchQuery] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isModalOpen && firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, [isModalOpen]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredOrders(orders);
    } else {
      setFilteredOrders(orderApi.search(searchQuery, ['customerName', 'productName', 'status']));
    }
  }, [orders, searchQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingOrder) {
      orderApi.update(editingOrder.id, formData);
      setAnnouncement(`Order for "${formData.customerName}" updated successfully`);
    } else {
      orderApi.create({ ...formData, date: formData.date || new Date().toISOString().split('T')[0] });
      setAnnouncement(`Order for "${formData.customerName}" created successfully`);
    }
    setOrders(orderApi.getAll());
    closeModal();
  };

  const handleEdit = (order: Order) => {
    setEditingOrder(order);
    setFormData({ customerName: order.customerName, productName: order.productName, quantity: order.quantity, total: order.total, status: order.status, date: order.date });
    setIsModalOpen(true);
  };

  const handleDelete = (order: Order) => {
    orderApi.delete(order.id);
    setOrders(orderApi.getAll());
    setAnnouncement(`Order for "${order.customerName}" deleted`);
  };

  const handleExport = () => {
    const csv = orderApi.export(
      ['id', 'customerName', 'productName', 'quantity', 'total', 'status', 'date'],
      ['ID', 'Customer', 'Product', 'Qty', 'Total', 'Status', 'Date']
    );
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'orders.csv';
    a.click();
    URL.revokeObjectURL(url);
    setAnnouncement('Orders exported to CSV');
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingOrder(null);
    setFormData({ customerName: '', productName: '', quantity: 1, total: 0, status: 'Pending', date: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) closeModal();
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4 text-gray-100">Order Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setIsModalOpen(true)}
          aria-label="Create new order"
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
        >
          + Create Order
        </button>
        <button
          onClick={handleExport}
          aria-label="Export orders to CSV"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 flex items-center gap-2"
        >
          <Download size={16} /> Export CSV
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <Search size={16} className="text-gray-400" />
          <input
            type="text"
            placeholder="Search orders..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search orders"
            className="border border-gray-600 rounded px-3 py-2 bg-gray-800 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </div>
      </div>

      {filteredOrders.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-800 rounded-lg">
          <ShoppingCart className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-gray-100 text-lg mb-4">
            {searchQuery ? 'No orders match your search.' : 'No orders found. Create your first order!'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setIsModalOpen(true)}
              aria-label="Create order"
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
            >
              Create Order
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Orders list" className="min-w-full border-collapse border border-gray-700">
            <thead>
              <tr>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">ID</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Customer</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Product</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Qty</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Total</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Status</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Date</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((order) => (
                <tr key={order.id}>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{order.id}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{order.customerName}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{order.productName}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{order.quantity}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">${order.total.toFixed(2)}</td>
                  <td className="border border-gray-700 px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      order.status === 'Completed' ? 'bg-green-600 text-white' :
                      order.status === 'Shipped' ? 'bg-blue-600 text-white' :
                      order.status === 'Cancelled' ? 'bg-red-600 text-white' :
                      'bg-yellow-600 text-white'
                    }`}>{order.status}</span>
                  </td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{order.date}</td>
                  <td className="border border-gray-700 px-4 py-2">
                    <button
                      onClick={() => handleEdit(order)}
                      aria-label={`Edit order ${order.id}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >Edit</button>
                    <button
                      onClick={() => handleDelete(order)}
                      aria-label={`Delete order ${order.id}`}
                      className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                    >Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isModalOpen && (
        <div
          role="dialog" aria-modal="true" aria-labelledby="order-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-gray-800 p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="order-modal-title" className="text-xl font-bold mb-4 text-gray-100">
              {editingOrder ? 'Edit Order' : 'Create New Order'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="order-customer" className="block text-sm font-medium mb-1 text-gray-100">Customer Name</label>
                <input ref={firstInputRef} id="order-customer" type="text" value={formData.customerName}
                  onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                  required className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="order-product" className="block text-sm font-medium mb-1 text-gray-100">Product Name</label>
                <input id="order-product" type="text" value={formData.productName}
                  onChange={(e) => setFormData({ ...formData, productName: e.target.value })}
                  required className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="order-qty" className="block text-sm font-medium mb-1 text-gray-100">Quantity</label>
                <input id="order-qty" type="number" min="1" value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 1 })}
                  required className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="order-total" className="block text-sm font-medium mb-1 text-gray-100">Total ($)</label>
                <input id="order-total" type="number" step="0.01" min="0" value={formData.total}
                  onChange={(e) => setFormData({ ...formData, total: parseFloat(e.target.value) || 0 })}
                  required className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="order-status" className="block text-sm font-medium mb-1 text-gray-100">Status</label>
                <select id="order-status" value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500">
                  <option value="Pending">Pending</option>
                  <option value="Shipped">Shipped</option>
                  <option value="Completed">Completed</option>
                  <option value="Cancelled">Cancelled</option>
                </select>
              </div>
              <div className="mb-4">
                <label htmlFor="order-date" className="block text-sm font-medium mb-1 text-gray-100">Date</label>
                <input id="order-date" type="date" value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={closeModal}
                  className="bg-gray-600 text-gray-100 px-4 py-2 rounded hover:bg-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500">Cancel</button>
                <button type="submit"
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500">
                  {editingOrder ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default OrderManagement;
