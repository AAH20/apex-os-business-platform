import React, { useState, useRef, useEffect } from 'react';
import { Users, Search, Download } from 'lucide-react';
import { customerApi, type Customer } from '../api/client';

const CustomerManagement: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filteredCustomers, setFilteredCustomers] = useState<Customer[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [formData, setFormData] = useState({ name: '', email: '', phone: '', company: '' });
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
      setFilteredCustomers(customers);
    } else {
      setFilteredCustomers(customerApi.search(searchQuery, ['name', 'email', 'company']));
    }
  }, [customers, searchQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingCustomer) {
      customerApi.update(editingCustomer.id, formData);
      setAnnouncement(`Customer "${formData.name}" updated successfully`);
    } else {
      customerApi.create(formData);
      setAnnouncement(`Customer "${formData.name}" added successfully`);
    }
    setCustomers(customerApi.getAll());
    closeModal();
  };

  const handleEdit = (customer: Customer) => {
    setEditingCustomer(customer);
    setFormData({ name: customer.name, email: customer.email, phone: customer.phone, company: customer.company });
    setIsModalOpen(true);
  };

  const handleDelete = (customer: Customer) => {
    customerApi.delete(customer.id);
    setCustomers(customerApi.getAll());
    setAnnouncement(`Customer "${customer.name}" removed`);
  };

  const handleExport = () => {
    const csv = customerApi.export(
      ['id', 'name', 'email', 'phone', 'company'],
      ['ID', 'Name', 'Email', 'Phone', 'Company']
    );
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'customers.csv';
    a.click();
    URL.revokeObjectURL(url);
    setAnnouncement('Customers exported to CSV');
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingCustomer(null);
    setFormData({ name: '', email: '', phone: '', company: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) closeModal();
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4 text-gray-100">Customer Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setIsModalOpen(true)}
          aria-label="Add new customer"
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
        >
          + Add Customer
        </button>
        <button
          onClick={handleExport}
          aria-label="Export customers to CSV"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 flex items-center gap-2"
        >
          <Download size={16} /> Export CSV
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <Search size={16} className="text-gray-400" />
          <input
            type="text"
            placeholder="Search customers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search customers"
            className="border border-gray-600 rounded px-3 py-2 bg-gray-800 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </div>
      </div>

      {filteredCustomers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-800 rounded-lg">
          <Users className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-gray-100 text-lg mb-4">
            {searchQuery ? 'No customers match your search.' : 'No customers found. Add your first customer!'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setIsModalOpen(true)}
              aria-label="Add customer"
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
            >
              Add Customer
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Customers list" className="min-w-full border-collapse border border-gray-700">
            <thead>
              <tr>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">ID</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Name</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Email</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Phone</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Company</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCustomers.map((customer) => (
                <tr key={customer.id}>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{customer.id}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{customer.name}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{customer.email}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{customer.phone}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{customer.company}</td>
                  <td className="border border-gray-700 px-4 py-2">
                    <button
                      onClick={() => handleEdit(customer)}
                      aria-label={`Edit customer ${customer.name}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >Edit</button>
                    <button
                      onClick={() => handleDelete(customer)}
                      aria-label={`Delete customer ${customer.name}`}
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
          role="dialog" aria-modal="true" aria-labelledby="customer-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-gray-800 p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="customer-modal-title" className="text-xl font-bold mb-4 text-gray-100">
              {editingCustomer ? 'Edit Customer' : 'Add New Customer'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="customer-name" className="block text-sm font-medium mb-1 text-gray-100">Name</label>
                <input ref={firstInputRef} id="customer-name" type="text" value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="customer-email" className="block text-sm font-medium mb-1 text-gray-100">Email</label>
                <input id="customer-email" type="email" value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="customer-phone" className="block text-sm font-medium mb-1 text-gray-100">Phone</label>
                <input id="customer-phone" type="tel" value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="mb-4">
                <label htmlFor="customer-company" className="block text-sm font-medium mb-1 text-gray-100">Company</label>
                <input id="customer-company" type="text" value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500" />
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={closeModal}
                  className="bg-gray-600 text-gray-100 px-4 py-2 rounded hover:bg-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500">Cancel</button>
                <button type="submit"
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500">
                  {editingCustomer ? 'Save' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomerManagement;
