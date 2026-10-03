import React, { useState, useEffect, useCallback } from "react";

interface CRMRecord {
  id: number;
  name: string;
  email: string;
  phone: string;
  company: string;
  status: string;
}

const API = "/api/crm";
const PAGE_SIZE = 10;
const emptyForm = { name: "", email: "", phone: "", company: "", status: "lead" };

export default function CRMCRUD() {
  const [records, setRecords] = useState<CRMRecord[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE), ...(search && { search }), ...(filterStatus && { status: filterStatus }) });
      const res = await fetch(`${API}?${params}`);
      if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
      const data = await res.json();
      setRecords(data.records || data);
      setTotal(data.total || (data.records || data).length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load records");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterStatus]);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);
    try {
      const res = await fetch(editingId ? `${API}/${editingId}` : API, {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      setForm({ ...emptyForm });
      setEditingId(null);
      setShowForm(false);
      fetchRecords();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save record");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (r: CRMRecord) => {
    setForm({ name: r.name, email: r.email, phone: r.phone, company: r.company, status: r.status });
    setEditingId(r.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`${API}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
      setConfirmDelete(null);
      fetchRecords();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete record");
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">CRM Management</h1>
      {error && <div className="bg-red-100 text-red-700 p-2 rounded mb-4">{error}</div>}

      <div className="flex gap-2 mb-4 flex-wrap">
        <input className="border rounded px-3 py-2 flex-1 min-w-[200px]" placeholder="Search name, email, company..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        <select className="border rounded px-3 py-2" value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          <option value="lead">Lead</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700" onClick={() => { setShowForm(true); setEditingId(null); setForm({ ...emptyForm }); }}>+ New CRM</button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white shadow rounded p-4 mb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <input required placeholder="Name *" className="border rounded px-3 py-2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input required type="email" placeholder="Email *" className="border rounded px-3 py-2" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input placeholder="Phone" className="border rounded px-3 py-2" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <input placeholder="Company" className="border rounded px-3 py-2" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <select className="border rounded px-3 py-2" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option value="lead">Lead</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">{editingId ? "Update" : "Create"}</button>
            <button type="button" className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400" onClick={() => { setShowForm(false); setEditingId(null); }}>Cancel</button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto bg-white shadow rounded">
        {loading ? (
          <div className="px-4 py-8 text-center text-gray-500">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Name</th><th className="px-4 py-2 text-left">Email</th><th className="px-4 py-2 text-left">Phone</th><th className="px-4 py-2 text-left">Company</th><th className="px-4 py-2 text-left">Status</th><th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">{r.name}</td><td className="px-4 py-2">{r.email}</td><td className="px-4 py-2">{r.phone}</td><td className="px-4 py-2">{r.company}</td>
                  <td className="px-4 py-2"><span className={`px-2 py-1 rounded text-xs ${r.status === "active" ? "bg-green-100 text-green-700" : r.status === "lead" ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-700"}`}>{r.status}</span></td>
                  <td className="px-4 py-2 flex gap-2">
                    <button className="text-blue-600 hover:underline" onClick={() => handleEdit(r)}>Edit</button>
                    {confirmDelete === r.id ? (
                      <>
                        <button className="text-red-600 font-bold hover:underline" onClick={() => handleDelete(r.id)}>Confirm</button>
                        <button className="text-gray-500 hover:underline" onClick={() => setConfirmDelete(null)}>Cancel</button>
                      </>
                    ) : (
                      <button className="text-red-600 hover:underline" onClick={() => setConfirmDelete(r.id)}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
              {records.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No records found</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex items-center gap-4 mt-4 justify-center">
        <button className="px-3 py-1 border rounded disabled:opacity-50" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>Prev</button>
        <span className="text-sm">Page {page} of {totalPages || 1}</span>
        <button className="px-3 py-1 border rounded disabled:opacity-50" disabled={page >= totalPages || loading} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}
