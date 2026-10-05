import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string;
  company: string;
  status: "active" | "inactive";
}

interface CustomerFormData {
  name: string;
  email: string;
  phone: string;
  company: string;
  status: "active" | "inactive";
}

const emptyForm: CustomerFormData = {
  name: "",
  email: "",
  phone: "",
  company: "",
  status: "active",
};

const PAGE_SIZE = 10;

const CustomerCRUD: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filtered, setFiltered] = useState<Customer[]>([]);
  const [formData, setFormData] = useState<CustomerFormData>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const { sortedData: sortedFiltered, requestSort, getSortIndicator } = useSort(filtered);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/customers", { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Customer[] = await res.json();
      setCustomers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch customers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  useEffect(() => {
    let result = customers;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(term) ||
          c.email.toLowerCase().includes(term) ||
          c.company.toLowerCase().includes(term)
      );
    }
    if (statusFilter !== "all") {
      result = result.filter((c) => c.status === statusFilter);
    }
    setFiltered(result);
    setCurrentPage(1);
  }, [customers, searchTerm, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const openCreate = () => {
    setFormData(emptyForm);
    setEditingId(null);
    setIsFormOpen(true);
  };

  const openEdit = (customer: Customer) => {
    setFormData({
      name: customer.name,
      email: customer.email,
      phone: customer.phone,
      company: customer.company,
      status: customer.status,
    });
    setEditingId(customer.id);
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    setEditingId(null);
    setFormData(emptyForm);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId
        ? `/api/customers/${editingId}`
        : "/api/customers";
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchCustomers();
      closeForm();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      const res = await fetch(`/api/customers/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirmId(null);
      await fetchCustomers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreate, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(customers as unknown as Record<string, unknown>[], "customer_export.csv"), onDelete: () => { if (customers.length > 0) setDeleteConfirmId(customers[0].id); }, onClose: closeForm });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Customer Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-4 mb-6">
        <input
          type="text"
          placeholder="Search name, email, or company..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"
         ref={searchRef}/>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded px-3 py-2"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <button
          onClick={openCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Customer
        </button>
      </div>

      {isFormOpen && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">
            {editingId ? "Edit Customer" : "Create Customer"}
          </h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              name="name"
              placeholder="Name *"
              value={formData.name}
              onChange={handleChange}
              required
              className="border rounded px-3 py-2"
            />
            <input
              name="email"
              type="email"
              placeholder="Email *"
              value={formData.email}
              onChange={handleChange}
              required
              className="border rounded px-3 py-2"
            />
            <input
              name="phone"
              placeholder="Phone"
              value={formData.phone}
              onChange={handleChange}
              className="border rounded px-3 py-2"
            />
            <input
              name="company"
              placeholder="Company"
              value={formData.company}
              onChange={handleChange}
              className="border rounded px-3 py-2"
            />
            <select
              name="status"
              value={formData.status}
              onChange={handleChange}
              className="border rounded px-3 py-2"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <div className="flex gap-2">
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                {editingId ? "Update" : "Create"}
              </button>
              <button
                type="button"
                onClick={closeForm}
                className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600"
              > title="Escape to close" Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-gray-400">Loading customers...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border">
            <thead>
              <tr className="bg-gray-800">
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('email')}>Email{getSortIndicator('email')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('phone')}>Phone{getSortIndicator('phone')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('company')}>Company{getSortIndicator('company')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('status')}>Status{getSortIndicator('status')}</th>
                <th className="border px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedFiltered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="border px-4 py-4 text-center text-gray-400">
                    No customers found
                  </td>
                </tr>
              ) : (
                sortedFiltered.map((customer) => (
                  <tr key={customer.id} className="hover:bg-gray-800">
                    <td className="border px-4 py-2">{customer.id}</td>
                    <td className="border px-4 py-2">{customer.name}</td>
                    <td className="border px-4 py-2">{customer.email}</td>
                    <td className="border px-4 py-2">{customer.phone}</td>
                    <td className="border px-4 py-2">{customer.company}</td>
                    <td className="border px-4 py-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          customer.status === "active"
                            ? "bg-green-900/50 text-green-200"
                            : "bg-red-900/50 text-red-200"
                        }`}
                      >
                        {customer.status}
                      </span>
                    </td>
                    <td className="border px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openEdit(customer)}
                          className="bg-yellow-500 text-white px-3 py-1 rounded text-sm hover:bg-yellow-600"
                        >
                          Edit
                        </button>
                        {deleteConfirmId === customer.id ? (
                          <>
                            <button
                              onClick={() => handleDelete(customer.id)}
                              className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(null)}
                              className="bg-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-600"
                            > title="Escape to close" Cancel
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirmId(customer.id)}
                            className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600"
                          > title="Delete key to delete" Delete
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
      )}

      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-gray-400">
          Showing {paginated.length} of {filtered.length} customers
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-800"
          >
            Previous
          </button>
          <span className="px-3 py-1">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-800"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

export default CustomerCRUD;
