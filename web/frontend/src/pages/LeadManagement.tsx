import React, { useState, useEffect, useCallback } from 'react'
import { fetchWithTimeout } from '../api/fallback'
import { FALLBACK_LEADS } from '../api/fallback'

// ── Types ────────────────────────────────────────────────────────────────────

// "converted" is a status the backend actually returns; without it in the
// union STATUS_STYLES lookup returned undefined for those rows.
type LeadStatus = "new" | "contacted" | "qualified" | "converted" | "lost";

interface Lead {
  id: number;
  name: string;
  email: string;
  phone?: string;
  company?: string;
  status: LeadStatus;
  source?: string;
  notes?: string;
  created_at?: string;
}

interface LeadFormData {
  name: string;
  email: string;
  phone: string;
  company: string;
  status: LeadStatus;
  source: string;
  notes: string;
}

type ApiResponse = Lead[] | { items: Lead[] };

// ── Helpers ──────────────────────────────────────────────────────────────────

function parseLeads(data: ApiResponse): Lead[] {
  let rows: unknown[] = [];
  if (Array.isArray(data)) {
    rows = data;
  } else if (data && typeof data === "object" && "items" in data && Array.isArray(data.items)) {
    rows = data.items;
  }
  // Normalise ids to numbers (the backend sends ints) so delete/update URLs
  // and list keys are always consistent, and drop malformed rows.
  return rows
    .filter((r): r is Lead => Boolean(r) && typeof r === "object")
    .map((r) => ({ ...r, id: Number(r.id) }))
    .filter((r) => Number.isFinite(r.id));
}

const EMPTY_FORM: LeadFormData = {
  name: "",
  email: "",
  phone: "",
  company: "",
  status: "new",
  source: "",
  notes: "",
};

const STATUS_STYLES: Record<LeadStatus, string> = {
  new: "bg-blue-900/40 text-blue-300 border border-blue-700",
  contacted: "bg-yellow-900/40 text-yellow-300 border border-yellow-700",
  qualified: "bg-green-900/40 text-green-300 border border-green-700",
  converted: "bg-emerald-900/40 text-emerald-300 border border-emerald-700",
  lost: "bg-red-900/40 text-red-300 border border-red-700",
};

// ── Component ────────────────────────────────────────────────────────────────

export default function LeadManagement() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<LeadFormData>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "all">("all");

  // ── Filtered leads ────────────────────────────────────────────────────────

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      searchQuery.trim() === "" ||
      lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (lead.company ?? "").toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || lead.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // ── Fetch ─────────────────────────────────────────────────────────────────

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetchWithTimeout("/api/leads/", { headers: { 'X-API-Key': 'test-api-key-12345' }, signal: controller.signal });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`Failed to fetch leads (${res.status})`);
      const data: ApiResponse = await res.json();
      setLeads(parseLeads(data));
    } catch (err) {
      // Fallback to synthetic data when API is unreachable
      setLeads(FALLBACK_LEADS.map((l) => ({ ...l, id: Number(l.id) })) as Lead[]);
      setError("API unavailable — showing sample data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // ── Mutations ─────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const url = editingId ? `/api/leads/${editingId}/` : "/api/leads/";
      const method = editingId ? "PUT" : "POST";
      const res = await fetchWithTimeout(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      await fetchLeads();
      setForm(EMPTY_FORM);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (lead: Lead) => {
    setEditingId(lead.id);
    setForm({
      name: lead.name,
      email: lead.email,
      phone: lead.phone ?? "",
      company: lead.company ?? "",
      status: lead.status,
      source: lead.source ?? "",
      notes: lead.notes ?? "",
    });
  };

  const handleDelete = async (id: number) => {
    setError(null);
    setDeleting(true);
    try {
      const res = await fetchWithTimeout(`/api/leads/${id}/`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
      setLeads((prev) => prev.filter((l) => l.id !== id));
      setShowDeleteConfirm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">Lead Management</h1>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 rounded bg-red-900/50 border border-red-700 text-red-200 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold">
            ✕
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-gray-800 rounded-lg p-4 mb-6 space-y-3">
        <h2 className="text-lg font-semibold">{editingId ? "Edit Lead" : "New Lead"}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            required
            placeholder="Name *"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            required
            type="email"
            placeholder="Email *"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            placeholder="Phone"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            placeholder="Company"
            value={form.company}
            onChange={(e) => setForm({ ...form, company: e.target.value })}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value as LeadStatus })}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>
          <input
            placeholder="Source"
            value={form.source}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <textarea
          placeholder="Notes"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          rows={2}
          className="w-full bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-2 rounded font-medium"
          >
            {submitting ? "Saving…" : editingId ? "Update Lead" : "Add Lead"}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={handleCancel}
              className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded"
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {/* Export buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => {
            const headers = ['ID', 'Name', 'Email', 'Phone', 'Company', 'Status', 'Source'];
            const rows = leads.map(l => [l.id, l.name, l.email, l.phone, l.company, l.status, l.source]);
            const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'leads_export.csv';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-medium"
        >
          Export CSV
        </button>
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(leads, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'leads_export.json';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded font-medium"
        >
          Export JSON
        </button>
      </div>

      {/* Search & Filter */}
      {!loading && leads.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <input
            type="text"
            placeholder="Search by name, email, or company…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as LeadStatus | "all")}
            className="bg-gray-700 text-gray-100 rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12 text-gray-400">
          <div className="inline-block w-6 h-6 border-2 border-gray-500 border-t-blue-400 rounded-full animate-spin mr-2" />
          Loading leads…
        </div>
      )}

      {/* Empty state */}
      {!loading && leads.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">No leads yet</p>
          <p className="text-sm mt-1">Add your first lead using the form above.</p>
        </div>
      )}

      {/* No results */}
      {!loading && leads.length > 0 && filteredLeads.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">No leads match your search</p>
          <p className="text-sm mt-1">Try adjusting your search or filter.</p>
        </div>
      )}

      {/* Table */}
      {!loading && filteredLeads.length > 0 && (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-700 text-gray-300">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Email</th>
                <th className="text-left px-4 py-3">Company</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Source</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredLeads.map((lead) => (
                <tr key={lead.id} className="border-t border-gray-700 hover:bg-gray-600">
                  <td className="px-4 py-3 font-medium">{lead.name}</td>
                  <td className="px-4 py-3 text-gray-300">{lead.email}</td>
                  <td className="px-4 py-3 text-gray-300">{lead.company ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_STYLES[lead.status]}`}>
                      {lead.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{lead.source ?? "—"}</td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => handleEdit(lead)}
                      className="text-blue-400 hover:text-blue-300 font-medium"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(lead.id)}
                      className="text-red-400 hover:text-red-300 font-medium"
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-100 mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this lead? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} disabled={deleting} className="rounded bg-gray-700 hover:bg-gray-600 px-4 py-2 text-gray-200 disabled:opacity-50">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} disabled={deleting} className="rounded bg-red-600 hover:bg-red-700 px-4 py-2 text-white disabled:opacity-50">
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}