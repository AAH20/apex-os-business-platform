import React, { useState, useEffect, useCallback } from 'react';

interface OrderItem {
  product_id: number;
  quantity: number;
  price: number;
}

interface Order {
  id: number;
  customer_id: number;
  items: OrderItem[];
  status: string;
  notes: string;
  total: number;
  created_at: string;
}

interface OrderFormData {
  customer_id: number;
  items: OrderItem[];
  status: string;
  notes: string;
}

const STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'];
const ITEMS_PER_PAGE = 10;

const emptyFormData: OrderFormData = {
  customer_id: 0,
  items: [{ product_id: 0, quantity: 1, price: 0 }],
  status: 'pending',
  notes: '',
};

const OrderManagement: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [formData, setFormData] = useState<OrderFormData>(emptyFormData);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingOrderId, setDeletingOrderId] = useState<number | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);
      params.set('page', String(currentPage));
      params.set('per_page', String(ITEMS_PER_PAGE));

      const res = await fetch(`/api/orders/?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : data.items || [];
      setOrders(items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, currentPage]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const openCreateForm = () => {
    setEditingOrder(null);
    setFormData(emptyFormData);
    setShowForm(true);
  };

  const openEditForm = (order: Order) => {
    setEditingOrder(order);
    setFormData({
      customer_id: order.customer_id,
      items: order.items.length > 0 ? [...order.items] : [{ product_id: 0, quantity: 1, price: 0 }],
      status: order.status,
      notes: order.notes || '',
    });
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingOrder(null);
    setFormData(emptyFormData);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingOrder ? `/api/orders/${editingOrder.id}/` : '/api/orders/';
      const method = editingOrder ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      closeForm();
      fetchOrders();
    } catch (err: any) {
      setError(err.message || 'Failed to save order');
    }
  };

  const handleDelete = async () => {
    if (!deletingOrderId) return;
    setError(null);
    try {
      const res = await fetch(`/api/orders/${deletingOrderId}/`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(false);
      setDeletingOrderId(null);
      fetchOrders();
    } catch (err: any) {
      setError(err.message || 'Failed to delete order');
    }
  };

  const addItem = () => {
    setFormData({
      ...formData,
      items: [...formData.items, { product_id: 0, quantity: 1, price: 0 }],
    });
  };

  const removeItem = (index: number) => {
    const items = formData.items.filter((_, i) => i !== index);
    setFormData({ ...formData, items });
  };

  const updateItem = (index: number, field: keyof OrderItem, value: number) => {
    const items = [...formData.items];
    items[index] = { ...items[index], [field]: value };
    setFormData({ ...formData, items });
  };

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      !search ||
      order.id.toString().includes(search) ||
      order.customer_id.toString().includes(search) ||
      (order.notes && order.notes.toLowerCase().includes(search.toLowerCase()));
    const matchesStatus = !statusFilter || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Order Management</h1>
          <button
            onClick={openCreateForm}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
            aria-label="Create new order"
          >
            + New Order
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm" role="alert" aria-live="assertive">
            {error}
          </div>
        )}

        <div className="flex gap-4 mb-4">
          <input
            type="text"
            placeholder="Search orders..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Search orders"
          />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Filter by status"
          >
            <option value="">All Statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>

        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">Customer</th>
                <th className="px-4 py-3 text-left">Items</th>
                <th className="px-4 py-3 text-left">Total</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400" role="status" aria-live="polite">Loading...</td></tr>
              ) : filteredOrders.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400" aria-live="polite">No orders found</td></tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr key={order.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="px-4 py-3">#{order.id}</td>
                    <td className="px-4 py-3">{order.customer_id}</td>
                    <td className="px-4 py-3">{order.items?.length || 0}</td>
                    <td className="px-4 py-3">${order.total?.toFixed(2) || '0.00'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        order.status === 'delivered' ? 'bg-green-900 text-green-200' :
                        order.status === 'cancelled' ? 'bg-red-900 text-red-200' :
                        order.status === 'shipped' ? 'bg-blue-900 text-blue-200' :
                        order.status === 'processing' ? 'bg-yellow-900 text-yellow-200' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">{new Date(order.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => openEditForm(order)}
                        className="mr-2 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label={`Edit order ${order.id}`}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => { setDeletingOrderId(order.id); setShowDeleteConfirm(true); }}
                        className="px-2 py-1 bg-red-800 hover:bg-red-700 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label={`Delete order ${order.id}`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-gray-400">
            Showing {filteredOrders.length} orders
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              aria-label="Go to previous page"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm">Page {currentPage}</span>
            <button
              onClick={() => setCurrentPage((p) => p + 1)}
              disabled={filteredOrders.length < ITEMS_PER_PAGE}
              className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              aria-label="Go to next page"
            >
              Next
            </button>
          </div>
        </div>

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label={editingOrder ? 'Edit order' : 'Create order'}>
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">
                {editingOrder ? 'Edit Order' : 'Create Order'}
              </h2>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm mb-1">Customer ID</label>
                  <input
                    type="number"
                    value={formData.customer_id || ''}
                    onChange={(e) => setFormData({ ...formData, customer_id: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    required
                    aria-label="Customer ID"
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    aria-label="Order status"
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                </div>

                <div className="mb-4">
                  <label className="block text-sm mb-1">Notes</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    rows={3}
                    aria-label="Order notes"
                  />
                </div>

                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm">Items</label>
                    <button type="button" onClick={addItem} className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label="Add item to order">
                      + Add Item
                    </button>
                  </div>
                  {formData.items.map((item, idx) => (
                    <div key={idx} className="flex gap-2 mb-2">
                      <input
                        type="number"
                        placeholder="Product ID"
                        value={item.product_id || ''}
                        onChange={(e) => updateItem(idx, 'product_id', parseInt(e.target.value) || 0)}
                        className="flex-1 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label={`Product ID for item ${idx + 1}`}
                      />
                      <input
                        type="number"
                        placeholder="Qty"
                        value={item.quantity || ''}
                        onChange={(e) => updateItem(idx, 'quantity', parseInt(e.target.value) || 0)}
                        className="w-16 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label={`Quantity for item ${idx + 1}`}
                      />
                      <input
                        type="number"
                        placeholder="Price"
                        value={item.price || ''}
                        onChange={(e) => updateItem(idx, 'price', parseFloat(e.target.value) || 0)}
                        className="w-20 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                        aria-label={`Price for item ${idx + 1}`}
                      />
                      <button type="button" onClick={() => removeItem(idx)} className="px-2 py-1 bg-red-800 hover:bg-red-700 rounded text-xs focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label={`Remove item ${idx + 1}`}>
                        X
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex gap-3 justify-end">
                  <button type="button" onClick={closeForm} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label="Cancel order form">
                    Cancel
                  </button>
                  <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label={editingOrder ? 'Update order' : 'Create order'}>
                    {editingOrder ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Confirm delete order">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm">
              <h2 className="text-lg font-bold mb-2">Confirm Delete</h2>
              <p className="text-sm text-gray-300 mb-4">
                Are you sure you want to delete order #{deletingOrderId}? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => { setShowDeleteConfirm(false); setDeletingOrderId(null); }}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                  aria-label="Cancel delete"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                  aria-label={`Confirm delete order ${deletingOrderId}`}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrderManagement;
