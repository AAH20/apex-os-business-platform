import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Employee {
  id: number;
  name: string;
  email: string;
  role: string;
  department: string;
  salary: number;
}

interface EmployeeFormData {
  name: string;
  email: string;
  role: string;
  department: string;
  salary: number;
}

const EMPTY_FORM: EmployeeFormData = {
  name: "",
  email: "",
  role: "",
  department: "",
  salary: 0,
};

const API_BASE = "/api/employees";
const PAGE_SIZE = 10;

const fetchEmployees = async (
  page: number,
  search: string
): Promise<{ employees: Employee[]; total: number }> => {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(PAGE_SIZE),
    ...(search && { search }),
  });
  const res = await fetch(`${API_BASE}?${params}`);
  if (!res.ok) throw new Error("Failed to fetch employees");
  return res.json();
};

const createEmployee = async (data: EmployeeFormData): Promise<Employee> => {
  const res = await fetch(API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create employee");
  return res.json();
};

const updateEmployee = async (
  id: number,
  data: EmployeeFormData
): Promise<Employee> => {
  const res = await fetch(`${API_BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update employee");
  return res.json();
};

const deleteEmployee = async (id: number): Promise<void> => {
  const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete employee");
};

const EmployeeForm: React.FC<{
  initialData: EmployeeFormData;
  onSubmit: (data: EmployeeFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}> = ({ initialData, onSubmit, onCancel, submitLabel }) => {
  const [form, setForm] = useState<EmployeeFormData>(initialData);
  const [errors, setErrors] = useState<Partial<Record<keyof EmployeeFormData, string>>>({});

  const validate = (): boolean => {
    const e: Partial<Record<keyof EmployeeFormData, string>> = {};
    if (!form.name.trim()) e.name = "Name is required";
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Invalid email";
    if (!form.role.trim()) e.role = "Role is required";
    if (!form.department.trim()) e.department = "Department is required";
    if (form.salary <= 0) e.salary = "Salary must be positive";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (validate()) onSubmit(form);
  };

  const field = (
    key: keyof EmployeeFormData,
    label: string,
    type: string = "text"
  ) => (
    <div>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={(e) =>
          setForm({ ...form, [key]: type === "number" ? Number(e.target.value) : e.target.value })
        }
        className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />
      {errors[key] && <p className="mt-1 text-xs text-red-600">{errors[key]}</p>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {field("name", "Name")}
      {field("email", "Email", "email")}
      {field("role", "Role")}
      {field("department", "Department")}
      {field("salary", "Salary", "number")}
      <div className="flex gap-2">
        <button
          type="submit"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
        >
          Cancel
        </button>
      </div>
    </form>
  );
};

const DeleteConfirmModal: React.FC<{
  employee: Employee;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({ employee, onConfirm, onCancel }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
      <h3 className="text-lg font-semibold text-gray-900">Delete Employee</h3>
      <p className="mt-2 text-sm text-gray-600">
        Are you sure you want to delete <strong>{employee.name}</strong>? This action
        cannot be undone.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Delete
        </button>
      </div>
    </div>
  </div>
);

const EmployeeCRUD: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [deletingEmployee, setDeletingEmployee] = useState<Employee | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const { sortedData: sortedEmployees, requestSort, getSortIndicator } = useSort(employees);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const loadEmployees = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEmployees(page, search);
      setEmployees(data.employees);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    loadEmployees();
  }, [loadEmployees]);

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleCreate = async (data: EmployeeFormData) => {
    try {
      await createEmployee(data);
      setShowForm(false);
      loadEmployees();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    }
  };

  const handleUpdate = async (data: EmployeeFormData) => {
    if (!editingEmployee) return;
    try {
      await updateEmployee(editingEmployee.id, data);
      setEditingEmployee(null);
      loadEmployees();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  };

  const handleDelete = async () => {
    if (!deletingEmployee) return;
    try {
      await deleteEmployee(deletingEmployee.id);
      setDeletingEmployee(null);
      loadEmployees();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const openEdit = (emp: Employee) => {
    setEditingEmployee(emp);
    setShowForm(false);
  };

  const openCreate = () => {
    setShowForm(true);
    setEditingEmployee(null);
  };

  const cancelForm = () => {
    setShowForm(false);
    setEditingEmployee(null);
  };

  useKeyboardShortcuts({
    onNew: openCreate,
    onSearch: () => searchRef.current?.focus(),
    searchRef,
    onExport: () => exportToCSV(employees as unknown as Record<string, unknown>[], "employee_export.csv"),
    onDelete: () => { if (employees.length > 0) setDeletingEmployee(employees[0]); },
    onClose: cancelForm,
  });

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Employees</h1>
        <button
          onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        > title="Ctrl+N"
          + New Employee
        </button>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by name, email, role, or department…"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full rounded border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
         ref={searchRef}/>
      </div>

      {error && (
        <div className="mb-4 rounded bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
      )}

      {showForm && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Create Employee</h2>
          <EmployeeForm
            initialData={EMPTY_FORM}
            onSubmit={handleCreate}
            onCancel={cancelForm}
            submitLabel="Create"
          />
        </div>
      )}

      {editingEmployee && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Edit Employee</h2>
          <EmployeeForm
            initialData={{
              name: editingEmployee.name,
              email: editingEmployee.email,
              role: editingEmployee.role,
              department: editingEmployee.department,
              salary: editingEmployee.salary,
            }}
            onSubmit={handleUpdate}
            onCancel={cancelForm}
            submitLabel="Update"
          />
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {(["Name", "Email", "Role", "Department", "Salary", "Actions"] as const).map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-600 cursor-pointer select-none"
                  onClick={() => h !== 'Actions' && requestSort(h.toLowerCase())}
                >
                  {h}{h !== 'Actions' ? getSortIndicator(h.toLowerCase()) : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : sortedEmployees.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  No employees found
                </td>
              </tr>
            ) : (
              sortedEmployees.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{emp.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{emp.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{emp.role}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{emp.department}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    ${emp.salary.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <button
                      onClick={() => openEdit(emp)}
                      className="mr-3 text-blue-600 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setDeletingEmployee(emp)}
                      className="text-red-600 hover:underline"
                    > title="Delete key to delete" Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {deletingEmployee && (
        <DeleteConfirmModal
          employee={deletingEmployee}
          onConfirm={handleDelete}
          onCancel={() => setDeletingEmployee(null)}
        />
      )}
    </div>
  );
};

export default EmployeeCRUD;
