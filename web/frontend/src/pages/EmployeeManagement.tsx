import React, { useState, useEffect, useCallback } from "react";

interface Employee {
  id: number;
  name: string;
  email: string;
  department: string;
  role: string;
}

interface EmployeeFormData {
  name: string;
  email: string;
  department: string;
  role: string;
}

const EMPTY_FORM: EmployeeFormData = { name: "", email: "", department: "", role: "" };
const PAGE_SIZE = 10;

export default function EmployeeManagement() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formData, setFormData] = useState<EmployeeFormData>(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState<Employee | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/employees/");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const list: Employee[] = Array.isArray(data) ? data : data.items || [];
      setEmployees(list);
    } catch (e: any) {
      setError(e.message || "Failed to fetch employees");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const departments = Array.from(new Set(employees.map((e) => e.department).filter(Boolean))).sort();

  const filtered = employees.filter((e) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      e.name.toLowerCase().includes(q) ||
      e.email.toLowerCase().includes(q) ||
      e.role.toLowerCase().includes(q);
    const matchesDept = !departmentFilter || e.department === departmentFilter;
    return matchesSearch && matchesDept;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function openCreate() {
    setEditingEmployee(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(emp: Employee) {
    setEditingEmployee(emp);
    setFormData({ name: emp.name, email: emp.email, department: emp.department, role: emp.role });
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const url = editingEmployee ? `/api/employees/${editingEmployee.id}/` : "/api/employees/";
      const method = editingEmployee ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchEmployees();
      setShowForm(false);
      setEditingEmployee(null);
      setFormData(EMPTY_FORM);
    } catch (e: any) {
      setError(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleteConfirm) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/employees/${deleteConfirm.id}/`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      await fetchEmployees();
    } catch (e: any) {
      setError(e.message || "Delete failed");
    } finally {
      setSaving(false);
    }
  }

  function handleSearchChange(val: string) {
    setSearch(val);
    setPage(1);
  }

  function handleDeptChange(val: string) {
    setDepartmentFilter(val);
    setPage(1);
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Employee Management</h1>
          <button
            onClick={openCreate}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            + Add Employee
          </button>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <input
            type="text"
            placeholder="Search by name, email, or role..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <select
            value={departmentFilter}
            onChange={(e) => handleDeptChange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading employees...</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-700">
              <table className="w-full text-left">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-sm font-semibold text-gray-300">Name</th>
                    <th className="px-4 py-3 text-sm font-semibold text-gray-300">Email</th>
                    <th className="px-4 py-3 text-sm font-semibold text-gray-300">Department</th>
                    <th className="px-4 py-3 text-sm font-semibold text-gray-300">Role</th>
                    <th className="px-4 py-3 text-sm font-semibold text-gray-300 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {paginated.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        No employees found
                      </td>
                    </tr>
                  ) : (
                    paginated.map((emp) => (
                      <tr key={emp.id} className="hover:bg-gray-800/50 transition-colors">
                        <td className="px-4 py-3">{emp.name}</td>
                        <td className="px-4 py-3 text-gray-400">{emp.email}</td>
                        <td className="px-4 py-3">
                          <span className="bg-gray-700 text-gray-300 px-2 py-1 rounded text-xs">
                            {emp.department}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-400">{emp.role}</td>
                        <td className="px-4 py-3 text-right space-x-2">
                          <button
                            onClick={() => openEdit(emp)}
                            className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(emp)}
                            className="text-red-400 hover:text-red-300 text-sm font-medium"
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

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-sm text-gray-400">
                  Page {safePage} of {totalPages} ({filtered.length} employees)
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={safePage <= 1}
                    className="bg-gray-800 border border-gray-700 px-3 py-1 rounded text-sm disabled:opacity-40 hover:bg-gray-700 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={safePage >= totalPages}
                    className="bg-gray-800 border border-gray-700 px-3 py-1 rounded text-sm disabled:opacity-40 hover:bg-gray-700 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700">
              <h2 className="text-xl font-bold mb-4">
                {editingEmployee ? "Edit Employee" : "Add Employee"}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Email</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Department</label>
                  <input
                    type="text"
                    required
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Role</label>
                  <input
                    type="text"
                    required
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2 rounded-lg font-medium transition-colors"
                  >
                    {saving ? "Saving..." : editingEmployee ? "Update" : "Create"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowForm(false);
                      setEditingEmployee(null);
                      setFormData(EMPTY_FORM);
                    }}
                    className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 py-2 rounded-lg font-medium transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm border border-gray-700">
              <h2 className="text-xl font-bold mb-2">Delete Employee</h2>
              <p className="text-gray-400 mb-6">
                Are you sure you want to delete <strong className="text-gray-200">{deleteConfirm.name}</strong>? This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDelete}
                  disabled={saving}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white py-2 rounded-lg font-medium transition-colors"
                >
                  {saving ? "Deleting..." : "Delete"}
                </button>
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 py-2 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
