import React, { useState, useEffect, useCallback, useMemo } from 'react';

interface Lead {
  id: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  value: number;
  status: 'New' | 'Contacted' | 'Qualified' | 'Proposal' | 'Negotiation' | 'Won' | 'Lost';
  score: number;
  createdAt: string;
  updatedAt: string;
}

type LeadFormData = Omit<Lead, 'id' | 'createdAt' | 'updatedAt' | 'score'>;

const STATUSES: Lead['status'][] = ['New', 'Contacted', 'Qualified', 'Proposal', 'Negotiation', 'Won', 'Lost'];
const PIPELINE_STAGES = ['New', 'Contacted', 'Qualified', 'Proposal', 'Negotiation', 'Won', 'Lost'] as const;

const API_BASE = '/api/leads';

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

function calculateScore(lead: Partial<LeadFormData>): number {
  let score = 0;
  if (lead.email) score += 20;
  if (lead.phone) score += 15;
  if (lead.company) score += 15;
  if (lead.value && lead.value > 10000) score += 25;
  else if (lead.value && lead.value > 5000) score += 15;
  else if (lead.value) score += 10;
  if (lead.status === 'Won') score += 25;
  else if (lead.status === 'Negotiation') score += 20;
  else if (lead.status === 'Proposal') score += 15;
  else if (lead.status === 'Qualified') score += 10;
  else if (lead.status === 'Contacted') score += 5;
  return Math.min(score, 100);
}

const emptyForm: LeadFormData = { name: '', company: '', email: '', phone: '', value: 0, status: 'New' };

export default function LeadManagement() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [scoreFilter, setScoreFilter] = useState<string>('All');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [view, setView] = useState<'list' | 'create' | 'edit' | 'details' | 'pipeline'>('list');
  const [form, setForm] = useState<LeadFormData>(emptyForm);
  const [detailLead, setDetailLead] = useState<Lead | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [bulkAction, setBulkAction] = useState<string>('');
  const [showScoring, setShowScoring] = useState(false);
  const perPage = 10;

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(perPage) });
      if (search) params.set('search', search);
      if (statusFilter !== 'All') params.set('status', statusFilter);
      if (scoreFilter !== 'All') params.set('minScore', scoreFilter);
      const data = await api<{ leads: Lead[]; total: number }>(`${API_BASE}?${params}`);
      setLeads(data.leads);
      setTotalPages(Math.ceil(data.total / perPage));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch leads');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, scoreFilter]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const openCreate = () => { setForm(emptyForm); setView('create'); };
  const openEdit = (lead: Lead) => {
    setForm({ name: lead.name, company: lead.company, email: lead.email, phone: lead.phone, value: lead.value, status: lead.status });
    setDetailLead(lead);
    setView('edit');
  };
  const openDetails = (lead: Lead) => { setDetailLead(lead); setView('details'); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const score = calculateScore(form);
      if (view === 'create') {
        await api(API_BASE, { method: 'POST', body: JSON.stringify({ ...form, score }) });
      } else if (view === 'edit' && detailLead) {
        await api(`${API_BASE}/${detailLead.id}`, { method: 'PUT', body: JSON.stringify({ ...form, score }) });
      }
      setView('list');
      fetchLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api(`${API_BASE}/${id}`, { method: 'DELETE' });
      setShowDeleteConfirm(null);
      fetchLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleBulkAction = async () => {
    if (!bulkAction || selected.size === 0) return;
    try {
      if (bulkAction === 'delete') {
        await Promise.all([...selected].map(id => api(`${API_BASE}/${id}`, { method: 'DELETE' })));
      } else {
        await Promise.all([...selected].map(id => api(`${API_BASE}/${id}`, { method: 'PUT', body: JSON.stringify({ status: bulkAction }) })));
      }
      setSelected(new Set());
      setBulkAction('');
      fetchLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk action failed');
    }
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const toggleAll = () => {
    if (selected.size === leads.length) setSelected(new Set());
    else setSelected(new Set(leads.map(l => l.id)));
  };

  const pipelineData = useMemo(() => {
    return PIPELINE_STAGES.map(stage => ({
      stage,
      count: leads.filter(l => l.status === stage).length,
      value: leads.filter(l => l.status === stage).reduce((s, l) => s + l.value, 0),
    }));
  }, [leads]);

  const scoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600 bg-green-100';
    if (score >= 50) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const statusColor = (status: string) => {
    const colors: Record<string, string> = {
      New: 'bg-blue-100 text-blue-800', Contacted: 'bg-purple-100 text-purple-800',
      Qualified: 'bg-indigo-100 text-indigo-800', Proposal: 'bg-orange-100 text-orange-800',
      Negotiation: 'bg-yellow-100 text-yellow-800', Won: 'bg-green-100 text-green-800',
      Lost: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (view === 'pipeline') {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Lead Pipeline</h1>
          <button onClick={() => setView('list')} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">Back to List</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
          {pipelineData.map(({ stage, count, value }) => (
            <div key={stage} className="border rounded-lg p-4 text-center">
              <div className="font-semibold mb-2">{stage}</div>
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-sm text-gray-500">${value.toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (view === 'create' || view === 'edit') {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{view === 'create' ? 'Create Lead' : 'Edit Lead'}</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div><label className="block text-sm font-medium mb-1">Name *</label>
            <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full border rounded px-3 py-2" /></div>
          <div><label className="block text-sm font-medium mb-1">Company</label>
            <input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} className="w-full border rounded px-3 py-2" /></div>
          <div><label className="block text-sm font-medium mb-1">Email</label>
            <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="w-full border rounded px-3 py-2" /></div>
          <div><label className="block text-sm font-medium mb-1">Phone</label>
            <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} className="w-full border rounded px-3 py-2" /></div>
          <div><label className="block text-sm font-medium mb-1">Value ($)</label>
            <input type="number" value={form.value} onChange={e => setForm({ ...form, value: Number(e.target.value) })} className="w-full border rounded px-3 py-2" /></div>
          <div><label className="block text-sm font-medium mb-1">Status</label>
            <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value as Lead['status'] })} className="w-full border rounded px-3 py-2">
              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select></div>
          <div className="flex gap-3">
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">{view === 'create' ? 'Create' : 'Update'}</button>
            <button type="button" onClick={() => setView('list')} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">Cancel</button>
          </div>
        </form>
      </div>
    );
  }

  if (view === 'details' && detailLead) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Lead Details</h1>
          <button onClick={() => setView('list')} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">Back</button>
        </div>
        <div className="bg-white border rounded-lg p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div><span className="text-sm text-gray-500">Name</span><p className="font-medium">{detailLead.name}</p></div>
            <div><span className="text-sm text-gray-500">Company</span><p className="font-medium">{detailLead.company}</p></div>
            <div><span className="text-sm text-gray-500">Email</span><p className="font-medium">{detailLead.email}</p></div>
            <div><span className="text-sm text-gray-500">Phone</span><p className="font-medium">{detailLead.phone}</p></div>
            <div><span className="text-sm text-gray-500">Value</span><p className="font-medium">${detailLead.value.toLocaleString()}</p></div>
            <div><span className="text-sm text-gray-500">Status</span><span className={`ml-2 px-2 py-1 rounded text-sm ${statusColor(detailLead.status)}`}>{detailLead.status}</span></div>
          </div>
          <div className="border-t pt-4">
            <h3 className="font-semibold mb-2">Lead Score</h3>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-gray-200 rounded-full h-4"><div className="bg-blue-600 h-4 rounded-full" style={{ width: `${detailLead.score}%` }} /></div>
              <span className={`px-3 py-1 rounded font-bold ${scoreColor(detailLead.score)}`}>{detailLead.score}/100</span>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => openEdit(detailLead)} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Edit</button>
            <button onClick={() => setShowDeleteConfirm(detailLead.id)} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Lead Management</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowScoring(!showScoring)} className="px-4 py-2 bg-purple-100 text-purple-800 rounded hover:bg-purple-200">Scoring</button>
          <button onClick={() => setView('pipeline')} className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">Pipeline</button>
          <button onClick={openCreate} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">+ New Lead</button>
        </div>
      </div>

      {showScoring && (
        <div className="mb-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h3 className="font-semibold mb-2">Lead Scoring Algorithm</h3>
          <ul className="text-sm space-y-1 text-purple-900">
            <li>• Email provided: +20 points</li>
            <li>• Phone provided: +15 points</li>
            <li>• Company provided: +15 points</li>
            <li>• Value &gt; $10,000: +25 | &gt; $5,000: +15 | &gt; $0: +10</li>
            <li>• Status: Won +25 | Negotiation +20 | Proposal +15 | Qualified +10 | Contacted +5</li>
            <li>• Maximum score: 100</li>
          </ul>
        </div>
      )}

      {error && <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">{error}</div>}

      <div className="flex flex-wrap gap-3 mb-4">
        <input placeholder="Search leads..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} className="border rounded px-3 py-2 w-64" />
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} className="border rounded px-3 py-2">
          <option value="All">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={scoreFilter} onChange={e => { setScoreFilter(e.target.value); setPage(1); }} className="border rounded px-3 py-2">
          <option value="All">All Scores</option>
          <option value="75">75+ (Hot)</option>
          <option value="50">50+ (Warm)</option>
          <option value="25">25+ (Cold)</option>
        </select>
      </div>

      {selected.size > 0 && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-blue-50 rounded">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <select value={bulkAction} onChange={e => setBulkAction(e.target.value)} className="border rounded px-2 py-1 text-sm">
            <option value="">Bulk Action</option>
            <option value="Contacted">Mark Contacted</option>
            <option value="Qualified">Mark Qualified</option>
            <option value="Proposal">Mark Proposal</option>
            <option value="delete">Delete Selected</option>
          </select>
          <button onClick={handleBulkAction} className="px-3 py-1 bg-blue-600 text-white rounded text-sm">Apply</button>
          <button onClick={() => { setSelected(new Set()); setBulkAction(''); }} className="px-3 py-1 bg-gray-200 rounded text-sm">Clear</button>
        </div>
      )}

      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left"><input type="checkbox" checked={selected.size === leads.length && leads.length > 0} onChange={toggleAll} /></th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Company</th>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Value</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Score</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : leads.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">No leads found</td></tr>
            ) : leads.map(lead => (
              <tr key={lead.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3"><input type="checkbox" checked={selected.has(lead.id)} onChange={() => toggleSelect(lead.id)} /></td>
                <td className="px-4 py-3 font-medium cursor-pointer text-blue-600" onClick={() => openDetails(lead)}>{lead.name}</td>
                <td className="px-4 py-3">{lead.company}</td>
                <td className="px-4 py-3">{lead.email}</td>
                <td className="px-4 py-3">${lead.value.toLocaleString()}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs ${statusColor(lead.status)}`}>{lead.status}</span></td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-bold ${scoreColor(lead.score)}`}>{lead.score}</span></td>
                <td className="px-4 py-3">
                  <button onClick={() => openEdit(lead)} className="text-blue-600 hover:underline mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(lead.id)} className="text-red-600 hover:underline text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between items-center mt-4">
        <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
        <div className="flex gap-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-bold mb-2">Confirm Delete</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to delete this lead? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 bg-gray-200 rounded">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="px-4 py-2 bg-red-600 text-white rounded">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
