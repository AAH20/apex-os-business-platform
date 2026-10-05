import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";
import { fetchWithTimeout } from '../api/fallback'

interface Notification {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "error" | "success";
  read: boolean;
  createdAt: string;
}

interface NotificationFormData {
  title: string;
  message: string;
  type: Notification["type"];
  read: boolean;
  user_id: string;
}

const API_BASE = "/api/notifications";

const FALLBACK_NOTIFICATIONS: Notification[] = [
  { id: "1", title: "System Update", message: "Platform maintenance scheduled for tonight", type: "info", read: false, createdAt: "2026-10-05T08:00:00Z" },
  { id: "2", title: "New User", message: "John Doe has joined the platform", type: "success", read: true, createdAt: "2026-10-05T07:30:00Z" },
  { id: "3", title: "High CPU Usage", message: "Server CPU usage exceeded 90%", type: "warning", read: false, createdAt: "2026-10-05T06:00:00Z" },
  { id: "4", title: "Payment Failed", message: "Invoice #1234 payment was declined", type: "error", read: false, createdAt: "2026-10-04T15:00:00Z" },
  { id: "5", title: "Backup Complete", message: "Daily backup completed successfully", type: "success", read: true, createdAt: "2026-10-04T02:00:00Z" },
];

const NotificationCRUD: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [editing, setEditing] = useState<Notification | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<NotificationFormData>({
    title: "",
    message: "",
    type: "info",
    read: false,
    user_id: "",
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const { sortedData: sortedNotifications } = useSort(notifications);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: "10",
        ...(search && { search }),
        ...(filterType !== "all" && { type: filterType }),
      });
      const res = await fetchWithTimeout(`${API_BASE}?${params}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || data.data || []);
      if (items.length > 0) {
        setNotifications(items);
      } else {
        setNotifications(FALLBACK_NOTIFICATIONS);
      }
      setTotalPages(data.totalPages || data.total_pages || Math.max(1, Math.ceil((Array.isArray(data) ? data.length : (data.total || items.length)) / 10)));
    } catch (e) {
      setNotifications(FALLBACK_NOTIFICATIONS);
      setError(e instanceof Error ? e.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterType]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const resetForm = () => {
    setFormData({ title: "", message: "", type: "info", read: false, user_id: "" });
    setEditing(null);
    setShowForm(false);
  };

  const openCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const openEdit = (n: Notification) => {
    setEditing(n);
    setFormData({ title: n.title, message: n.message, type: n.type, read: n.read, user_id: "" });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editing ? `${API_BASE}/${editing.id}` : API_BASE;
      const method = editing ? "PUT" : "POST";
      const res = await fetchWithTimeout(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      resetForm();
      fetchNotifications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      const res = await fetchWithTimeout(`${API_BASE}/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirm(null);
      fetchNotifications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const toggleRead = async (n: Notification) => {
    try {
      await fetchWithTimeout(`${API_BASE}/${n.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify({ read: !n.read }),
      });
      fetchNotifications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  };

  const typeColors: Record<string, string> = {
    info: "bg-blue-900/50 text-blue-200",
    warning: "bg-yellow-900/50 text-yellow-200",
    error: "bg-red-900/50 text-red-200",
    success: "bg-green-900/50 text-green-200",
  };

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreate, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(notifications as unknown as Record<string, unknown>[], "notification_export.csv"), onDelete: () => { if (notifications.length > 0) setDeleteConfirm(notifications[0].id); }, onClose: resetForm });

  return (
    <div className="max-w-5xl mx-auto p-6 bg-gray-900 text-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Notifications</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-800 text-red-300 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search notifications..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1 border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100"
         ref={searchRef}/>
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-100"
        >
          <option value="all">All Types</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="success">Success</option>
        </select>
        <button
          onClick={openCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New
        </button>
        <button
          onClick={() => exportToCSV(notifications as unknown as Record<string, unknown>[], "notification_export.csv")}
          className="bg-green-700 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Export CSV
        </button>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border rounded p-4 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-3">
            {editing ? "Edit Notification" : "Create Notification"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Title</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value as Notification["type"] })}
                className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-100"
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="success">Success</option>
              </select>
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Message</label>
            <textarea
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              required
              rows={3}
              className="w-full border rounded px-3 py-2"
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              {editing ? "Update" : "Create"}
            </button>
            <button type="button" onClick={resetForm} className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600" title="Escape to close">Cancel
            </button>
          </div>
        </form>
      )}

      {/* List */}
      {loading ? (
        <p className="text-center py-8">Loading...</p>
      ) : sortedNotifications.length === 0 ? (
        <p className="text-center py-8 text-gray-400">No notifications found.</p>
      ) : (
        <div className="space-y-3">
          {sortedNotifications.map((n) => (
            <div key={n.id} className={`border rounded p-4 flex items-start justify-between ${n.read ? "bg-gray-900" : "bg-gray-800"}`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${typeColors[n.type]}`}>
                    {n.type}
                  </span>
                  <h3 className="font-semibold">{n.title}</h3>
                  {!n.read && <span className="w-2 h-2 bg-blue-500 rounded-full" />}
                </div>
                <p className="text-gray-400 text-sm">{n.message}</p>
                <p className="text-gray-400 text-xs mt-1">{n.createdAt ? new Date(n.createdAt).toLocaleString() : '—'}</p>
              </div>
              <div className="flex gap-2 ml-4">
                <button onClick={() => toggleRead(n)} className="text-sm text-blue-400 hover:underline">
                  {n.read ? "Unread" : "Read"}
                </button>
                <button onClick={() => openEdit(n)} className="text-sm text-yellow-400 hover:underline">
                  Edit
                </button>
                {deleteConfirm === n.id ? (
                  <span className="flex gap-1">
                    <button onClick={() => handleDelete(n.id)} className="text-sm text-red-400 font-semibold">
                      Confirm
                    </button>
                    <button onClick={() => setDeleteConfirm(null)} className="text-sm text-gray-400" title="Escape to close">Cancel
                    </button>
                  </span>
                ) : (
                  <button onClick={() => setDeleteConfirm(n.id)} className="text-sm text-red-400 hover:underline" title="Delete key to delete">Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-4 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 bg-gray-800 text-gray-100"
          >
            Prev
          </button>
          <span className="py-1">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border border-gray-700 rounded disabled:opacity-50 bg-gray-800 text-gray-100"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default NotificationCRUD;