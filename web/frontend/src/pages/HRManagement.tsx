import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

// ── Types ───────────────────────────────────────────────────────────────────

interface Department {
  id: number;
  name: string;
  head: string;
  budget: number;
}

interface Position {
  id: number;
  title: string;
  department_id: number;
  level: string;
  salary_min: number;
  salary_max: number;
}

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

interface LeaveRequest {
  id: number;
  employee_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  status: string;
  reason?: string;
}

interface PerformanceReview {
  id: number;
  employee_id: number;
  review_date: string;
  reviewer_id: number;
  rating: number;
  goals_met: boolean;
  comments?: string;
}

type TabKey = "employees" | "departments" | "positions" | "leave_requests" | "performance_reviews";

// ── API helpers ─────────────────────────────────────────────────────────────

const API_BASE = "/api/hr";
const PAGE_SIZE = 10;
const API_KEY = "test-api-key-12345";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY, ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `API error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

interface PaginatedResult {
  items: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── Form data types ─────────────────────────────────────────────────────────

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

interface DepartmentFormData {
  name: string;
  head: string;
  budget: number;
}

interface PositionFormData {
  title: string;
  department_id: number;
  level: string;
  salary_min: number;
  salary_max: number;
}

interface LeaveRequestFormData {
  employee_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  status: string;
  reason: string;
}

interface PerformanceReviewFormData {
  employee_id: number;
  review_date: string;
  reviewer_id: number;
  rating: number;
  goals_met: boolean;
  comments: string;
}

// ── Form components ─────────────────────────────────────────────────────────

const inputCls = "mt-1 block w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-100 focus:border-cyan-500 focus:outline-none";
const labelCls = "block text-sm font-medium text-gray-300";

const EmployeeForm: React.FC<{
  initialData: EmployeeFormData;
  departments: Department[];
  positions: Position[];
  onSubmit: (data: EmployeeFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}> = ({ initialData, departments, positions, onSubmit, onCancel, submitLabel }) => {
  const [form, setForm] = useState(initialData);
  const [errors, setErrors] = useState<Partial<Record<keyof EmployeeFormData, string>>>({});

  const validate = (): boolean => {
    const e: Partial<Record<keyof EmployeeFormData, string>> = {};
    if (!form.first_name.trim()) e.first_name = "Required";
    if (!form.last_name.trim()) e.last_name = "Required";
    if (!form.email.trim()) e.email = "Required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Invalid email";
    if (form.department_id <= 0) e.department_id = "Required";
    if (form.position_id <= 0) e.position_id = "Required";
    if (form.salary <= 0) e.salary = "Must be positive";
    if (!form.hire_date) e.hire_date = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (validate()) onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className={labelCls}>First Name</label>
          <input className={inputCls} value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          {errors.first_name && <p className="mt-1 text-xs text-red-400">{errors.first_name}</p>}
        </div>
        <div>
          <label className={labelCls}>Last Name</label>
          <input className={inputCls} value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          {errors.last_name && <p className="mt-1 text-xs text-red-400">{errors.last_name}</p>}
        </div>
        <div>
          <label className={labelCls}>Email</label>
          <input type="email" className={inputCls} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email}</p>}
        </div>
        <div>
          <label className={labelCls}>Department</label>
          <select className={inputCls} value={form.department_id} onChange={(e) => setForm({ ...form, department_id: Number(e.target.value) })}>
            <option value={0}>Select department</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          {errors.department_id && <p className="mt-1 text-xs text-red-400">{errors.department_id}</p>}
        </div>
        <div>
          <label className={labelCls}>Position</label>
          <select className={inputCls} value={form.position_id} onChange={(e) => setForm({ ...form, position_id: Number(e.target.value) })}>
            <option value={0}>Select position</option>
            {positions.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
          {errors.position_id && <p className="mt-1 text-xs text-red-400">{errors.position_id}</p>}
        </div>
        <div>
          <label className={labelCls}>Salary</label>
          <input type="number" className={inputCls} value={form.salary} onChange={(e) => setForm({ ...form, salary: Number(e.target.value) })} />
          {errors.salary && <p className="mt-1 text-xs text-red-400">{errors.salary}</p>}
        </div>
        <div>
          <label className={labelCls}>Hire Date</label>
          <input type="date" className={inputCls} value={form.hire_date} onChange={(e) => setForm({ ...form, hire_date: e.target.value })} />
          {errors.hire_date && <p className="mt-1 text-xs text-red-400">{errors.hire_date}</p>}
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded border-gray-600 bg-gray-700" />
          <label className={labelCls}>Active</label>
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600">Cancel</button>
      </div>
    </form>
  );
};

const DepartmentForm: React.FC<{
  initialData: DepartmentFormData;
  onSubmit: (data: DepartmentFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}> = ({ initialData, onSubmit, onCancel, submitLabel }) => {
  const [form, setForm] = useState(initialData);
  const [errors, setErrors] = useState<Partial<Record<keyof DepartmentFormData, string>>>({});

  const validate = (): boolean => {
    const e: Partial<Record<keyof DepartmentFormData, string>> = {};
    if (!form.name.trim()) e.name = "Required";
    if (!form.head.trim()) e.head = "Required";
    if (form.budget <= 0) e.budget = "Must be positive";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (validate()) onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelCls}>Name</label>
        <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name}</p>}
      </div>
      <div>
        <label className={labelCls}>Head</label>
        <input className={inputCls} value={form.head} onChange={(e) => setForm({ ...form, head: e.target.value })} />
        {errors.head && <p className="mt-1 text-xs text-red-400">{errors.head}</p>}
      </div>
      <div>
        <label className={labelCls}>Budget</label>
        <input type="number" className={inputCls} value={form.budget} onChange={(e) => setForm({ ...form, budget: Number(e.target.value) })} />
        {errors.budget && <p className="mt-1 text-xs text-red-400">{errors.budget}</p>}
      </div>
      <div className="flex gap-2">
        <button type="submit" className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600">Cancel</button>
      </div>
    </form>
  );
};

const PositionForm: React.FC<{
  initialData: PositionFormData;
  departments: Department[];
  onSubmit: (data: PositionFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}> = ({ initialData, departments, onSubmit, onCancel, submitLabel }) => {
  const [form, setForm] = useState(initialData);
  const [errors, setErrors] = useState<Partial<Record<keyof PositionFormData, string>>>({});

  const validate = (): boolean => {
    const e: Partial<Record<keyof PositionFormData, string>> = {};
    if (!form.title.trim()) e.title = "Required";
    if (form.department_id <= 0) e.department_id = "Required";
    if (!form.level.trim()) e.level = "Required";
    if (form.salary_min <= 0) e.salary_min = "Must be positive";
    if (form.salary_max <= 0) e.salary_max = "Must be positive";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (validate()) onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelCls}>Title</label>
        <input className={inputCls} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        {errors.title && <p className="mt-1 text-xs text-red-400">{errors.title}</p>}
      </div>
      <div>
        <label className={labelCls}>Department</label>
        <select className={inputCls} value={form.department_id} onChange={(e) => setForm({ ...form, department_id: Number(e.target.value) })}>
          <option value={0}>Select department</option>
          {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        {errors.department_id && <p className="mt-1 text-xs text-red-400">{errors.department_id}</p>}
      </div>
      <div>
        <label className={labelCls}>Level</label>
        <input className={inputCls} value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })} />
        {errors.level && <p className="mt-1 text-xs text-red-400">{errors.level}</p>}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Salary Min</label>
          <input type="number" className={inputCls} value={form.salary_min} onChange={(e) => setForm({ ...form, salary_min: Number(e.target.value) })} />
          {errors.salary_min && <p className="mt-1 text-xs text-red-400">{errors.salary_min}</p>}
        </div>
        <div>
          <label className={labelCls}>Salary Max</label>
          <input type="number" className={inputCls} value={form.salary_max} onChange={(e) => setForm({ ...form, salary_max: Number(e.target.value) })} />
          {errors.salary_max && <p className="mt-1 text-xs text-red-400">{errors.salary_max}</p>}
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600">Cancel</button>
      </div>
    </form>
  );
};

const LeaveRequestForm: React.FC<{
  initialData: LeaveRequestFormData;
  employees: Employee[];
  onSubmit: (data: LeaveRequestFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}> = ({ initialData, employees, onSubmit, onCancel, submitLabel }) => {
  const [form, setForm] = useState(initialData);
  const [errors, setErrors] = useState<Partial<Record<keyof LeaveRequestFormData, string>>>({});

  const validate = (): boolean => {
    const e: Partial<Record<keyof LeaveRequestFormData, string>> = {};
    if (form.employee_id <= 0) e.employee_id = "Required";
    if (!form.leave_type.trim()) e.leave_type = "Required";
    if (!form.start_date) e.start_date = "Required";
    if (!form.end_date) e.end_date = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (validate()) onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelCls}>Employee</label>
        <select className={inputCls} value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: Number(e.target.value) })}>
          <option value={0}>Select employee</option>
          {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>)}
        </select>
        {errors.employee_id && <p className="mt-1 text-xs text-red-400">{errors.employee_id}</p>}
      </div>
      <div>
        <label className={labelCls}>Leave Type</label>
        <input className={inputCls} value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })} />
        {errors.leave_type && <p className="mt-1 text-xs text-red-400">{errors.leave_type}</p>}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Start Date</label>
          <input type="date" className={inputCls} value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          {errors.start_date && <p className="mt-1 text-xs text-red-400">{errors.start_date}</p>}
        </div>
        <div>
          <label className={labelCls}>End Date</label>
          <input type="date" className={inputCls} value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          {errors.end_date && <p className="mt-1 text-xs text-red-400">{errors.end_date}</p>}
        </div>
      </div>
      <div>
        <label className={labelCls}>Status</label>
        <select className={inputCls} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
      <div>
        <label className={labelCls}>Reason</label>
        <input className={inputCls} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
      </div>
      <div className="flex gap-2">
        <button type="submit" className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600">Cancel</button>
      </div>
    </form>
  );
};

const PerformanceReviewForm: React.FC<{
  initialData: PerformanceReviewFormData;
  employees: Employee[];
  onSubmit: (data: PerformanceReviewFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}> = ({ initialData, employees, onSubmit, onCancel, submitLabel }) => {
  const [form, setForm] = useState(initialData);
  const [errors, setErrors] = useState<Partial<Record<keyof PerformanceReviewFormData, string>>>({});

  const validate = (): boolean => {
    const e: Partial<Record<keyof PerformanceReviewFormData, string>> = {};
    if (form.employee_id <= 0) e.employee_id = "Required";
    if (!form.review_date) e.review_date = "Required";
    if (form.reviewer_id <= 0) e.reviewer_id = "Required";
    if (form.rating < 0 || form.rating > 5) e.rating = "0-5";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (validate()) onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelCls}>Employee</label>
        <select className={inputCls} value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: Number(e.target.value) })}>
          <option value={0}>Select employee</option>
          {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>)}
        </select>
        {errors.employee_id && <p className="mt-1 text-xs text-red-400">{errors.employee_id}</p>}
      </div>
      <div>
        <label className={labelCls}>Review Date</label>
        <input type="date" className={inputCls} value={form.review_date} onChange={(e) => setForm({ ...form, review_date: e.target.value })} />
        {errors.review_date && <p className="mt-1 text-xs text-red-400">{errors.review_date}</p>}
      </div>
      <div>
        <label className={labelCls}>Reviewer</label>
        <select className={inputCls} value={form.reviewer_id} onChange={(e) => setForm({ ...form, reviewer_id: Number(e.target.value) })}>
          <option value={0}>Select reviewer</option>
          {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>)}
        </select>
        {errors.reviewer_id && <p className="mt-1 text-xs text-red-400">{errors.reviewer_id}</p>}
      </div>
      <div>
        <label className={labelCls}>Rating (0-5)</label>
        <input type="number" step="0.1" min="0" max="5" className={inputCls} value={form.rating} onChange={(e) => setForm({ ...form, rating: Number(e.target.value) })} />
        {errors.rating && <p className="mt-1 text-xs text-red-400">{errors.rating}</p>}
      </div>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={form.goals_met} onChange={(e) => setForm({ ...form, goals_met: e.target.checked })} className="rounded border-gray-600 bg-gray-700" />
        <label className={labelCls}>Goals Met</label>
      </div>
      <div>
        <label className={labelCls}>Comments</label>
        <textarea className={inputCls} rows={3} value={form.comments} onChange={(e) => setForm({ ...form, comments: e.target.value })} />
      </div>
      <div className="flex gap-2">
        <button type="submit" className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600">Cancel</button>
      </div>
    </form>
  );
};

// ── Delete confirmation modal ───────────────────────────────────────────────

const DeleteModal: React.FC<{
  itemName: string;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({ itemName, onConfirm, onCancel }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div className="w-full max-w-sm rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-xl">
      <h3 className="text-lg font-semibold text-gray-100">Delete {itemName}</h3>
      <p className="mt-2 text-sm text-gray-300">Are you sure? This action cannot be undone.</p>
      <div className="mt-4 flex justify-end gap-2">
        <button onClick={onCancel} className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-600">Cancel</button>
        <button onClick={onConfirm} className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Delete</button>
      </div>
    </div>
  </div>
);

// ── Main HR Management page ─────────────────────────────────────────────────

const TABS: { key: TabKey; label: string }[] = [
  { key: "employees", label: "Employees" },
  { key: "departments", label: "Departments" },
  { key: "positions", label: "Positions" },
  { key: "leave_requests", label: "Leave Requests" },
  { key: "performance_reviews", label: "Performance Reviews" },
];

const HRManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>("employees");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
  const [performanceReviews, setPerformanceReviews] = useState<PerformanceReview[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [filterValue, setFilterValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<Record<string, unknown> | null>(null);
  const [deletingItem, setDeletingItem] = useState<{ id: number; name: string } | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Client-side filter
  const filteredEmployees = useMemo(() => {
    if (!filterValue) return employees;
    const fid = Number(filterValue);
    return employees.filter((e) => e.department_id === fid);
  }, [employees, filterValue]);

  const filteredLeaveRequests = useMemo(() => {
    if (!filterValue) return leaveRequests;
    return leaveRequests.filter((lr) => lr.status === filterValue);
  }, [leaveRequests, filterValue]);

  const filteredPerformanceReviews = useMemo(() => {
    if (!filterValue) return performanceReviews;
    if (filterValue === "goals_met") return performanceReviews.filter((pr) => pr.goals_met);
    return performanceReviews;
  }, [performanceReviews, filterValue]);

  // Load reference data (departments, positions, employees) for dropdowns
  const loadReferenceData = useCallback(async () => {
    try {
      const [deptData, posData, empData] = await Promise.all([
        apiFetch<PaginatedResult>("/departments?page=1&page_size=100"),
        apiFetch<PaginatedResult>("/positions?page=1&page_size=100"),
        apiFetch<PaginatedResult>("/employees?page=1&page_size=100"),
      ]);
      setDepartments(deptData.items as unknown as Department[]);
      setPositions(posData.items as unknown as Position[]);
      setEmployees(empData.items as unknown as Employee[]);
    } catch {
      // Reference data is best-effort
    }
  }, []);

  // Load active tab data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (search) params.set("search", search);
      const data = await apiFetch<PaginatedResult>(`/${activeTab}?${params}`);
      const items = data.items;
      switch (activeTab) {
        case "employees": setEmployees(items as unknown as Employee[]); break;
        case "departments": setDepartments(items as unknown as Department[]); break;
        case "positions": setPositions(items as unknown as Position[]); break;
        case "leave_requests": setLeaveRequests(items as unknown as LeaveRequest[]); break;
        case "performance_reviews": setPerformanceReviews(items as unknown as PerformanceReview[]); break;
      }
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [activeTab, page, search]);

  useEffect(() => { loadReferenceData(); }, [loadReferenceData]);
  useEffect(() => { loadData(); }, [loadData]);

  const handleSearch = (value: string) => { setSearch(value); setPage(1); };

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
    setPage(1);
    setSearch("");
    setShowForm(false);
    setEditingItem(null);
  };

  const handleCreate = async (data: Record<string, unknown>) => {
    try {
      await apiFetch(`/${activeTab}`, { method: "POST", body: JSON.stringify(data) });
      setShowForm(false);
      loadData();
      loadReferenceData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    }
  };

  const handleUpdate = async (data: Record<string, unknown>) => {
    if (!editingItem) return;
    try {
      await apiFetch(`/${activeTab}/${editingItem.id}`, { method: "PUT", body: JSON.stringify(data) });
      setEditingItem(null);
      loadData();
      loadReferenceData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  };

  const handleDelete = async () => {
    if (!deletingItem) return;
    try {
      await apiFetch(`/${activeTab}/${deletingItem.id}`, { method: "DELETE" });
      setDeletingItem(null);
      loadData();
      loadReferenceData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const openEdit = (item: Record<string, unknown>) => {
    setEditingItem(item);
    setShowForm(false);
  };

  const openCreate = () => {
    setShowForm(true);
    setEditingItem(null);
  };

  const cancelForm = () => {
    setShowForm(false);
    setEditingItem(null);
  };

  useKeyboardShortcuts({
    onNew: openCreate,
    onSearch: () => searchRef.current?.focus(),
    searchRef,
    onExport: () => {
      const data = activeTab === "employees" ? employees : activeTab === "departments" ? departments : activeTab === "positions" ? positions : activeTab === "leave_requests" ? leaveRequests : performanceReviews;
      exportToCSV(data as unknown as Record<string, unknown>[], `${activeTab}_export.csv`);
    },
    onDelete: () => {
      const data = activeTab === "employees" ? employees : activeTab === "departments" ? departments : activeTab === "positions" ? positions : activeTab === "leave_requests" ? leaveRequests : performanceReviews;
      if (data.length > 0) setDeletingItem({ id: (data[0] as unknown as Record<string, unknown>).id as number, name: activeTab });
    },
    onClose: cancelForm,
  });

  // ── Render table based on active tab ──────────────────────────────────────

  const renderTable = () => {
    if (loading) {
      return <div className="py-8 text-center text-sm text-gray-400">Loading…</div>;
    }

    const emptyRow = (cols: number) => (
      <tr><td colSpan={cols} className="py-8 text-center text-sm text-gray-400">No records found</td></tr>
    );

    switch (activeTab) {
      case "employees": {
        const sorted = useSort(filteredEmployees);
        return (
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>
                {["Name", "Email", "Department", "Position", "Salary", "Hire Date", "Active", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-300">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {sorted.sortedData.length === 0 ? emptyRow(8) : sorted.sortedData.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-900/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">{emp.first_name} {emp.last_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{emp.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{departments.find((d) => d.id === emp.department_id)?.name ?? "-"}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{positions.find((p) => p.id === emp.position_id)?.title ?? "-"}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">${emp.salary.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{emp.hire_date}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${emp.is_active ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                      {emp.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <button onClick={() => openEdit(emp as unknown as Record<string, unknown>)} className="mr-3 text-cyan-400 hover:underline">Edit</button>
                    <button onClick={() => setDeletingItem({ id: emp.id, name: `${emp.first_name} ${emp.last_name}` })} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      }
      case "departments": {
        const sorted = useSort(departments);
        return (
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>{["Name", "Head", "Budget", "Actions"].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-300">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {sorted.sortedData.length === 0 ? emptyRow(4) : sorted.sortedData.map((dept) => (
                <tr key={dept.id} className="hover:bg-gray-900/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">{dept.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{dept.head}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">${dept.budget.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">
                    <button onClick={() => openEdit(dept as unknown as Record<string, unknown>)} className="mr-3 text-cyan-400 hover:underline">Edit</button>
                    <button onClick={() => setDeletingItem({ id: dept.id, name: dept.name })} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      }
      case "positions": {
        const sorted = useSort(positions);
        return (
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>{["Title", "Department", "Level", "Salary Range", "Actions"].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-300">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {sorted.sortedData.length === 0 ? emptyRow(5) : sorted.sortedData.map((pos) => (
                <tr key={pos.id} className="hover:bg-gray-900/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">{pos.title}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{departments.find((d) => d.id === pos.department_id)?.name ?? "-"}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{pos.level}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">${pos.salary_min.toLocaleString()} - ${pos.salary_max.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">
                    <button onClick={() => openEdit(pos as unknown as Record<string, unknown>)} className="mr-3 text-cyan-400 hover:underline">Edit</button>
                    <button onClick={() => setDeletingItem({ id: pos.id, name: pos.title })} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      }
      case "leave_requests": {
        const sorted = useSort(filteredLeaveRequests);
        return (
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>{["Employee", "Type", "Start", "End", "Status", "Reason", "Actions"].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-300">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {sorted.sortedData.length === 0 ? emptyRow(7) : sorted.sortedData.map((lr) => (
                <tr key={lr.id} className="hover:bg-gray-900/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">{employees.find((e) => e.id === lr.employee_id) ? `${(employees.find((e) => e.id === lr.employee_id) as Employee).first_name} ${(employees.find((e) => e.id === lr.employee_id) as Employee).last_name}` : "-"}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{lr.leave_type}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{lr.start_date}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{lr.end_date}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${lr.status === "approved" ? "bg-emerald-500/20 text-emerald-400" : lr.status === "rejected" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                      {lr.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">{lr.reason ?? "-"}</td>
                  <td className="px-4 py-3 text-sm">
                    <button onClick={() => openEdit(lr as unknown as Record<string, unknown>)} className="mr-3 text-cyan-400 hover:underline">Edit</button>
                    <button onClick={() => setDeletingItem({ id: lr.id, name: `Leave #${lr.id}` })} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      }
      case "performance_reviews": {
        const sorted = useSort(filteredPerformanceReviews);
        return (
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>{["Employee", "Date", "Reviewer", "Rating", "Goals Met", "Comments", "Actions"].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-300">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {sorted.sortedData.length === 0 ? emptyRow(7) : sorted.sortedData.map((pr) => (
                <tr key={pr.id} className="hover:bg-gray-900/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">{employees.find((e) => e.id === pr.employee_id) ? `${(employees.find((e) => e.id === pr.employee_id) as Employee).first_name} ${(employees.find((e) => e.id === pr.employee_id) as Employee).last_name}` : "-"}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{pr.review_date}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{employees.find((e) => e.id === pr.reviewer_id) ? `${(employees.find((e) => e.id === pr.reviewer_id) as Employee).first_name} ${(employees.find((e) => e.id === pr.reviewer_id) as Employee).last_name}` : "-"}</td>
                  <td className="px-4 py-3 text-sm text-gray-300">{pr.rating}/5</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${pr.goals_met ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                      {pr.goals_met ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-300">{pr.comments ?? "-"}</td>
                  <td className="px-4 py-3 text-sm">
                    <button onClick={() => openEdit(pr as unknown as Record<string, unknown>)} className="mr-3 text-cyan-400 hover:underline">Edit</button>
                    <button onClick={() => setDeletingItem({ id: pr.id, name: `Review #${pr.id}` })} className="text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      }
    }
  };

  // ── Render form based on active tab ───────────────────────────────────────

  const renderForm = () => {
    if (showForm) {
      switch (activeTab) {
        case "employees":
          return (
            <EmployeeForm
              initialData={{ first_name: "", last_name: "", email: "", department_id: 0, position_id: 0, salary: 0, hire_date: "", is_active: true }}
              departments={departments}
              positions={positions}
              onSubmit={(d) => handleCreate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Create"
            />
          );
        case "departments":
          return (
            <DepartmentForm
              initialData={{ name: "", head: "", budget: 0 }}
              onSubmit={(d) => handleCreate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Create"
            />
          );
        case "positions":
          return (
            <PositionForm
              initialData={{ title: "", department_id: 0, level: "", salary_min: 0, salary_max: 0 }}
              departments={departments}
              onSubmit={(d) => handleCreate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Create"
            />
          );
        case "leave_requests":
          return (
            <LeaveRequestForm
              initialData={{ employee_id: 0, leave_type: "", start_date: "", end_date: "", status: "pending", reason: "" }}
              employees={employees}
              onSubmit={(d) => handleCreate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Create"
            />
          );
        case "performance_reviews":
          return (
            <PerformanceReviewForm
              initialData={{ employee_id: 0, review_date: "", reviewer_id: 0, rating: 0, goals_met: false, comments: "" }}
              employees={employees}
              onSubmit={(d) => handleCreate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Create"
            />
          );
      }
    }
    if (editingItem) {
      switch (activeTab) {
        case "employees": {
          const emp = editingItem as unknown as Employee;
          return (
            <EmployeeForm
              initialData={{ first_name: emp.first_name, last_name: emp.last_name, email: emp.email, department_id: emp.department_id, position_id: emp.position_id, salary: emp.salary, hire_date: emp.hire_date, is_active: emp.is_active }}
              departments={departments}
              positions={positions}
              onSubmit={(d) => handleUpdate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Update"
            />
          );
        }
        case "departments": {
          const dept = editingItem as unknown as Department;
          return (
            <DepartmentForm
              initialData={{ name: dept.name, head: dept.head, budget: dept.budget }}
              onSubmit={(d) => handleUpdate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Update"
            />
          );
        }
        case "positions": {
          const pos = editingItem as unknown as Position;
          return (
            <PositionForm
              initialData={{ title: pos.title, department_id: pos.department_id, level: pos.level, salary_min: pos.salary_min, salary_max: pos.salary_max }}
              departments={departments}
              onSubmit={(d) => handleUpdate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Update"
            />
          );
        }
        case "leave_requests": {
          const lr = editingItem as unknown as LeaveRequest;
          return (
            <LeaveRequestForm
              initialData={{ employee_id: lr.employee_id, leave_type: lr.leave_type, start_date: lr.start_date, end_date: lr.end_date, status: lr.status, reason: lr.reason ?? "" }}
              employees={employees}
              onSubmit={(d) => handleUpdate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Update"
            />
          );
        }
        case "performance_reviews": {
          const pr = editingItem as unknown as PerformanceReview;
          return (
            <PerformanceReviewForm
              initialData={{ employee_id: pr.employee_id, review_date: pr.review_date, reviewer_id: pr.reviewer_id, rating: pr.rating, goals_met: pr.goals_met, comments: pr.comments ?? "" }}
              employees={employees}
              onSubmit={(d) => handleUpdate(d as unknown as Record<string, unknown>)}
              onCancel={cancelForm}
              submitLabel="Update"
            />
          );
        }
      }
    }
    return null;
  };

  // ── Dashboard data ───────────────────────────────────────────────────────
  const dashboardData = useMemo(() => {
    const totalEmployees = employees.length;
    const activeDepartments = departments.filter((d) => d.head && d.head.trim()).length;
    const openLeaveRequests = leaveRequests.filter((lr) => lr.status === "pending").length;
    const avgPerformance = performanceReviews.length > 0
      ? (performanceReviews.reduce((sum, pr) => sum + pr.rating, 0) / performanceReviews.length).toFixed(1)
      : "0.0";

    const employeesByDepartment = departments.map((d) => ({
      name: d.name,
      count: employees.filter((e) => e.department_id === d.id).length,
    })).filter((d) => d.count > 0);

    const leaveByStatus = (["pending", "approved", "rejected"] as const).map((status) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      value: leaveRequests.filter((lr) => lr.status === status).length,
    })).filter((s) => s.value > 0);

    return { totalEmployees, activeDepartments, openLeaveRequests, avgPerformance, employeesByDepartment, leaveByStatus };
  }, [employees, departments, leaveRequests, performanceReviews]);

  const PIE_COLORS = ["#f59e0b", "#10b981", "#ef4444"];

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">HR Management</h1>
        <button onClick={openCreate} className="rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">
          + New {TABS.find((t) => t.key === activeTab)?.label.replace(/s$/, "")}
        </button>
      </div>

      {/* Dashboard */}
      <div className="mb-6 space-y-4">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
            <p className="text-sm text-gray-400">Total Employees</p>
            <p className="mt-1 text-2xl font-bold text-gray-100">{dashboardData.totalEmployees}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
            <p className="text-sm text-gray-400">Active Departments</p>
            <p className="mt-1 text-2xl font-bold text-gray-100">{dashboardData.activeDepartments}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
            <p className="text-sm text-gray-400">Open Leave Requests</p>
            <p className="mt-1 text-2xl font-bold text-amber-400">{dashboardData.openLeaveRequests}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
            <p className="text-sm text-gray-400">Avg Performance Score</p>
            <p className="mt-1 text-2xl font-bold text-cyan-400">{dashboardData.avgPerformance}</p>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-gray-300">Employees by Department</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={dashboardData.employeesByDepartment}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 12 }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "0.375rem" }} labelStyle={{ color: "#f3f4f6" }} itemStyle={{ color: "#60a5fa" }} />
                <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-gray-300">Leave Requests by Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={dashboardData.leaveByStatus} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {dashboardData.leaveByStatus.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "0.375rem" }} labelStyle={{ color: "#f3f4f6" }} itemStyle={{ color: "#f3f4f6" }} />
                <Legend wrapperStyle={{ color: "#9ca3af", fontSize: "12px" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex flex-wrap gap-1 rounded-lg bg-gray-800 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-cyan-600 text-white"
                : "text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search & Filter */}
      <div className="mb-4 flex gap-3">
        <input
          ref={searchRef}
          type="text"
          placeholder={`Search ${TABS.find((t) => t.key === activeTab)?.label.toLowerCase()}…`}
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="flex-1 rounded border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-gray-100 focus:border-cyan-500 focus:outline-none"
        />
        <select
          value={filterValue}
          onChange={(e) => setFilterValue(e.target.value)}
          className="rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-cyan-500 focus:outline-none"
        >
          <option value="">All</option>
          {activeTab === "employees" && departments.map((d) => <option key={d.id} value={String(d.id)}>{d.name}</option>)}
          {activeTab === "leave_requests" && ["pending", "approved", "rejected"].map((s) => <option key={s} value={s}>{s}</option>)}
          {activeTab === "performance_reviews" && <option value="goals_met">Goals Met</option>}
        </select>
      </div>

      {error && (
        <div className="mb-4 rounded bg-red-500/20 px-4 py-2 text-sm text-red-400">{error}</div>
      )}

      {/* Form */}
      {(showForm || editingItem) && (
        <div className="mb-6 rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-100">
            {editingItem ? "Edit" : "Create"} {TABS.find((t) => t.key === activeTab)?.label.replace(/s$/, "")}
          </h2>
          {renderForm()}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-700 bg-gray-800 shadow-sm">
        {renderTable()}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-400">Page {page} of {totalPages} ({total} total)</p>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded border border-gray-600 px-3 py-1 text-sm text-gray-300 disabled:opacity-40">Previous</button>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="rounded border border-gray-600 px-3 py-1 text-sm text-gray-300 disabled:opacity-40">Next</button>
          </div>
        </div>
      )}

      {/* Delete modal */}
      {deletingItem && (
        <DeleteModal
          itemName={deletingItem.name}
          onConfirm={handleDelete}
          onCancel={() => setDeletingItem(null)}
        />
      )}
    </div>
  );
};

export default HRManagement;
