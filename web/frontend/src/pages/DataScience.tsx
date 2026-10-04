import { useEffect, useState, ComponentType } from 'react'
import { api, DataScienceData } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, Legend,
} from 'recharts'
import {
  Brain, FlaskConical, TrendingUp, Activity, Zap, Target, Layers,
  CheckCircle, AlertCircle, Settings, AlertTriangle, GitBranch, Clock,
  Plus, Pencil, Trash2, Search, Download, X,
} from 'lucide-react'

const SC: Record<string, string> = { production: '#10b981', staging: '#3b82f6', failed: '#ef4444', running: '#f59e0b', completed: '#10b981', pending: '#94a3b8' }
const MC: Record<string, string> = { classification: '#06b6d4', regression: '#a855f7', clustering: '#10b981', neural_network: '#f59e0b', ensemble: '#ec4899', other: '#94a3b8' }
const TS = { backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }

// --- Types ---
interface ModelFormData {
  id?: string
  name: string
  type: string
  accuracy: number
  last_trained: string
  status: string
}

interface EditingModel {
  id: string
  name: string
  type: string
  accuracy: number
  last_trained: string
  status: string
}

// --- Constants ---
const MODEL_TYPES = ['classification', 'regression', 'clustering', 'neural_network', 'ensemble', 'other']
const MODEL_STATUSES = ['production', 'staging', 'failed', 'running', 'completed', 'pending']
const EMPTY_FORM: ModelFormData = { name: '', type: 'classification', accuracy: 0, last_trained: new Date().toISOString().split('T')[0], status: 'pending' }

// --- Reusable Components ---
function StatusBadge({ status }: { status: string }) {
  const c = SC[status] || '#94a3b8'
  return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: `${c}20`, color: c, border: `1px solid ${c}40` }}>
    <span className="w-1.5 h-1.5 rounded-full mr-1.5" style={{ backgroundColor: c }} />{status.charAt(0).toUpperCase() + status.slice(1)}
  </span>
}
function ProgressBar({ progress, status }: { progress?: number; status: string }) {
  const c = SC[status] || '#06b6d4'
  const width = progress != null ? Math.min(progress, 100) : 0
  return <div className="w-full bg-gray-700/50 rounded-full h-2.5 overflow-hidden">
    <div className="h-full rounded-full transition-all duration-700 ease-out animate-pulse-slow" style={{ width: `${width}%`, backgroundColor: c, boxShadow: `0 0 8px ${c}60` }} />
  </div>
}
function TypeBadge({ type }: { type: string }) {
  const c = MC[type] || MC.other
  return <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium" style={{ backgroundColor: `${c}15`, color: c, border: `1px solid ${c}30` }}>{type.replace('_', ' ').toUpperCase()}</span>
}
function AccuracyBar({ accuracy }: { accuracy: number }) {
  const accuracyPct = accuracy * 100
  const c = accuracyPct >= 90 ? '#10b981' : accuracyPct >= 75 ? '#06b6d4' : accuracyPct >= 60 ? '#f59e0b' : '#ef4444'
  return <div className="flex items-center gap-2"><div className="w-20 bg-gray-700/50 rounded-full h-2 overflow-hidden">
    <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${accuracyPct}%`, backgroundColor: c }} />
  </div><span className="text-sm font-medium" style={{ color: c }}>{accuracyPct.toFixed(1)}%</span></div>
}
function StatCard({ icon: Icon, label, value, subValue, color }: { icon: ComponentType<{ className?: string }>; label: string; value: string | number; subValue?: string; color: string }) {
  return <div className="glass rounded-xl p-5 card-hover"><div className="flex items-start justify-between">
    <div><p className="text-xs text-gray-400 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}</div>
    <div className="p-3 rounded-lg" style={{ backgroundColor: `${color}15` }}><Icon className="w-6 h-6" /></div>
  </div></div>
}
function SectionHeader({ icon: Icon, title, subtitle, color }: { icon: ComponentType<{ className?: string }>; title: string; subtitle?: string; color: string }) {
  return <div className="flex items-center gap-3 mb-4"><div className="p-2 rounded-lg" style={{ backgroundColor: `${color}15` }}><Icon className="w-5 h-5" /></div>
    <div><h2 className="text-lg font-semibold">{title}</h2>{subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}</div></div>
}

// --- Model Form Modal ---
function ModelFormModal({ initial, onSave, onClose }: { initial: ModelFormData; onSave: (data: ModelFormData) => void; onClose: () => void }) {
  const [form, setForm] = useState<ModelFormData>(initial)
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try { await onSave(form) } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-100">Create New Model</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Model Name</label>
            <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. ResNet-50" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Type</label>
              <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {MODEL_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Status</label>
              <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {MODEL_STATUSES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Accuracy (0-1)</label>
              <input type="number" step="0.01" min="0" max="1" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.accuracy} onChange={(e) => setForm({ ...form, accuracy: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Last Trained</label>
              <input type="date" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.last_trained} onChange={(e) => setForm({ ...form, last_trained: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors">Cancel</button>
            <button type="submit" disabled={saving || !form.name.trim()} className="px-4 py-2 text-sm rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">{saving ? 'Creating...' : 'Create Model'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Edit Model Modal ---
function EditModelModal({ model, onSave, onClose }: { model: EditingModel; onSave: (data: ModelFormData) => void; onClose: () => void }) {
  const [form, setForm] = useState<ModelFormData>({ name: model.name, type: model.type, accuracy: model.accuracy, last_trained: model.last_trained, status: model.status })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try { await onSave(form) } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-100">Edit Model</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Model Name</label>
            <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Type</label>
              <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {MODEL_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Status</label>
              <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {MODEL_STATUSES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Accuracy (0-1)</label>
              <input type="number" step="0.01" min="0" max="1" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.accuracy} onChange={(e) => setForm({ ...form, accuracy: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Last Trained</label>
              <input type="date" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" value={form.last_trained} onChange={(e) => setForm({ ...form, last_trained: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors">Cancel</button>
            <button type="submit" disabled={saving || !form.name.trim()} className="px-4 py-2 text-sm rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">{saving ? 'Saving...' : 'Save Changes'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Main Component ---
export default function DataScience() {
  const [data, setData] = useState<DataScienceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingModel, setEditingModel] = useState<EditingModel | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const result = await api.getDataScience()
        const normalized: DataScienceData = {
          id: result.id || '',
          models: Array.isArray(result.models) ? result.models : [],
          features: Array.isArray(result.features) ? result.features : [],
          experiments: Array.isArray(result.experiments) ? result.experiments : [],
        }
        setData(normalized)
        setError(null)
      }
      catch (err) { setError(err instanceof Error ? err.message : 'Failed to fetch data') }
      finally { setLoading(false) }
    }
    fetchData()
  }, [])

  // --- CRUD Handlers ---
  const handleCreate = async (formData: ModelFormData) => {
    try {
      setActionLoading(true)
      const response = await fetch('/api/datascience', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      if (!response.ok) throw new Error(`Failed to create model: ${response.status}`)
      const newModel = await response.json()
      setData((prev) => prev ? { ...prev, models: [...prev.models, newModel] } : prev)
      setShowCreateModal(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create model')
    } finally { setActionLoading(false) }
  }

  const handleEdit = async (formData: ModelFormData) => {
    if (!editingModel) return
    try {
      setActionLoading(true)
      const response = await fetch(`/api/datascience/${editingModel.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      if (!response.ok) throw new Error(`Failed to update model: ${response.status}`)
      const updatedModel = await response.json()
      setData((prev) => prev ? { ...prev, models: prev.models.map((m) => (m.id === editingModel.id ? updatedModel : m)) } : prev)
      setEditingModel(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update model')
    } finally { setActionLoading(false) }
  }

  const handleDelete = async (modelId: string) => {
    if (!confirm('Are you sure you want to delete this model?')) return
    try {
      setActionLoading(true)
      const response = await fetch(`/api/datascience/${modelId}`, { method: 'DELETE' })
      if (!response.ok) throw new Error(`Failed to delete model: ${response.status}`)
      setData((prev) => prev ? { ...prev, models: prev.models.filter((m) => m.id !== modelId) } : prev)
      setSelectedIds((prev) => { const next = new Set(prev); next.delete(modelId); return next })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete model')
    } finally { setActionLoading(false) }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} selected model(s)?`)) return
    try {
      setActionLoading(true)
      const response = await fetch('/api/datascience/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedIds) }),
      })
      if (!response.ok) throw new Error(`Failed to bulk delete: ${response.status}`)
      setData((prev) => prev ? { ...prev, models: prev.models.filter((m) => !selectedIds.has(m.id)) } : prev)
      setSelectedIds(new Set())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bulk delete')
    } finally { setActionLoading(false) }
  }

  // --- Export Handlers ---
  const handleExportCSV = () => {
    if (!data) return
    const headers = ['Name', 'Type', 'Accuracy', 'Last Trained', 'Status']
    const rows = data.models.map((m) => [m.name, m.type, m.accuracy, m.last_trained, m.status])
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `datascience-models-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExportJSON = () => {
    if (!data) return
    const blob = new Blob([JSON.stringify(data.models, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `datascience-models-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // --- Selection Handlers ---
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (!data) return
    if (selectedIds.size === data.models.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(data.models.map((m) => m.id)))
  }

  // --- Filtered Models ---
  const filteredModels = data?.models.filter((m) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return m.name.toLowerCase().includes(q) || m.type.toLowerCase().includes(q) || m.status.toLowerCase().includes(q)
  }) || []

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-pulse-slow flex items-center gap-3">
    <Brain className="w-6 h-6 text-cyan-400" /><span className="text-gray-400">Loading data science metrics...</span></div></div>
  if (error) return <div className="flex items-center justify-center h-64"><div className="text-center">
    <Activity className="w-12 h-12 text-red-400 mx-auto mb-3" /><p className="text-red-400">{error}</p></div></div>
  if (!data) return null

  const avgAccuracy = data.models.length > 0 ? (data.models.reduce((s, m) => s + m.accuracy * 100, 0) / data.models.length).toFixed(1) : '0'
  const bestModel = data.models.length > 0 ? data.models.reduce((b, m) => (m.accuracy > b.accuracy ? m : b), data.models[0]) : null
  const productionCount = data.models.filter((m) => m.status === 'production').length
  const chartData = data.features.map((f) => ({ name: f.name, importance: f.importance, type: f.type }))
  const modelComparisonData = data.models.slice(0, 6).map((m) => ({ name: m.name.length > 10 ? m.name.substring(0, 10) + '…' : m.name, accuracy: m.accuracy * 100, type: m.type }))
  const trainingHistory = [
    { epoch: 'Epoch 1', loss: 0.85, accuracy: 45, valLoss: 0.88, valAccuracy: 42 },
    { epoch: 'Epoch 5', loss: 0.62, accuracy: 68, valLoss: 0.65, valAccuracy: 65 },
    { epoch: 'Epoch 10', loss: 0.41, accuracy: 82, valLoss: 0.44, valAccuracy: 79 },
    { epoch: 'Epoch 15', loss: 0.28, accuracy: 89, valLoss: 0.31, valAccuracy: 86 },
    { epoch: 'Epoch 20', loss: 0.19, accuracy: 93, valLoss: 0.22, valAccuracy: 91 },
    { epoch: 'Epoch 25', loss: 0.14, accuracy: 95, valLoss: 0.17, valAccuracy: 93 },
    { epoch: 'Epoch 30', loss: 0.11, accuracy: 97, valLoss: 0.14, valAccuracy: 95 },
  ]
  const hyperparams = [
    { name: 'Learning Rate', value: '0.001', range: '0.0001 – 0.1', optimal: true },
    { name: 'Batch Size', value: '64', range: '16 – 256', optimal: true },
    { name: 'Dropout Rate', value: '0.3', range: '0.1 – 0.5', optimal: false },
    { name: 'Hidden Layers', value: '3', range: '1 – 5', optimal: true },
    { name: 'Neurons/Layer', value: '128', range: '32 – 512', optimal: false },
    { name: 'Optimizer', value: 'Adam', range: 'Adam, SGD, RMSprop', optimal: true },
    { name: 'Epochs', value: '50', range: '10 – 200', optimal: false },
    { name: 'Weight Decay', value: '0.0001', range: '0 – 0.01', optimal: true },
  ]
  const latencyData = [
    { model: 'ResNet-50', training: 120, inference: 12 },
    { model: 'BERT-Base', training: 340, inference: 45 },
    { model: 'XGBoost', training: 8, inference: 2 },
    { model: 'LSTM', training: 210, inference: 28 },
    { model: 'ViT-Small', training: 450, inference: 65 },
    { model: 'Random Forest', training: 5, inference: 1 },
  ]
  const abTestData = [
    { variant: 'A (Control)', conversion: 4.2, revenue: 12500, users: 5000 },
    { variant: 'B (Treatment)', conversion: 5.8, revenue: 18200, users: 5000 },
    { variant: 'C (Variant)', conversion: 5.1, revenue: 15800, users: 5000 },
  ]
  const driftAlerts = [
    { feature: 'user_age', severity: 'high', driftScore: 0.82, detected: '2h ago', status: 'active' },
    { feature: 'purchase_amount', severity: 'medium', driftScore: 0.45, detected: '6h ago', status: 'investigating' },
    { feature: 'session_duration', severity: 'low', driftScore: 0.23, detected: '1d ago', status: 'resolved' },
    { feature: 'click_rate', severity: 'high', driftScore: 0.78, detected: '30m ago', status: 'active' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-purple-500/20"><Brain className="w-8 h-8 text-cyan-400" /></div>
          <div><h1 className="text-2xl font-bold gradient-text">Data Science</h1><p className="text-sm text-gray-400">ML models, experiments & feature importance</p></div>
        </div>
        <div className="text-xs text-gray-500">Last updated: {new Date().toLocaleString()}</div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Brain} label="Total Models" value={data.models.length} subValue={`${data.models.filter((m) => m.status === 'staging').length} in staging`} color="#06b6d4" />
        <StatCard icon={Target} label="Avg Accuracy" value={`${avgAccuracy}%`} subValue="Across all models" color="#10b981" />
        <StatCard icon={Zap} label="Best Model" value={bestModel ? bestModel.name : 'N/A'} subValue={bestModel ? `${(bestModel.accuracy * 100).toFixed(1)}% accuracy` : 'No models'} color="#f59e0b" />
        <StatCard icon={CheckCircle} label="In Production" value={productionCount} subValue={`${data.models.length - productionCount} non-production`} color="#a855f7" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-xl p-6">
          <SectionHeader icon={TrendingUp} title="Model Performance" subtitle="Accuracy comparison" color="#06b6d4" />
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={modelComparisonData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <Tooltip contentStyle={TS} />
              <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>{modelComparisonData.map((e, i) => <Cell key={i} fill={MC[e.type] || '#94a3b8'} />)}</Bar>
            </BarChart>
          </ResponsiveContainer></div>
        </div>
        <div className="glass rounded-xl p-6">
          <SectionHeader icon={Layers} title="Feature Importance" subtitle="Top contributing features" color="#10b981" />
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 60, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" domain={[0, 1]} tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} width={100} />
              <Tooltip contentStyle={TS} formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'Importance']} />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]}>{chartData.map((e, i) => <Cell key={i} fill={e.type === 'numeric' ? '#06b6d4' : e.type === 'categorical' ? '#a855f7' : '#10b981'} />)}</Bar>
            </BarChart>
          </ResponsiveContainer></div>
          <div className="flex items-center justify-center gap-4 mt-3 text-xs text-gray-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-cyan-400" />Numeric</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-purple-400" />Categorical</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-green-400" />Other</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-xl p-6">
          <SectionHeader icon={FlaskConical} title="Experiments" subtitle={`${data.experiments.length} active experiments`} color="#f59e0b" />
          <div className="space-y-4">{data.experiments.map((exp) => (
            <div key={exp.id} className="p-3 rounded-lg bg-gray-800/30 border border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <div><p className="font-medium text-sm">{exp.name}</p><p className="text-xs text-gray-500">{exp.id}</p></div>
                <StatusBadge status={exp.status} />
              </div>
              <div className="flex items-center gap-3"><div className="flex-1"><ProgressBar progress={exp.progress} status={exp.status} /></div>
                <span className="text-xs text-gray-400 w-10 text-right">{exp.progress != null ? `${exp.progress}%` : 'N/A'}</span></div>
            </div>
          ))}</div>
        </div>
        <div className="glass rounded-xl p-6">
          <SectionHeader icon={Activity} title="Training History" subtitle="Loss & accuracy over epochs" color="#ec4899" />
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={trainingHistory} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="epoch" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <Tooltip contentStyle={TS} /><Legend wrapperStyle={{ fontSize: '11px' }} />
              <Line type="monotone" dataKey="accuracy" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 3 }} name="Train Accuracy" />
              <Line type="monotone" dataKey="valAccuracy" stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" dot={{ fill: '#10b981', r: 3 }} name="Val Accuracy" />
              <Line type="monotone" dataKey="loss" stroke="#ef4444" strokeWidth={2} dot={{ fill: '#ef4444', r: 3 }} name="Train Loss" />
              <Line type="monotone" dataKey="valLoss" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={{ fill: '#f59e0b', r: 3 }} name="Val Loss" />
            </LineChart>
          </ResponsiveContainer></div>
        </div>
      </div>

      {/* --- Model Registry with CRUD --- */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <SectionHeader icon={Layers} title="Model Registry" subtitle={`${data.models.length} registered models`} color="#06b6d4" />
          <div className="flex items-center gap-2">
            <button onClick={handleExportCSV} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors">
              <Download className="w-3.5 h-3.5" />CSV
            </button>
            <button onClick={handleExportJSON} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors">
              <Download className="w-3.5 h-3.5" />JSON
            </button>
            <button onClick={() => setShowCreateModal(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 transition-colors">
              <Plus className="w-3.5 h-3.5" />Create
            </button>
          </div>
        </div>

        {/* Search & Bulk Actions Bar */}
        <div className="flex items-center justify-between mb-4 gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search models by name, type, or status..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </div>
          {selectedIds.size > 0 && (
            <button onClick={handleBulkDelete} disabled={actionLoading} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-red-600/20 text-red-400 border border-red-600/30 hover:bg-red-600/30 disabled:opacity-50 transition-colors">
              <Trash2 className="w-3.5 h-3.5" />Delete Selected ({selectedIds.size})
            </button>
          )}
        </div>

        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="border-b border-gray-700">
            <th className="text-left py-3 px-4 text-gray-400 font-medium w-10">
              <input type="checkbox" checked={data.models.length > 0 && selectedIds.size === data.models.length} onChange={toggleSelectAll} className="rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500/50" />
            </th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Name</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Type</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Accuracy</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Last Trained</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Actions</th>
          </tr></thead>
          <tbody>{filteredModels.map((model) => (
            <tr key={model.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
              <td className="py-3 px-4">
                <input type="checkbox" checked={selectedIds.has(model.id)} onChange={() => toggleSelect(model.id)} className="rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500/50" />
              </td>
              <td className="py-3 px-4 font-medium">{model.name}</td>
              <td className="py-3 px-4"><TypeBadge type={model.type} /></td>
              <td className="py-3 px-4"><AccuracyBar accuracy={model.accuracy} /></td>
              <td className="py-3 px-4 text-gray-400">{model.last_trained}</td>
              <td className="py-3 px-4"><StatusBadge status={model.status} /></td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-1">
                  <button onClick={() => setEditingModel({ id: model.id, name: model.name, type: model.type, accuracy: model.accuracy, last_trained: model.last_trained, status: model.status })} className="p-1.5 rounded-lg text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors" title="Edit">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(model.id)} disabled={actionLoading} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 disabled:opacity-50 transition-colors" title="Delete">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}</tbody>
        </table></div>
        {filteredModels.length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            {searchQuery ? 'No models match your search.' : 'No models registered yet. Click "Create" to add one.'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-xl p-6">
          <SectionHeader icon={Clock} title="Latency Comparison" subtitle="Training vs inference (ms)" color="#f59e0b" />
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={latencyData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="model" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <Tooltip contentStyle={TS} /><Legend wrapperStyle={{ fontSize: '11px' }} />
              <Bar dataKey="training" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Training (ms)" />
              <Bar dataKey="inference" fill="#a855f7" radius={[4, 4, 0, 0]} name="Inference (ms)" />
            </BarChart>
          </ResponsiveContainer></div>
        </div>
        <div className="glass rounded-xl p-6">
          <SectionHeader icon={GitBranch} title="A/B Test Results" subtitle="Conversion & revenue by variant" color="#10b981" />
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={abTestData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="variant" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
              <Tooltip contentStyle={TS} /><Legend wrapperStyle={{ fontSize: '11px' }} />
              <Bar dataKey="conversion" fill="#10b981" radius={[4, 4, 0, 0]} name="Conversion %" />
              <Bar dataKey="revenue" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Revenue ($)" />
            </BarChart>
          </ResponsiveContainer></div>
        </div>
      </div>

      <div className="glass rounded-xl p-6">
        <SectionHeader icon={AlertTriangle} title="Drift Detection" subtitle="Feature drift monitoring" color="#ef4444" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">{driftAlerts.map((alert, i) => (
          <div key={i} className="p-4 rounded-lg border border-gray-700/50 bg-gray-800/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400 uppercase tracking-wider">{alert.feature}</span>
              <span className={`w-2 h-2 rounded-full ${alert.severity === 'high' ? 'bg-red-400 animate-pulse' : alert.severity === 'medium' ? 'bg-amber-400' : 'bg-green-400'}`} />
            </div>
            <p className="text-lg font-bold text-white mb-1">{(alert.driftScore * 100).toFixed(0)}%</p>
            <p className="text-xs text-gray-500">Drift score</p>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-gray-500">{alert.detected}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${alert.status === 'active' ? 'bg-red-500/20 text-red-400' : alert.status === 'investigating' ? 'bg-amber-500/20 text-amber-400' : 'bg-green-500/20 text-green-400'}`}>{alert.status}</span>
            </div>
          </div>
        ))}</div>
      </div>

      <div className="glass rounded-xl p-6">
        <SectionHeader icon={Settings} title="Hyperparameter Tuning" subtitle="Current model configuration" color="#06b6d4" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">{hyperparams.map((param, idx) => (
          <div key={idx} className="p-4 rounded-lg border border-gray-700/50 bg-gray-800/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400 uppercase tracking-wider">{param.name}</span>
              {param.optimal ? <CheckCircle className="w-4 h-4 text-green-400" /> : <AlertCircle className="w-4 h-4 text-amber-400" />}
            </div>
            <p className="text-lg font-bold text-white mb-1">{param.value}</p>
            <p className="text-xs text-gray-500">Range: {param.range}</p>
          </div>
        ))}</div>
      </div>

      {/* --- Modals --- */}
      {showCreateModal && (
        <ModelFormModal initial={EMPTY_FORM} onSave={handleCreate} onClose={() => setShowCreateModal(false)} />
      )}
      {editingModel && (
        <EditModelModal model={editingModel} onSave={handleEdit} onClose={() => setEditingModel(null)} />
      )}
    </div>
  )
}
