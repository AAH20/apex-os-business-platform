import React, { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface ProductionLine {
  id: number;
  name: string;
  code: string;
  status: string;
  capacity_per_hour: number;
  location: string;
  supervisor: string;
}

interface WorkOrder {
  id: number;
  product_name: string;
  quantity: number;
  production_line_id: number;
  priority: string;
  status: string;
  due_date: string;
  notes: string;
}

interface QualityCheck {
  id: number;
  work_order_id: number;
  inspector: string;
  result: string;
  defect_count: number;
  notes: string;
}

interface BOMItem {
  material_name: string;
  quantity: number;
  unit: string;
}

interface BillOfMaterials {
  id: number;
  product_name: string;
  version: string;
  items: BOMItem[];
  notes: string;
}

type Tab = 'production-lines' | 'work-orders' | 'quality-checks' | 'bills-of-materials';

const EMPTY_LINE = { name: '', code: '', status: 'active', capacity_per_hour: 0, location: '', supervisor: '' };
const EMPTY_ORDER = { product_name: '', quantity: 0, production_line_id: 0, priority: 'normal', status: 'pending', due_date: '', notes: '' };
const EMPTY_CHECK = { work_order_id: 0, inspector: '', result: 'pending', defect_count: 0, notes: '' };
const EMPTY_BOM = { product_name: '', version: '1.0', items: [{ material_name: '', quantity: 0, unit: 'pcs' }], notes: '' };

const _PAGE_SIZE = 10;

export default function ManufacturingManagement() {
  const [tab, setTab] = useState<Tab>('production-lines');
  const [lines, setLines] = useState<ProductionLine[]>([]);
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [checks, setChecks] = useState<QualityCheck[]>([]);
  const [boms, setBoms] = useState<BillOfMaterials[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showDelete, setShowDelete] = useState<{ id: number; tab: Tab } | null>(null);

  // Form states
  const [lineForm, setLineForm] = useState({ ...EMPTY_LINE });
  const [editingLineId, setEditingLineId] = useState<number | null>(null);
  const [orderForm, setOrderForm] = useState({ ...EMPTY_ORDER });
  const [editingOrderId, setEditingOrderId] = useState<number | null>(null);
  const [checkForm, setCheckForm] = useState({ ...EMPTY_CHECK });
  const [editingCheckId, setEditingCheckId] = useState<number | null>(null);
  const [bomForm, setBomForm] = useState({ ...EMPTY_BOM });
  const [editingBomId, setEditingBomId] = useState<number | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [lr, or, qr, br] = await Promise.all([
        fetch('/api/manufacturing/production-lines/'),
        fetch('/api/manufacturing/work-orders/'),
        fetch('/api/manufacturing/quality-checks/'),
        fetch('/api/manufacturing/bills-of-materials/'),
      ]);
      setLines(await lr.json());
      setOrders(await or.json());
      setChecks(await qr.json());
      setBoms(await br.json());
    } catch {
      setError('Failed to load manufacturing data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ─── Production Lines CRUD ──────────────────────────────────────────────

  const submitLine = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingLineId) {
        await fetch(`/api/manufacturing/production-lines/${editingLineId}/`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(lineForm),
        });
      } else {
        await fetch('/api/manufacturing/production-lines/', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(lineForm),
        });
      }
      setLineForm({ ...EMPTY_LINE }); setEditingLineId(null); fetchAll();
    } catch { setError('Save failed'); }
  };

  const editLine = (l: ProductionLine) => {
    setLineForm({ name: l.name, code: l.code, status: l.status, capacity_per_hour: l.capacity_per_hour, location: l.location, supervisor: l.supervisor });
    setEditingLineId(l.id);
  };

  // ─── Work Orders CRUD ───────────────────────────────────────────────────

  const submitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingOrderId) {
        await fetch(`/api/manufacturing/work-orders/${editingOrderId}/`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(orderForm),
        });
      } else {
        await fetch('/api/manufacturing/work-orders/', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(orderForm),
        });
      }
      setOrderForm({ ...EMPTY_ORDER }); setEditingOrderId(null); fetchAll();
    } catch { setError('Save failed'); }
  };

  const editOrder = (o: WorkOrder) => {
    setOrderForm({ product_name: o.product_name, quantity: o.quantity, production_line_id: o.production_line_id, priority: o.priority, status: o.status, due_date: o.due_date, notes: o.notes });
    setEditingOrderId(o.id);
  };

  // ─── Quality Checks CRUD ────────────────────────────────────────────────

  const submitCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingCheckId) {
        await fetch(`/api/manufacturing/quality-checks/${editingCheckId}/`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(checkForm),
        });
      } else {
        await fetch('/api/manufacturing/quality-checks/', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(checkForm),
        });
      }
      setCheckForm({ ...EMPTY_CHECK }); setEditingCheckId(null); fetchAll();
    } catch { setError('Save failed'); }
  };

  const editCheck = (c: QualityCheck) => {
    setCheckForm({ work_order_id: c.work_order_id, inspector: c.inspector, result: c.result, defect_count: c.defect_count, notes: c.notes });
    setEditingCheckId(c.id);
  };

  // ─── Bills of Materials CRUD ────────────────────────────────────────────

  const submitBom = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingBomId) {
        await fetch(`/api/manufacturing/bills-of-materials/${editingBomId}/`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bomForm),
        });
      } else {
        await fetch('/api/manufacturing/bills-of-materials/', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bomForm),
        });
      }
      setBomForm({ ...EMPTY_BOM }); setEditingBomId(null); fetchAll();
    } catch { setError('Save failed'); }
  };

  const editBom = (b: BillOfMaterials) => {
    setBomForm({ product_name: b.product_name, version: b.version, items: b.items.map(i => ({ ...i })), notes: b.notes });
    setEditingBomId(b.id);
  };

  const updateBomItem = (idx: number, field: keyof BOMItem, value: string | number) => {
    const items = [...bomForm.items];
    items[idx] = { ...items[idx], [field]: value };
    setBomForm({ ...bomForm, items });
  };

  const addBomItem = () => setBomForm({ ...bomForm, items: [...bomForm.items, { material_name: '', quantity: 0, unit: 'pcs' }] });
  const removeBomItem = (idx: number) => setBomForm({ ...bomForm, items: bomForm.items.filter((_, i) => i !== idx) });

  // ─── Delete ─────────────────────────────────────────────────────────────

  const handleDelete = async () => {
    if (!showDelete) return;
    try {
      await fetch(`/api/manufacturing/${showDelete.tab}/${showDelete.id}/`, { method: 'DELETE' });
      setShowDelete(null); fetchAll();
    } catch { setError('Delete failed'); }
  };

  // ─── Helpers ─────────────────────────────────────────────────────────────

  const statusColor = (s: string) => {
    const map: Record<string, string> = {
      active: 'text-emerald-400', inactive: 'text-gray-400', maintenance: 'text-amber-400',
      pending: 'text-yellow-400', in_progress: 'text-blue-400', completed: 'text-emerald-400', cancelled: 'text-red-400',
      pass: 'text-emerald-400', fail: 'text-red-400',
      low: 'text-gray-400', normal: 'text-blue-400', high: 'text-amber-400', urgent: 'text-red-400',
    };
    return map[s] || 'text-gray-400';
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'production-lines', label: 'Production Lines' },
    { key: 'work-orders', label: 'Work Orders' },
    { key: 'quality-checks', label: 'Quality Checks' },
    { key: 'bills-of-materials', label: 'Bills of Materials' },
  ];

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">Manufacturing Management</h1>

      {error && <div className="bg-red-900 text-red-200 p-3 rounded mb-4">{error}</div>}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.key ? 'bg-cyan-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="text-center py-8">Loading...</div>}

      {/* ─── Production Lines ─────────────────────────────────────────────── */}
      {!loading && tab === 'production-lines' && (
        <>
          <form onSubmit={submitLine} className="bg-gray-800 p-4 rounded-lg mb-6">
            <h2 className="text-lg font-semibold mb-3">{editingLineId ? 'Edit Line' : 'Add Line'}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Name" value={lineForm.name} onChange={e => setLineForm({ ...lineForm, name: e.target.value })} required />
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Code" value={lineForm.code} onChange={e => setLineForm({ ...lineForm, code: e.target.value })} required />
              <select className="bg-gray-700 text-gray-100 p-2 rounded" value={lineForm.status} onChange={e => setLineForm({ ...lineForm, status: e.target.value })}>
                <option value="active">Active</option><option value="inactive">Inactive</option><option value="maintenance">Maintenance</option>
              </select>
              <input className="bg-gray-700 text-gray-100 p-2 rounded" type="number" placeholder="Capacity/hr" value={lineForm.capacity_per_hour} onChange={e => setLineForm({ ...lineForm, capacity_per_hour: Number(e.target.value) })} required />
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Location" value={lineForm.location} onChange={e => setLineForm({ ...lineForm, location: e.target.value })} />
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Supervisor" value={lineForm.supervisor} onChange={e => setLineForm({ ...lineForm, supervisor: e.target.value })} />
              <div className="flex gap-2">
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex-1">{editingLineId ? 'Update' : 'Add'}</button>
                {editingLineId && <button type="button" onClick={() => { setLineForm({ ...EMPTY_LINE }); setEditingLineId(null); }} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">Cancel</button>}
              </div>
            </div>
          </form>
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700"><tr><th className="p-3 text-left">Name</th><th className="p-3 text-left">Code</th><th className="p-3 text-left">Status</th><th className="p-3 text-right">Capacity/hr</th><th className="p-3 text-left">Supervisor</th><th className="p-3 text-center">Actions</th></tr></thead>
              <tbody>
                {lines.length === 0 ? <tr><td colSpan={6} className="p-4 text-center">No production lines yet</td></tr> : lines.map(l => (
                  <tr key={l.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="p-3">{l.name}</td><td className="p-3">{l.code}</td>
                    <td className={`p-3 ${statusColor(l.status)}`}>{l.status}</td>
                    <td className="p-3 text-right">{l.capacity_per_hour}</td>
                    <td className="p-3">{l.supervisor}</td>
                    <td className="p-3 text-center">
                      <button onClick={() => editLine(l)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                      <button onClick={() => setShowDelete({ id: l.id, tab: 'production-lines' })} className="text-red-400 hover:text-red-300">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ─── Work Orders ─────────────────────────────────────────────────── */}
      {!loading && tab === 'work-orders' && (
        <>
          <form onSubmit={submitOrder} className="bg-gray-800 p-4 rounded-lg mb-6">
            <h2 className="text-lg font-semibold mb-3">{editingOrderId ? 'Edit Order' : 'Add Order'}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Product Name" value={orderForm.product_name} onChange={e => setOrderForm({ ...orderForm, product_name: e.target.value })} required />
              <input className="bg-gray-700 text-gray-100 p-2 rounded" type="number" placeholder="Quantity" value={orderForm.quantity} onChange={e => setOrderForm({ ...orderForm, quantity: Number(e.target.value) })} required />
              <select className="bg-gray-700 text-gray-100 p-2 rounded" value={orderForm.production_line_id} onChange={e => setOrderForm({ ...orderForm, production_line_id: Number(e.target.value) })} required>
                <option value={0}>Select Line</option>
                {lines.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
              <select className="bg-gray-700 text-gray-100 p-2 rounded" value={orderForm.priority} onChange={e => setOrderForm({ ...orderForm, priority: e.target.value })}>
                <option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option>
              </select>
              <select className="bg-gray-700 text-gray-100 p-2 rounded" value={orderForm.status} onChange={e => setOrderForm({ ...orderForm, status: e.target.value })}>
                <option value="pending">Pending</option><option value="in_progress">In Progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option>
              </select>
              <input className="bg-gray-700 text-gray-100 p-2 rounded" type="date" value={orderForm.due_date ? orderForm.due_date.split('T')[0] : ''} onChange={e => setOrderForm({ ...orderForm, due_date: e.target.value })} />
              <input className="bg-gray-700 text-gray-100 p-2 rounded md:col-span-2" placeholder="Notes" value={orderForm.notes} onChange={e => setOrderForm({ ...orderForm, notes: e.target.value })} />
              <div className="flex gap-2">
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex-1">{editingOrderId ? 'Update' : 'Add'}</button>
                {editingOrderId && <button type="button" onClick={() => { setOrderForm({ ...EMPTY_ORDER }); setEditingOrderId(null); }} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">Cancel</button>}
              </div>
            </div>
          </form>
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700"><tr><th className="p-3 text-left">Product</th><th className="p-3 text-right">Qty</th><th className="p-3 text-left">Priority</th><th className="p-3 text-left">Status</th><th className="p-3 text-left">Due</th><th className="p-3 text-center">Actions</th></tr></thead>
              <tbody>
                {orders.length === 0 ? <tr><td colSpan={6} className="p-4 text-center">No work orders yet</td></tr> : orders.map(o => (
                  <tr key={o.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="p-3">{o.product_name}</td><td className="p-3 text-right">{o.quantity}</td>
                    <td className={`p-3 ${statusColor(o.priority)}`}>{o.priority}</td>
                    <td className={`p-3 ${statusColor(o.status)}`}>{o.status}</td>
                    <td className="p-3">{o.due_date ? o.due_date.split('T')[0] : '-'}</td>
                    <td className="p-3 text-center">
                      <button onClick={() => editOrder(o)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                      <button onClick={() => setShowDelete({ id: o.id, tab: 'work-orders' })} className="text-red-400 hover:text-red-300">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ─── Quality Checks ──────────────────────────────────────────────── */}
      {!loading && tab === 'quality-checks' && (
        <>
          <form onSubmit={submitCheck} className="bg-gray-800 p-4 rounded-lg mb-6">
            <h2 className="text-lg font-semibold mb-3">{editingCheckId ? 'Edit Check' : 'Add Check'}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <select className="bg-gray-700 text-gray-100 p-2 rounded" value={checkForm.work_order_id} onChange={e => setCheckForm({ ...checkForm, work_order_id: Number(e.target.value) })} required>
                <option value={0}>Select Work Order</option>
                {orders.map(o => <option key={o.id} value={o.id}>{o.product_name} (#{o.id})</option>)}
              </select>
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Inspector" value={checkForm.inspector} onChange={e => setCheckForm({ ...checkForm, inspector: e.target.value })} required />
              <select className="bg-gray-700 text-gray-100 p-2 rounded" value={checkForm.result} onChange={e => setCheckForm({ ...checkForm, result: e.target.value })}>
                <option value="pending">Pending</option><option value="pass">Pass</option><option value="fail">Fail</option>
              </select>
              <input className="bg-gray-700 text-gray-100 p-2 rounded" type="number" placeholder="Defect Count" value={checkForm.defect_count} onChange={e => setCheckForm({ ...checkForm, defect_count: Number(e.target.value) })} />
              <input className="bg-gray-700 text-gray-100 p-2 rounded md:col-span-2" placeholder="Notes" value={checkForm.notes} onChange={e => setCheckForm({ ...checkForm, notes: e.target.value })} />
              <div className="flex gap-2">
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex-1">{editingCheckId ? 'Update' : 'Add'}</button>
                {editingCheckId && <button type="button" onClick={() => { setCheckForm({ ...EMPTY_CHECK }); setEditingCheckId(null); }} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">Cancel</button>}
              </div>
            </div>
          </form>
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700"><tr><th className="p-3 text-left">Work Order</th><th className="p-3 text-left">Inspector</th><th className="p-3 text-left">Result</th><th className="p-3 text-right">Defects</th><th className="p-3 text-center">Actions</th></tr></thead>
              <tbody>
                {checks.length === 0 ? <tr><td colSpan={5} className="p-4 text-center">No quality checks yet</td></tr> : checks.map(c => (
                  <tr key={c.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="p-3">#{c.work_order_id}</td><td className="p-3">{c.inspector}</td>
                    <td className={`p-3 ${statusColor(c.result)}`}>{c.result}</td>
                    <td className="p-3 text-right">{c.defect_count}</td>
                    <td className="p-3 text-center">
                      <button onClick={() => editCheck(c)} className="text-blue-400 hover:text-blue-300 mr-3">Edit</button>
                      <button onClick={() => setShowDelete({ id: c.id, tab: 'quality-checks' })} className="text-red-400 hover:text-red-300">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ─── Bills of Materials ──────────────────────────────────────────── */}
      {!loading && tab === 'bills-of-materials' && (
        <>
          <form onSubmit={submitBom} className="bg-gray-800 p-4 rounded-lg mb-6">
            <h2 className="text-lg font-semibold mb-3">{editingBomId ? 'Edit BOM' : 'Add BOM'}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Product Name" value={bomForm.product_name} onChange={e => setBomForm({ ...bomForm, product_name: e.target.value })} required />
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Version" value={bomForm.version} onChange={e => setBomForm({ ...bomForm, version: e.target.value })} required />
              <input className="bg-gray-700 text-gray-100 p-2 rounded" placeholder="Notes" value={bomForm.notes} onChange={e => setBomForm({ ...bomForm, notes: e.target.value })} />
            </div>
            <div className="space-y-2 mb-3">
              {bomForm.items.map((item, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                  <input className="bg-gray-700 text-gray-100 p-2 rounded flex-1" placeholder="Material" value={item.material_name} onChange={e => updateBomItem(idx, 'material_name', e.target.value)} required />
                  <input className="bg-gray-700 text-gray-100 p-2 rounded w-24" type="number" placeholder="Qty" value={item.quantity} onChange={e => updateBomItem(idx, 'quantity', Number(e.target.value))} required />
                  <input className="bg-gray-700 text-gray-100 p-2 rounded w-20" placeholder="Unit" value={item.unit} onChange={e => updateBomItem(idx, 'unit', e.target.value)} required />
                  <button type="button" onClick={() => removeBomItem(idx)} className="text-red-400 hover:text-red-300 px-2">✕</button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={addBomItem} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded">+ Add Material</button>
              <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex-1">{editingBomId ? 'Update' : 'Add'} BOM</button>
              {editingBomId && <button type="button" onClick={() => { setBomForm({ ...EMPTY_BOM }); setEditingBomId(null); }} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">Cancel</button>}
            </div>
          </form>
          <div className="space-y-3">
            {boms.length === 0 ? <div className="bg-gray-800 p-4 rounded-lg text-center">No bills of materials yet</div> : boms.map(b => (
              <div key={b.id} className="bg-gray-800 p-4 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <span className="font-semibold">{b.product_name}</span>
                    <span className="text-gray-400 ml-2">v{b.version}</span>
                  </div>
                  <div>
                    <button onClick={() => editBom(b)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                    <button onClick={() => setShowDelete({ id: b.id, tab: 'bills-of-materials' })} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                  </div>
                </div>
                <div className="text-sm text-gray-400">
                  {b.items.map((item, i) => (
                    <span key={i} className="inline-block bg-gray-700 rounded px-2 py-1 mr-2 mb-1">{item.material_name}: {item.quantity} {item.unit}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Delete Confirmation */}
      {showDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-300 mb-4">Are you sure you want to delete this item?</p>
            <div className="flex gap-3">
              <button onClick={handleDelete} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded flex-1">Delete</button>
              <button onClick={() => setShowDelete(null)} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded flex-1">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
