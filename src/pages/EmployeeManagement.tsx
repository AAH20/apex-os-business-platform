import React, { useState, useRef, useEffect } from 'react';
import { Users, Search, Download } from 'lucide-react';
import { employeeApi, type Employee } from '../api/client';

const EmployeeManagement: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [filteredEmployees, setFilteredEmployees] = useState<Employee[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formData, setFormData] = useState({ name: '', email: '', position: '', department: '' });
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
      setFilteredEmployees(employees);
    } else {
      setFilteredEmployees(employeeApi.search(searchQuery, ['name', 'email', 'position', 'department']));
    }
  }, [employees, searchQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingEmployee) {
      employeeApi.update(editingEmployee.id, formData);
      setAnnouncement(`Employee "${formData.name}" updated successfully`);
    } else {
      employeeApi.create(formData);
      setAnnouncement(`Employee "${formData.name}" added successfully`);
    }
    setEmployees(employeeApi.getAll());
    closeModal();
  };

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setFormData({ name: employee.name, email: employee.email, position: employee.position, department: employee.department });
    setIsModalOpen(true);
  };

  const handleDelete = (employee: Employee) => {
    employeeApi.delete(employee.id);
    setEmployees(employeeApi.getAll());
    setAnnouncement(`Employee "${employee.name}" removed`);
  };

  const handleExport = () => {
    const csv = employeeApi.export(
      ['id', 'name', 'email', 'position', 'department'],
      ['ID', 'Name', 'Email', 'Position', 'Department']
    );
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employees.csv';
    a.click();
    URL.revokeObjectURL(url);
    setAnnouncement('Employees exported to CSV');
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingEmployee(null);
    setFormData({ name: '', email: '', position: '', department: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">Employee Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setIsModalOpen(true)}
          aria-label="Add new employee"
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
        >
          + Add Employee
        </button>
        <button
          onClick={handleExport}
          aria-label="Export employees to CSV"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 flex items-center gap-2"
        >
          <Download size={16} /> Export CSV
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <Search size={16} className="text-gray-400" />
          <input
            type="text"
            placeholder="Search employees..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search employees"
            className="border border-gray-600 rounded px-3 py-2 bg-gray-800 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </div>
      </div>

      {filteredEmployees.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 bg-gray-900 rounded-lg">
          <Users className="w-16 h-16 text-gray-100 mb-4" />
          <p className="text-gray-100 text-lg mb-4">{searchQuery ? 'No employees match your search.' : 'No employees found'}</p>
          {!searchQuery && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-gray-800 text-gray-100 px-4 py-2 rounded hover:bg-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
            >
              Create Employee
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Employees list" className="min-w-full border-collapse border border-gray-300">
            <thead>
              <tr>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Name</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Email</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Position</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Department</th>
                <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredEmployees.map(employee => (
                <tr key={employee.id}>
                  <td className="border border-gray-300 px-4 py-2">{employee.name}</td>
                  <td className="border border-gray-300 px-4 py-2">{employee.email}</td>
                  <td className="border border-gray-300 px-4 py-2">{employee.position}</td>
                  <td className="border border-gray-300 px-4 py-2">{employee.department}</td>
                  <td className="border border-gray-300 px-4 py-2">
                    <button
                      onClick={() => handleEdit(employee)}
                      aria-label={`Edit employee ${employee.name}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(employee)}
                      aria-label={`Delete employee ${employee.name}`}
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
          aria-labelledby="employee-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="employee-modal-title" className="text-xl font-bold mb-4">
              {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="employee-name" className="block text-sm font-medium mb-1">Name</label>
                <input
                  ref={firstInputRef}
                  id="employee-name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  aria-label="Employee name"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="employee-email" className="block text-sm font-medium mb-1">Email</label>
                <input
                  id="employee-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  aria-label="Employee email"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="employee-position" className="block text-sm font-medium mb-1">Position</label>
                <input
                  id="employee-position"
                  type="text"
                  value={formData.position}
                  onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                  aria-label="Employee position"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="employee-department" className="block text-sm font-medium mb-1">Department</label>
                <input
                  id="employee-department"
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  aria-label="Employee department"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
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
                  aria-label={editingEmployee ? 'Save employee changes' : 'Add employee'}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                >
                  {editingEmployee ? 'Save' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmployeeManagement;
