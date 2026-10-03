import { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Column { name: string; type: string; }
interface Record { [key: string]: any; }
interface TableDef { name: string; endpoint: string; columns: Column[]; }

// ─── Table Definitions (20+ endpoints) ──────────────────────────────────────
const TABLES: TableDef[] = [
  { name: 'users', endpoint: '/api/users', columns: [{name:'id',type:'int'},{name:'name',type:'string'},{name:'email',type:'string'},{name:'role',type:'string'}] },
  { name: 'leads', endpoint: '/api/leads', columns: [{name:'id',type:'int'},{name:'name',type:'string'},{name:'email',type:'string'},{name:'status',type:'string'}] },
  { name: 'reports', endpoint: '/api/reports', columns: [{name:'id',type:'int'},{name:'title',type:'string'},{name:'type',type:'string'},{name:'created_at',type:'datetime'}] },
  { name: 'dashboard', endpoint: '/api/dashboard', columns: [{name:'id',type:'int'},{name:'widget',type:'string'},{name:'config',type:'json'}] },
  { name: 'accounting', endpoint: '/api/accounting', columns: [{name:'id',type:'int'},{name:'account',type:'string'},{name:'balance',type:'float'}] },
  { name: 'analytics', endpoint: '/api/analytics', columns: [{name:'id',type:'int'},{name:'metric',type:'string'},{name:'value',type:'float'}] },
  { name: 'agent-reach', endpoint: '/api/agent-reach', columns: [{name:'id',type:'int'},{name:'agent',type:'string'},{name:'reach',type:'int'}] },
  { name: 'bigdata', endpoint: '/api/bigdata', columns: [{name:'id',type:'int'},{name:'dataset',type:'string'},{name:'size',type:'int'}] },
  { name: 'datascience', endpoint: '/api/datascience', columns: [{name:'id',type:'int'},{name:'model',type:'string'},{name:'accuracy',type:'float'}] },
  { name: 'continuous-bi', endpoint: '/api/continuous-bi', columns: [{name:'id',type:'int'},{name:'pipeline',type:'string'},{name:'status',type:'string'}] },
  { name: 'products', endpoint: '/api/products', columns: [{name:'id',type:'int'},{name:'name',type:'string'},{name:'price',type:'float'},{name:'stock',type:'int'}] },
  { name: 'orders', endpoint: '/api/orders', columns: [{name:'id',type:'int'},{name:'customer_id',type:'int'},{name:'total',type:'float'},{name:'status',type:'string'}] },
  { name: 'customers', endpoint: '/api/customers', columns: [{name:'id',type:'int'},{name:'name',type:'string'},{name:'email',type:'string'}] },
  { name: 'employees', endpoint: '/api/employees', columns: [{name:'id',type:'int'},{name:'name',type:'string'},{name:'department',type:'string'}] },
  { name: 'projects', endpoint: '/api/projects', columns: [{name:'id',type:'int'},{name:'name',type:'string'},{name:'status',type:'string'}] },
  { name: 'tasks', endpoint: '/api/tasks', columns: [{name:'id',type:'int'},{name:'title',type:'string'},{name:'assignee',type:'string'},{name:'done',type:'bool'}] },
  { name: 'inventory', endpoint: '/api/inventory', columns: [{name:'id',type:'int'},{name:'item',type:'string'},{name:'quantity',type:'int'}] },
  { name: 'payments', endpoint: '/api/payments', columns: [{name:'id',type:'int'},{name:'amount',type:'float'},{name:'method',type:'string'}] },
  { name: 'notifications', endpoint: '/api/notifications', columns: [{name:'id',type:'int'},{name:'message',type:'string'},{name:'read',type:'bool'}] },
  { name: 'audit-logs', endpoint: '/api/audit-logs', columns: [{name:'id',type:'int'},{name:'action',type:'string'},{name:'timestamp',type:'datetime'}] },
  { name: 'journal-entries', endpoint: '/api/journal-entries', columns: [{name:'id',type:'int'},{name:'debit',type:'float'},{name:'credit',type:'float'}] },
  { name: 'invoices', endpoint: '/api/invoices', columns: [{name:'id',type:'int'},{name:'number',type:'string'},{name:'amount',type:'float'}] },
];

// ─── API Helper ──────────────────────────────────────────────────────────────
const api = {
  base: (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000'),
  async req(method: string, path: string, body?: any) {
    const res = await fetch(`${this.base}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`${method} ${path} → ${res.status}`);
    return res.json();
  },
  get: (p: string) => api.req('GET', p),
  post: (p: string, b: any) => api.req('POST', p, b),
  put: (p: string, b: any) => api.req('PUT', p, b),
  del: (p: string) => api.req('DELETE', p),
};

// ─── CSV Export ──────────────────────────────────────────────────────────────
function toCSV(rows: Record[]): string {
  if (!rows.length) return '';
  const keys = Object.keys(rows[0]);
  const esc = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  return [keys.join(','), ...rows.map(r => keys.map(k => esc(r[k])).join(','))].join('\n');
}
function download(filename: string, content: string, mime: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content], { type: mime }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ─── Main Component ──────────────────────────────────────────────────────────
export default function DatabaseAdmin() {
  const [active, setActive] = useState<TableDef>(TABLES[0]);
  const [rows, setRows] = useState<Record[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showSchema, setShowSchema] = useState(false);
  const [editing, setEditing] = useState<Record | null>(null);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [form, setForm] = useState<Record>({});

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setRows(await api.get(active.endpoint)); }
    catch (e: any) { setError(e.message); setRows([]); }
    finally { setLoading(false); }
  }, [active]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setForm({}); setCreating(true); setEditing(null); };
  const openEdit = (r: Record) => { setForm({ ...r }); setEditing(r); setCreating(false); };
  const closeForm = () => { setEditing(null); setCreating(false); setForm({}); };

  const save = async () => {
    try {
      if (creating) await api.post(active.endpoint, form);
      else if (editing) await api.put(`${active.endpoint}/${editing.id}`, form);
      closeForm(); load();
    } catch (e: any) { setError(e.message); }
  };

  const remove = async (id: number) => {
    if (!confirm('Delete this record?')) return;
    try { await api.del(`${active.endpoint}/${id}`); load(); }
    catch (e: any) { setError(e.message); }
  };

  const bulkDelete = async () => {
    if (!selected.size || !confirm(`Delete ${selected.size} records?`)) return;
    try {
      await Promise.all([...selected].map(id => api.del(`${active.endpoint}/${id}`)));
      setSelected(new Set()); load();
    } catch (e: any) { setError(e.message); }
  };

  const toggleSelect = (id: number) => {
    const s = new Set(selected);
    s.has(id) ? s.delete(id) : s.add(id);
    setSelected(s);
  };

  const exportData = (fmt: 'csv' | 'json') => {
    const name = `${active.name}.${fmt}`;
    fmt === 'csv'
      ? download(name, toCSV(rows), 'text/csv')
      : download(name, JSON.stringify(rows, null, 2), 'application/json');
  };

  const cols = rows.length ? Object.keys(rows[0]) : active.columns.map(c => c.name);

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-800 border-r border-gray-700 overflow-y-auto p-4">
        <h2 className="text-lg font-bold mb-4 text-blue-400">DB Admin</h2>
        <ul className="space-y-1">
          {TABLES.map(t => (
            <li key={t.name}>
              <button
                onClick={() => { setActive(t); setSelected(new Set()); }}
                className={`w-full text-left px-3 py-2 rounded text-sm transition ${active.name === t.name ? 'bg-blue-600 text-white' : 'hover:bg-gray-700'}`}
              >
                {t.name}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-3 p-4 bg-gray-800 border-b border-gray-700 flex-wrap">
          <h1 className="text-xl font-semibold capitalize">{active.name}</h1>
          <span className="text-xs text-gray-400">{active.endpoint}</span>
          <div className="ml-auto flex gap-2 flex-wrap">
            <button onClick={openCreate} className="px-3 py-1.5 bg-green-600 hover:bg-green-500 rounded text-sm">+ New</button>
            <button onClick={() => setShowSchema(!showSchema)} className="px-3 py-1.5 bg-gray-600 hover:bg-gray-500 rounded text-sm">Schema</button>
            <button onClick={() => exportData('csv')} className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded text-sm">CSV</button>
            <button onClick={() => exportData('json')} className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded text-sm">JSON</button>
            {selected.size > 0 && (
              <button onClick={bulkDelete} className="px-3 py-1.5 bg-red-600 hover:bg-red-500 rounded text-sm">Delete ({selected.size})</button>
            )}
          </div>
        </div>

        {error && <div className="px-4 py-2 bg-red-900/50 text-red-300 text-sm">{error}</div>}

        {/* Schema Panel */}
        {showSchema && (
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-700">
            <h3 className="text-sm font-semibold mb-2 text-gray-300">Schema</h3>
            <div className="flex flex-wrap gap-2">
              {active.columns.map(c => (
                <span key={c.name} className="px-2 py-1 bg-gray-700 rounded text-xs">
                  <span className="text-blue-300">{c.name}</span>
                  <span className="text-gray-400 ml-1">{c.type}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-8 text-center text-gray-400">Loading…</div>
          ) : rows.length === 0 ? (
            <div className="p-8 text-center text-gray-400">No records</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr>
                  <th className="px-3 py-2 w-10"></th>
                  {cols.map(c => <th key={c} className="px-3 py-2 text-left font-medium text-gray-300">{c}</th>)}
                  <th className="px-3 py-2 w-28">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={r.id ?? i} className="border-t border-gray-700 hover:bg-gray-800/50">
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)} className="rounded" />
                    </td>
                    {cols.map(c => <td key={c} className="px-3 py-2 max-w-xs truncate">{String(r[c] ?? '')}</td>)}
                    <td className="px-3 py-2">
                      <button onClick={() => openEdit(r)} className="text-blue-400 hover:underline mr-2">Edit</button>
                      <button onClick={() => remove(r.id)} className="text-red-400 hover:underline">Del</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {/* Modal */}
      {(creating || editing) && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={closeForm}>
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">{creating ? 'Create' : 'Edit'} — {active.name}</h3>
            <div className="space-y-3">
              {cols.filter(c => c !== 'id').map(c => (
                <div key={c}>
                  <label className="block text-xs text-gray-400 mb-1">{c}</label>
                  <input
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm"
                    value={form[c] ?? ''}
                    onChange={e => setForm({ ...form, [c]: e.target.value })}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={closeForm} className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm">Cancel</button>
              <button onClick={save} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
