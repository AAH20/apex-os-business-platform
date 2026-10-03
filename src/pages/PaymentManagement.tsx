import React, { useState, useRef, useEffect } from 'react';
import { CreditCard } from 'lucide-react';

interface Payment {
  id: number;
  invoiceNumber: string;
  customerName: string;
  amount: number;
  status: 'pending' | 'paid' | 'overdue' | 'cancelled';
  dueDate: string;
}

const PaymentManagement: React.FC = () => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPayment, setEditingPayment] = useState<Payment | null>(null);
  const [formData, setFormData] = useState({ invoiceNumber: '', customerName: '', amount: 0, status: 'pending' as Payment['status'], dueDate: '' });
  const [announcement, setAnnouncement] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isModalOpen && firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, [isModalOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingPayment) {
      setPayments(payments.map(p => p.id === editingPayment.id ? { ...p, ...formData } : p));
      setAnnouncement(`Payment for invoice "${formData.invoiceNumber}" updated successfully`);
    } else {
      const newPayment: Payment = { id: Date.now(), ...formData };
      setPayments([...payments, newPayment]);
      setAnnouncement(`Payment for invoice "${formData.invoiceNumber}" created successfully`);
    }
    closeModal();
  };

  const handleEdit = (payment: Payment) => {
    setEditingPayment(payment);
    setFormData({ invoiceNumber: payment.invoiceNumber, customerName: payment.customerName, amount: payment.amount, status: payment.status, dueDate: payment.dueDate });
    setIsModalOpen(true);
  };

  const handleDelete = (payment: Payment) => {
    setPayments(payments.filter(p => p.id !== payment.id));
    setAnnouncement(`Payment for invoice "${payment.invoiceNumber}" deleted successfully`);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingPayment(null);
    setFormData({ invoiceNumber: '', customerName: '', amount: 0, status: 'pending', dueDate: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">Payment Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={() => setIsModalOpen(true)}
        aria-label="Create new payment"
        className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2 mb-4"
      >
        + New Payment
      </button>

      {payments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-900 rounded-lg">
          <CreditCard className="w-16 h-16 text-gray-100 mb-4" />
          <p className="text-gray-100 text-lg mb-4">No payments found. Create your first payment!</p>
          <button
            onClick={() => setIsModalOpen(true)}
            aria-label="Create new payment"
            className="bg-gray-800 text-gray-100 px-4 py-2 rounded hover:bg-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
          >
            Create Payment
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Payments list" className="min-w-full border-collapse border border-gray-300">
            <thead>
              <tr>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Invoice #</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Customer</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Amount</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Status</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Due Date</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
              </tr>
            </thead>
            <tbody>
              {payments.map(payment => (
                <tr key={payment.id}>
                  <td className="border border-gray-300 px-4 py-2">{payment.invoiceNumber}</td>
                  <td className="border border-gray-300 px-4 py-2">{payment.customerName}</td>
                  <td className="border border-gray-300 px-4 py-2">${payment.amount.toFixed(2)}</td>
                  <td className="border border-gray-300 px-4 py-2">{payment.status}</td>
                  <td className="border border-gray-300 px-4 py-2">{payment.dueDate}</td>
                  <td className="border border-gray-300 px-4 py-2">
                    <button
                      onClick={() => handleEdit(payment)}
                      aria-label={`Edit payment for invoice ${payment.invoiceNumber}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(payment)}
                      aria-label={`Delete payment for invoice ${payment.invoiceNumber}`}
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

      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="payment-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="payment-modal-title" className="text-xl font-bold mb-4">
              {editingPayment ? 'Edit Payment' : 'Create New Payment'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="payment-invoice" className="block text-sm font-medium mb-1">Invoice Number</label>
                <input
                  ref={firstInputRef}
                  id="payment-invoice"
                  type="text"
                  value={formData.invoiceNumber}
                  onChange={(e) => setFormData({ ...formData, invoiceNumber: e.target.value })}
                  aria-label="Invoice number"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="payment-customer" className="block text-sm font-medium mb-1">Customer Name</label>
                <input
                  id="payment-customer"
                  type="text"
                  value={formData.customerName}
                  onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                  aria-label="Customer name"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="payment-amount" className="block text-sm font-medium mb-1">Amount</label>
                <input
                  id="payment-amount"
                  type="number"
                  step="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                  aria-label="Payment amount"
                  aria-required="true"
                  required
                  min="0"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="payment-status" className="block text-sm font-medium mb-1">Status</label>
                <select
                  id="payment-status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as Payment['status'] })}
                  aria-label="Payment status"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div className="mb-4">
                <label htmlFor="payment-due-date" className="block text-sm font-medium mb-1">Due Date</label>
                <input
                  id="payment-due-date"
                  type="date"
                  value={formData.dueDate}
                  onChange={(e) => setFormData({ ...formData, dueDate: e.target.value })}
                  aria-label="Payment due date"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  aria-label="Cancel"
                  className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  aria-label={editingPayment ? 'Save payment changes' : 'Create payment'}
                  className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  {editingPayment ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaymentManagement;
