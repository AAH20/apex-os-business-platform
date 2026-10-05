import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { fetchWithTimeout } from '../api/fallback'

interface Employee {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  department_id: number;
  position_id: number;
  salary: number;
  hire_date: string;
  is_active: boolean;
}

interface EmployeeFormData {
  first_name: string;
  last_name: string;
  email: string;
  department_id: number;
  position_id: number;
  salary: number;
  hire_date: string;
  is_active: boolean;
}

const EMPTY_FORM: EmployeeFormData = {
  first_name: "",
  last_name: "",
  email: "",
  department_id: 0,
  position_id: 0,
  salary: 0,
  hire_date: "",
  is_active: true,
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
  const res = await fetchWithTimeout(`${API_BASE}?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
  if (!res.ok) throw new Error("Failed to fetch employees");
  return res.json();
};

const createEmployee = async (data: EmployeeFormData): Promise<Employee> => {
  const res = await fetchWithTimeout(API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create employee");
  return res.json();
};

const updateEmployee = async (
  id: number,
  data: EmployeeFormData
): Promise<Employee> => {
  const res = await fetchWithTimeout(`${API_BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update employee");
  return res.json();
};

const deleteEmployee = async (id: number): Promise<void> => {
  const res = await fetchWithTimeout(`${API_BASE}/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
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
    if (!form.first_name.trim()) e.first_name = "First name is required";
    if (!form.last_name.trim()) e.last_name = "Last name is required";
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Invalid email";
    if (!form.department_id) e.department_id = "Department is required";
    if (!form.position_id) e.position_id = "Position is required";
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
      <label className="block text-sm font-medium text-gray-300">{label}</label>
      <input
        type={type}
        value={String(form[key])}
        onChange={(e) =>
          setForm({ ...form, [key]: type === "number" ? Number(e.target.value) : String(e.target.value) })
        }
        className="mt-1 block w-full rounded border border-gray-700 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />
      {errors[key] && <p className="mt-1 text-xs text-red-400">{errors[key]}</p>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {field("first_name", "First Name")}
      {field("last_name", "Last Name")}
      {field("email", "Email", "email")}
      {field("department_id", "Department ID", "number")}
      {field("position_id", "Position ID", "number")}
      {field("salary", "Salary", "number")}
      {field("hire_date", "Hire Date")}
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
          className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600"
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
    <div className="w-full max-w-sm rounded-lg bg-gray-800 p-6 shadow-xl">
      <h3 className="text-lg font-semibold text-gray-100">Delete Employee</h3>
      <p className="mt-2 text-sm text-gray-300">
        Are you sure you want to delete <strong>{employee.first_name} {employee.last_name}</strong>? This action
        cannot be undone.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600"
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
        <h1 className="text-2xl font-bold text-gray-100">Employees</h1>
        <button
          onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New Employee
        </button>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by name, email, role, or department…"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full rounded border border-gray-700 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
         ref={searchRef}/>
      </div>

      {error && (
        <div className="mb-4 rounded bg-red-900/50 px-4 py-2 text-sm text-red-200">{error}</div>
      )}

      {showForm && (
        <div className="mb-6 rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-sm">
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
        <div className="mb-6 rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Edit Employee</h2>
          <EmployeeForm
            initialData={{
              first_name: editingEmployee.first_name,
              last_name: editingEmployee.last_name,
              email: editingEmployee.email,
              department_id: editingEmployee.department_id,
              position_id: editingEmployee.position_id,
              salary: editingEmployee.salary,
              hire_date: editingEmployee.hire_date,
              is_active: editingEmployee.is_active,
            }}
            onSubmit={handleUpdate}
            onCancel={cancelForm}
            submitLabel="Update"
          />
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-700 bg-gray-800 shadow-sm">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-900">
            <tr>
              {(["Name", "Email", "Role", "Department", "Salary", "Actions"] as const).map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-300 cursor-pointer select-none"
                  onClick={() => h !== 'Actions' && requestSort(h.toLowerCase())}
                >
                  {h}{h !== 'Actions' ? getSortIndicator(h.toLowerCase()) : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                  Loading…
                </td>
              </tr>
            ) : sortedEmployees.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                  No employees found
                </td>
              </tr>
            ) : (
              sortedEmployees.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-900">
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">{emp.first_name} {emp.last_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{emp.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{emp.department_id}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{emp.position_id}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    ${(emp.salary ?? 0).toLocaleString()}
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
                      className="text-red-400 hover:underline"
                    title="Delete key to delete">Delete
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
          <p className="text-sm text-gray-300">
            Page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded border border-gray-700 px-3 py-1 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded border border-gray-700 px-3 py-1 text-sm disabled:opacity-40"
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