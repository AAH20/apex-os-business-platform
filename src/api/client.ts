// APEX-OS API Client
// In-memory CRUD store with localStorage persistence

export interface Product {
  id: number;
  name: string;
  sku: string;
  price: number;
  category: string;
}

export interface Order {
  id: number;
  customerName: string;
  productName: string;
  quantity: number;
  total: number;
  status: string;
  date: string;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string;
  company: string;
}

export interface Employee {
  id: number;
  name: string;
  email: string;
  position: string;
  department: string;
}

export interface Report {
  id: number;
  title: string;
  type: string;
  createdBy: string;
  createdAt: string;
  status: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  status: string;
}

export interface Lead {
  id: number;
  name: string;
  company: string;
  email: string;
  status: string;
  value: number;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  startDate: string;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed';
  priority: 'low' | 'medium' | 'high';
}

export interface InventoryItem {
  id: number;
  name: string;
  sku: string;
  quantity: number;
  price: number;
  category: string;
}

export interface Payment {
  id: number;
  invoiceNumber: string;
  customerName: string;
  amount: number;
  status: 'pending' | 'paid' | 'overdue' | 'cancelled';
  dueDate: string;
}

// ── LocalStorage helpers ──────────────────────────────────────────────
function getStore<T>(key: string): T[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T[]) : [];
  } catch {
    return [];
  }
}

function setStore<T>(key: string, value: T[]): void {
  localStorage.setItem(key, JSON.stringify(value));
}

// ── Generic CRUD factory ──────────────────────────────────────────────
function createCrud<T extends { id: number }>(key: string) {
  return {
    getAll: (): T[] => getStore<T>(key),

    getById: (id: number): T | undefined =>
      getStore<T>(key).find((item) => item.id === id),

    create: (data: Omit<T, 'id'>): T => {
      const items = getStore<T>(key);
      const newItem = { ...data, id: Date.now() } as T;
      setStore(key, [...items, newItem]);
      return newItem;
    },

    update: (id: number, data: Partial<T>): T | null => {
      const items = getStore<T>(key);
      const idx = items.findIndex((i) => i.id === id);
      if (idx === -1) return null;
      items[idx] = { ...items[idx], ...data };
      setStore(key, items);
      return items[idx];
    },

    delete: (id: number): boolean => {
      const items = getStore<T>(key);
      const filtered = items.filter((i) => i.id !== id);
      if (filtered.length === items.length) return false;
      setStore(key, filtered);
      return true;
    },

    search: (query: string, fields: (keyof T)[]): T[] => {
      const q = query.toLowerCase().trim();
      if (!q) return getStore<T>(key);
      return getStore<T>(key).filter((item) =>
        fields.some((f) =>
          String(item[f] ?? '')
            .toLowerCase()
            .includes(q)
        )
      );
    },

    export: (fields: (keyof T)[], headers: string[]): string => {
      const items = getStore<T>(key);
      const rows = items.map((item) =>
        fields.map((f) => `"${String(item[f] ?? '')}"`).join(',')
      );
      return [headers.join(','), ...rows].join('\n');
    },
  };
}

// ── Public API ────────────────────────────────────────────────────────
export const productApi = createCrud<Product>('apex_products');
export const orderApi = createCrud<Order>('apex_orders');
export const customerApi = createCrud<Customer>('apex_customers');
export const employeeApi = createCrud<Employee>('apex_employees');
export const userApi = createCrud<User>('apex_users');
export const leadApi = createCrud<Lead>('apex_leads');
export const reportApi = createCrud<Report>('apex_reports');
export const projectApi = createCrud<Project>('apex_projects');
export const taskApi = createCrud<Task>('apex_tasks');
export const inventoryApi = createCrud<InventoryItem>('apex_inventory');
export const paymentApi = createCrud<Payment>('apex_payments');


