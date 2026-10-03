import React, { useState, useEffect, useCallback } from "react";

interface Account {
  id: number;
  name: string;
  type: string;
  balance: number;
  currency: string;
  status: string;
  created_at: string;
}

interface AccountFormData {
  name: string;
  type: string;
  balance: number;
  currency: string;
  status: string;
}

const API_BASE = "/api/accounts";

const emptyForm: AccountFormData = {
  name: "",
  type: "asset",
  balance: 0,
  currency: "USD",
  status: "active",
};

const ACCOUNT_TYPES = ["asset", "liability", "equity", "revenue", "expense"];
const CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AED"];
const STATUSES = ["active", "inactive", "archived"];

export default function AccountingCRUD() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [formData, setFormData] = useState<AccountFormData>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);

  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: "10",
        ...(search && { search }),
        ...(filterType && { type: filterType }),
        ...(filterStatus && { status: filterStatus }),
      });
      const res = await fetch(`${API_BASE}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAccounts(data.accounts || data.data || []);
      setTotalPages(data.total_pages || data.totalPages || 1);
    } catch (e: any) {
      setError(e.message || "Failed to fetch accounts");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterType, filterStatus]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setFormData(emptyForm);
      setEditingId(null);
      setShowForm(false);
      fetchAccounts();
    } catch (e: any) {
      setError(e.message || "Save failed");
    }
  };

  const handleEdit = (account: Account) => {
    setFormData({
      name: account.name,
      type: account.type,
      balance: account.balance,
      currency: account.currency,
      status: account.status,
    });
    setEditingId(account.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(null);
      fetchAccounts();
    } catch (e: any) {
      setError(e.message || "Delete failed");
    }
  };

  const handleCancel = () => {
    setFormData(emptyForm);
    setEditingId(null);
    setShowForm(false);
    setError("");
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Accounting — Accounts</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Search & Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search accounts..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"
        />
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="">All Types</option>
          {ACCOUNT_TYPES.map((t) => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setFormData(emptyForm); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Account
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-4 mb-4 shadow">
          <h2 className="text-lg font-semibold mb-3">
            {editingId ? "Edit Account" : "Create Account"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                className="w-full border rounded px-3 py-2"
              >
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Balance</label>
              <input
                type="number"
                step="0.01"
                value={formData.balance}
                onChange={(e) => setFormData({ ...formData, balance: parseFloat(e.target.value) || 0 })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Currency</label>
              <select
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                className="w-full border rounded px-3 py-2"
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full border rounded px-3 py-2"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editingId ? "Update" : "Create"}
            </button>
            <button type="button" onClick={handleCancel} className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Accounts Table */}
      <div className="overflow-x-auto bg-white border rounded-lg shadow">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">ID</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-right">Balance</th>
              <th className="px-4 py-3 text-left">Currency</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : accounts.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No accounts found</td></tr>
            ) : (
              accounts.map((acc) => (
                <tr key={acc.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">{acc.id}</td>
                  <td className="px-4 py-3 font-medium">{acc.name}</td>
                  <td className="px-4 py-3 capitalize">{acc.type}</td>
                  <td className="px-4 py-3 text-right">{acc.balance.toLocaleString()}</td>
                  <td className="px-4 py-3">{acc.currency}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      acc.status === "active" ? "bg-green-100 text-green-800" :
                      acc.status === "inactive" ? "bg-yellow-100 text-yellow-800" :
                      "bg-gray-100 text-gray-800"
                    }`}>
                      {acc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleEdit(acc)}
                      className="text-blue-600 hover:underline mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(acc.id)}
                      className="text-red-600 hover:underline"
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

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="px-3 py-1 border rounded disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-600">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="px-3 py-1 border rounded disabled:opacity-50"
        >
          Next
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-600 mb-4">
              Are you sure you want to delete account #{showDeleteConfirm}? This action cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(showDeleteConfirm)}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
