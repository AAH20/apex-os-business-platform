import React, { useState, useRef, useEffect } from 'react';
import { FileText } from 'lucide-react';

interface Invoice {
  id: number;
  invoiceNumber: string;
  customerName: string;
  amount: number;
  status: 'draft' | 'sent' | 'paid' | 'overdue';
  dueDate: string;
}

const InvoiceManagement: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
  const [formData, setFormData] = useState({ invoiceNumber: '', customerName: '', amount: 0, status: 'draft' as Invoice['status'], dueDate: '' });
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
    if (editingInvoice) {
      setInvoices(invoices.map(inv => inv.id === editingInvoice.id ? { ...inv, ...formData } : inv));
      setAnnouncement(`Invoice "${formData.invoiceNumber}" updated successfully`);
    } else {
      const newInvoice: Invoice = { id: Date.now(), ...formData };
      setInvoices([...invoices, newInvoice]);
      setAnnouncement(`Invoice "${formData.invoiceNumber}" created successfully`);
    }
    closeModal();
  };

  const handleEdit = (invoice: Invoice) => {
    setEditingInvoice(invoice);
    setFormData({ invoiceNumber: invoice.invoiceNumber, customerName: invoice.customerName, amount: invoice.amount, status: invoice.status, dueDate: invoice.dueDate });
    setIsModalOpen(true);
  };

  const handleDelete = (invoice: Invoice) => {
    setInvoices(invoices.filter(inv => inv.id !== invoice.id));
    setAnnouncement(`Invoice "${invoice.invoiceNumber}" deleted successfully`);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingInvoice(null);
    setFormData({ invoiceNumber: '', customerName: '', amount: 0, status: 'draft', dueDate: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">Invoice Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={() => setIsModalOpen(true)}
        aria-label="Create new invoice"
        className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2 mb-4"
      >
        + New Invoice
      </button>

      {invoices.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-900 rounded-lg">
          <FileText className="w-16 h-16 text-gray-100 mb-4" />
          <p className="text-gray-100 text-lg mb-4">No invoices found. Create your first invoice!</p>
          <button
            onClick={() => setIsModalOpen(true)}
            aria-label="Create new invoice"
            className="bg-gray-800 text-gray-100 px-4 py-2 rounded hover:bg-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
          >
            Create Invoice
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Invoices list" className="min-w-full border-collapse border border-gray-300">
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
              {invoices.map(invoice => (
                <tr key={invoice.id}>
                  <td className="border border-gray-300 px-4 py-2">{invoice.invoiceNumber}</td>
                  <td className="border border-gray-300 px-4 py-2">{invoice.customerName}</td>
                  <td className="border border-gray-300 px-4 py-2">${invoice.amount.toFixed(2)}</td>
                  <td className="border border-gray-300 px-4 py-2">{invoice.status}</td>
                  <td className="border border-gray-300 px-4 py-2">{invoice.dueDate}</td>
                  <td className="border border-gray-300 px-4 py-2">
                    <button
                      onClick={() => handleEdit(invoice)}
                      aria-label={`Edit invoice ${invoice.invoiceNumber}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(invoice)}
                      aria-label={`Delete invoice ${invoice.invoiceNumber}`}
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
          aria-labelledby="invoice-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="invoice-modal-title" className="text-xl font-bold mb-4">
              {editingInvoice ? 'Edit Invoice' : 'Create New Invoice'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="invoice-number" className="block text-sm font-medium mb-1">Invoice Number</label>
                <input
                  ref={firstInputRef}
                  id="invoice-number"
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
                <label htmlFor="invoice-customer" className="block text-sm font-medium mb-1">Customer Name</label>
                <input
                  id="invoice-customer"
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
                <label htmlFor="invoice-amount" className="block text-sm font-medium mb-1">Amount</label>
                <input
                  id="invoice-amount"
                  type="number"
                  step="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                  aria-label="Invoice amount"
                  aria-required="true"
                  required
                  min="0"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="invoice-status" className="block text-sm font-medium mb-1">Status</label>
                <select
                  id="invoice-status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as Invoice['status'] })}
                  aria-label="Invoice status"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                </select>
              </div>
              <div className="mb-4">
                <label htmlFor="invoice-due-date" className="block text-sm font-medium mb-1">Due Date</label>
                <input
                  id="invoice-due-date"
                  type="date"
                  value={formData.dueDate}
                  onChange={(e) => setFormData({ ...formData, dueDate: e.target.value })}
                  aria-label="Invoice due date"
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
                  aria-label={editingInvoice ? 'Save invoice changes' : 'Create invoice'}
                  className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  {editingInvoice ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvoiceManagement;
