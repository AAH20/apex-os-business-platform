import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { Notification } from '../api/client';
import { Bell, Check, Trash2, Filter, RefreshCw, Info, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

const POLL_INTERVAL = 30_000; // 30 seconds

const typeIcons: Record<string, React.ReactNode> = {
  info: <Info size={16} className="text-blue-400" />,
  warning: <AlertTriangle size={16} className="text-amber-400" />,
  success: <CheckCircle size={16} className="text-emerald-400" />,
  error: <XCircle size={16} className="text-red-400" />,
};

const typeBadgeColors: Record<string, string> = {
  info: 'bg-blue-900/50 text-blue-300',
  warning: 'bg-amber-900/50 text-amber-300',
  success: 'bg-emerald-900/50 text-emerald-300',
  error: 'bg-red-900/50 text-red-300',
};

const NotificationCenter: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [readFilter, setReadFilter] = useState<string>('all');
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [markingId, setMarkingId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { page: number; limit: number; type?: string; read?: boolean } = {
        page,
        limit: 20,
      };
      if (typeFilter !== 'all') params.type = typeFilter;
      if (readFilter === 'unread') params.read = false;
      else if (readFilter === 'read') params.read = true;

      const data = await api.getNotifications(params);
      setNotifications(data.items);
      setTotal(data.total);
      setLastUpdated(new Date());
    } catch (e: any) {
      setError(e.message || 'Failed to fetch notifications');
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter, readFilter]);

  // Initial fetch + polling
  useEffect(() => {
    fetchNotifications();
    pollRef.current = setInterval(fetchNotifications, POLL_INTERVAL);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchNotifications]);

  const handleMarkAsRead = async (id: number) => {
    setMarkingId(id);
    try {
      await api.updateNotification(id, { read: true });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (e: any) {
      setError(e.message || 'Failed to mark as read');
    } finally {
      setMarkingId(null);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await Promise.all(
        notifications.filter(n => !n.read).map(n => api.updateNotification(n.id, { read: true }))
      );
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (e: any) {
      setError(e.message || 'Failed to mark all as read');
    }
  };

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await api.deleteNotification(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
      setTotal(prev => prev - 1);
    } catch (e: any) {
      setError(e.message || 'Failed to delete notification');
    } finally {
      setDeletingId(null);
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;
  const totalPages = Math.ceil(total / 20);

  return (
    <div className="p-6 max-w-5xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-cyan-400" />
          <h1 className="text-2xl font-bold">Notification Center</h1>
          {unreadCount > 0 && (
            <span className="bg-red-500/20 text-red-300 text-xs font-medium px-2 py-1 rounded-full">
              {unreadCount} unread
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchNotifications}
            disabled={loading}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-500" />
          <select
            value={typeFilter}
            onChange={e => { setTypeFilter(e.target.value); setPage(1); }}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
          >
            <option value="all">All Types</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
            <option value="success">Success</option>
          </select>
        </div>
        <select
          value={readFilter}
          onChange={e => { setReadFilter(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
        >
          <option value="all">All</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
        </select>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="flex items-center gap-1 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <Check size={14} /> Mark all read
          </button>
        )}
      </div>

      {/* Notification List */}
      <div className="space-y-2">
        {loading && notifications.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
            <p>Loading notifications...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Bell size={32} className="mx-auto mb-2 opacity-50" />
            <p>No notifications found</p>
          </div>
        ) : (
          notifications.map(n => (
            <div
              key={n.id}
              className={`flex items-start gap-3 p-4 rounded-lg border transition-colors ${
                n.read
                  ? 'bg-gray-800/50 border-gray-700/50'
                  : 'bg-gray-800 border-gray-700 hover:border-gray-600'
              }`}
            >
              {/* Type Icon */}
              <div className="mt-0.5 shrink-0">
                {typeIcons[n.type] || typeIcons.info}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-sm font-medium ${n.read ? 'text-gray-400' : 'text-gray-100'}`}>
                    {n.title}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${typeBadgeColors[n.type] || typeBadgeColors.info}`}>
                    {n.type}
                  </span>
                  {!n.read && (
                    <span className="w-2 h-2 rounded-full bg-cyan-400 shrink-0" />
                  )}
                </div>
                <p className={`text-sm ${n.read ? 'text-gray-500' : 'text-gray-300'}`}>
                  {n.message}
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0">
                {!n.read && (
                  <button
                    onClick={() => handleMarkAsRead(n.id)}
                    disabled={markingId === n.id}
                    className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-cyan-400 transition-colors disabled:opacity-50"
                    title="Mark as read"
                  >
                    <Check size={14} />
                  </button>
                )}
                <button
                  onClick={() => handleDelete(n.id)}
                  disabled={deletingId === n.id}
                  className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-red-400 transition-colors disabled:opacity-50"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-sm text-gray-500">
            Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-700 rounded text-sm disabled:opacity-50 hover:bg-gray-800 text-gray-300"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm text-gray-500">{page} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 border border-gray-700 rounded text-sm disabled:opacity-50 hover:bg-gray-800 text-gray-300"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationCenter;
