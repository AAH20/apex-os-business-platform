import React, { useState, useRef, useEffect } from 'react';
import { Package } from 'lucide-react';

interface Employee {
  id: number;
  name: string;
  email: string;
  position: string;
  department: string;
}

const EmployeeManagement: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formData, setFormData] = useState({ name: '', email: '', position: '', department: '' });
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
    if (editingEmployee) {
      setEmployees(employees.map(emp => emp.id === editingEmployee.id ? { ...emp, ...formData } : emp));
      setAnnouncement(`Employee "${formData.name}" updated successfully`);
    } else {
      const newEmployee: Employee = { id: Date.now(), ...formData };
      setEmployees([...employees, newEmployee]);
      setAnnouncement(`Employee "${formData.name}" added successfully`);
    }
    closeModal();
  };

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setFormData({ name: employee.name, email: employee.email, position: employee.position, department: employee.department });
    setIsModalOpen(true);
  };

  const handleDelete = (employee: Employee) => {
    setEmployees(employees.filter(emp => emp.id !== employee.id));
    setAnnouncement(`Employee "${employee.name}" removed`);
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

      <button
        onClick={() => setIsModalOpen(true)}
        aria-label="Add new employee"
        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2 mb-4"
      >
        + Add Employee
      </button>

      {employees.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 bg-gray-900 rounded-lg">
          <Package className="w-16 h-16 text-gray-100 mb-4" />
          <p className="text-gray-100 text-lg mb-4">No employees found</p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-gray-800 text-gray-100 px-4 py-2 rounded hover:bg-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
          >
            Create Employee
          </button>
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
              {employees.map(employee => (
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
