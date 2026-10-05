import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { BigData } from '../api/client'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, RadialBarChart, RadialBar } from 'recharts'
import { Database, HardDrive, Search, GitBranch, Archive, Zap, Layers, Cpu, Activity, CheckCircle2, XCircle, Timer, BarChart3, Workflow, Shield, GitMerge, Boxes, Gauge, Download, Plus, Edit2, Trash2, X, CheckSquare, Square } from 'lucide-react'

const SC: Record<string, string> = { completed: '#10b981', running: '#3b82f6', pending: '#f59e0b', failed: '#ef4444', success: '#10b981', active: '#3b82f6' }
const FC: Record<string, { bg: string; text: string; border: string }> = { parquet: { bg: 'bg-cyan-500/15', text: 'text-cyan-400', border: 'border-cyan-500/30' }, csv: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' }, json: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' }, avro: { bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30' }, orc: { bg: 'bg-rose-500/15', text: 'text-rose-400', border: 'border-rose-500/30' }, delta: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30' } }
const STAGES = [{ key: 'ingest', label: 'Ingest', icon: Database, color: '#06b6d4' }, { key: 'validate', label: 'Validate', icon: Shield, color: '#8b5cf6' }, { key: 'transform', label: 'Transform', icon: GitBranch, color: '#f59e0b' }, { key: 'enrich', label: 'Enrich', icon: Layers, color: '#10b981' }, { key: 'index', label: 'Index', icon: Cpu, color: '#ec4899' }, { key: 'serve', label: 'Serve', icon: Zap, color: '#3b82f6' }]
const PARTITIONS = [{ name: 'Time-based', pct: 40, color: '#06b6d4', desc: 'Daily/hourly' }, { name: 'Hash', pct: 25, color: '#8b5cf6', desc: 'Even distribution' }, { name: 'Range', pct: 20, color: '#f59e0b', desc: 'Value range' }, { name: 'List', pct: 15, color: '#10b981', desc: 'Category-based' }]
const INDEXES = [{ name: 'B-Tree', lookups: 98, size: '2.4 GB' }, { name: 'Bitmap', lookups: 92, size: '1.8 GB' }, { name: 'Inverted', lookups: 95, size: '3.1 GB' }, { name: 'Columnar', lookups: 99, size: '4.2 GB' }]

const fmtN = (n: number) => n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : n.toLocaleString()
const fmtD = (ms: number) => ms >= 60000 ? `${(ms / 60000).toFixed(1)}m` : ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
const fmtSize = (s: string) => { const m = s.match(/([\d.]+)\s*(B|KB|MB|GB|TB)/i); if (!m) return 0; const mult: Record<string, number> = { B: 1, KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3, TB: 1024 ** 4 }; return parseFloat(m[1]) * (mult[m[2].toUpperCase()] || 1) }

const Badge = ({ status }: { status: string }) => {
  const c = SC[status] || '#94a3b8'
  return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: `${c}18`, color: c, border: `1px solid ${c}35` }}><span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: c }} />{status}</span>
}

const FmtBadge = ({ f }: { f: string }) => {
  const c = FC[f.toLowerCase()] || { bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/30' }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase ${c.bg} ${c.text} border ${c.border}`}>{f}</span>
}

const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => <div className={`bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 card-hover ${className}`}>{children}</div>

const ST = ({ icon: I, title, sub }: { icon: React.ElementType; title: string; sub?: string }) => (
  <div className="flex items-center gap-2 mb-4">
    <I className="w-5 h-5 text-cyan-400" />
    <div>
      <h2 className="text-lg font-semibold text-[var(--text)]">{title}</h2>
      {sub && <p className="text-xs text-[var(--muted)]">{sub}</p>}
    </div>
  </div>
)

const Donut = ({ used, total }: { used: number; total: number }) => {
  const free = Math.max(total - used, 0)
  const pct = total > 0 ? Math.round((used / total) * 100) : 0
  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      <div className="relative w-44 h-44 flex-shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={[{ name: 'Used', value: used, color: '#06b6d4' }, { name: 'Free', value: free, color: '#1e293b' }] as unknown as Array<{ name: string; value: number; color: string }>} dataKey="value" cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} stroke="none">
              {[{ color: '#06b6d4' }, { color: '#1e293b' }].map((e, i) => <Cell key={i} fill={e.color} />)}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold text-[var(--text)]">{pct}%</span>
          <span className="text-xs text-[var(--muted)]">used</span>
        </div>
      </div>
      <div className="space-y-3 flex-1 w-full">
        {[{ l: 'Used', v: used, c: '#06b6d4' }, { l: 'Free', v: free, c: '#475569' }, { l: 'Total', v: total, c: '#94a3b8' }].map((i) => (
          <div key={i.l} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: i.c }} />
              <span className="text-sm text-[var(--muted)]">{i.l}</span>
            </div>
            <span className="text-sm font-semibold text-[var(--text)]">{i.v} TB</span>
          </div>
        ))}
        <div className="mt-2 pt-3 border-t border-[var(--border)] flex justify-between text-xs text-[var(--muted)]">
          <span>Available</span>
          <span className="text-emerald-400 font-medium">{free} TB</span>
        </div>
      </div>
    </div>
  )
}

const DatasetBar = ({ ds }: { ds: BigData['datasets'] }) => (
  <div className="h-56">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={ds.map((d) => ({ name: d.name.length > 12 ? d.name.slice(0, 12) + '…' : d.name, size: fmtSize(d.size) }))} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} tickFormatter={(v: number) => fmtN(v)} />
        <Tooltip contentStyle={{ backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }} />
        <Bar dataKey="size" radius={[4, 4, 0, 0]}>
          {ds.map((_, i) => <Cell key={i} fill={['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#ec4899', '#3b82f6'][i % 6]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </div>
)

const QueryChart = ({ qs }: { qs: BigData['queries'] }) => (
  <div className="h-64">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={qs.map((q, i) => ({ name: q.id.slice(0, 8), duration: q.duration_ms, rows: q.rows_scanned, index: i }))} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="dg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#06b6d4" stopOpacity="0.3" />
            <stop offset="95%" stopColor="#06b6d4" stopOpacity="0" />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#1e293b' }} tickLine={{ stroke: '#1e293b' }} tickFormatter={(v: number) => fmtD(v)} />
        <Tooltip contentStyle={{ backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }} formatter={(v: number, n: string) => n === 'duration' ? [fmtD(v), 'Duration'] : [fmtN(v), 'Rows']} />
        <Area type="monotone" dataKey="duration" stroke="#06b6d4" strokeWidth={2} fill="url(#dg)" />
      </AreaChart>
    </ResponsiveContainer>
  </div>
)

const Compression = ({ ratio, used }: { ratio: number; used: number }) => {
  const pct = Math.min((ratio / 10) * 100, 100)
  const savings = Math.round((1 - 1 / ratio) * 100)
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Archive className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-[var(--muted)]">Ratio</span>
        </div>
        <span className="text-2xl font-bold text-purple-400">{ratio}x</span>
      </div>
      <div className="w-full bg-[var(--border)] rounded-full h-3 overflow-hidden">
        <div className="h-full rounded-full bg-gradient-to-r from-purple-500 via-pink-500 to-rose-500 transition-all duration-700" style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-900/[0.02] rounded-lg p-3 text-center">
          <p className="text-xs text-[var(--muted)]">Space Saved</p>
          <p className="text-lg font-bold text-emerald-400">{savings}%</p>
        </div>
        <div className="bg-gray-900/[0.02] rounded-lg p-3 text-center">
          <p className="text-xs text-[var(--muted)]">Raw Size</p>
          <p className="text-lg font-bold text-[var(--text)]">{(used * ratio).toFixed(1)} TB</p>
        </div>
      </div>
      <div className="flex justify-between text-xs text-[var(--muted)]">
        <span>Algorithm: Zstandard</span>
        <span>Level 9</span>
      </div>
    </div>
  )
}

const Pipeline = () => (
  <div className="space-y-4">
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
      {STAGES.map((s, i) => (
        <div key={s.key} className="flex items-center flex-1 w-full sm:w-auto">
          <div className="flex flex-col items-center gap-2 flex-1">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center border transition-transform hover:scale-110" style={{ backgroundColor: `${s.color}12`, borderColor: `${s.color}30` }}>
              <s.icon className="w-5 h-5" style={{ color: s.color }} />
            </div>
            <span className="text-xs font-medium text-[var(--muted)]">{s.label}</span>
          </div>
          {i < STAGES.length - 1 && <div className="hidden sm:block flex-shrink-0 w-6 h-0.5 bg-[var(--border)] mx-1" />}
        </div>
      ))}
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
      {[{ l: 'Throughput', v: '2.4 GB/s', I: Zap, c: '#06b6d4' }, { l: 'Latency', v: '12ms', I: Timer, c: '#f59e0b' }, { l: 'Success Rate', v: '99.7%', I: CheckCircle2, c: '#10b981' }].map((m) => (
        <div key={m.l} className="flex items-center gap-2 bg-gray-900/[0.02] rounded-lg px-3 py-2">
          <m.I className="w-4 h-4" style={{ color: m.c }} />
          <div>
            <p className="text-xs text-[var(--muted)]">{m.l}</p>
            <p className="text-sm font-semibold text-[var(--text)]">{m.v}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
)

const Partition = () => (
  <div className="space-y-4">
    <div className="flex flex-wrap gap-4">
      {PARTITIONS.map((p) => (
        <div key={p.name} className="flex-1 min-w-[140px]">
          <div className="flex justify-between mb-1">
            <span className="text-sm font-medium text-[var(--text)]">{p.name}</span>
            <span className="text-sm font-bold" style={{ color: p.color }}>{p.pct}%</span>
          </div>
          <div className="w-full bg-[var(--border)] rounded-full h-2 overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${p.pct}%`, backgroundColor: p.color }} />
          </div>
          <p className="text-[10px] text-[var(--muted)] mt-1">{p.desc}</p>
        </div>
      ))}
    </div>
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
      {[{ l: 'Total Partitions', v: '1,247', I: Boxes }, { l: 'Avg Size', v: '2.1 GB', I: Database }, { l: 'Rebalance', v: 'Auto', I: GitMerge }, { l: 'Replication', v: '3x', I: Shield }].map((m) => (
        <div key={m.l} className="flex items-center gap-2 bg-gray-900/[0.02] rounded-lg px-3 py-2">
          <m.I className="w-4 h-4 text-cyan-400" />
          <div>
            <p className="text-[10px] text-[var(--muted)]">{m.l}</p>
            <p className="text-sm font-semibold text-[var(--text)]">{m.v}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
)

const IndexPerf = () => (
  <div className="space-y-4">
    <div className="h-40">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart cx="50%" cy="50%" innerRadius="30%" outerRadius="90%" data={INDEXES.map((m, i) => ({ name: m.name, value: m.lookups, fill: ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981'][i] }))} startAngle={180} endAngle={0}>
          <RadialBar dataKey={"value" as any} cornerRadius={5} />
          <Tooltip contentStyle={{ backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }} />
        </RadialBarChart>
      </ResponsiveContainer>
    </div>
    <div className="grid grid-cols-2 gap-3">
      {INDEXES.map((m) => (
        <div key={m.name} className="bg-gray-900/[0.02] rounded-lg p-3">
          <div className="flex justify-between mb-1">
            <span className="text-xs font-medium text-[var(--text)]">{m.name}</span>
            <span className="text-xs text-[var(--muted)]">{m.size}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-[var(--border)] rounded-full h-1.5 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500" style={{ width: `${m.lookups}%` }} />
            </div>
            <span className="text-xs font-semibold text-cyan-400">{m.lookups}%</span>
          </div>
        </div>
      ))}
    </div>
  </div>
)

export default function BigData() {
  const [data, setData] = useState<BigData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingDataset, setEditingDataset] = useState<BigData['datasets'][0] | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [formData, setFormData] = useState({ name: '', description: '', size: 0, format: 'csv' })
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    api.getBigData().then((result) => {
      if (Array.isArray(result)) {
        setData(result[0] ?? null)
      } else {
        setData(result)
      }
    }).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [])

  const filteredDatasets = data?.datasets.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.format.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? []

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormLoading(true)
    setFormError(null)
    try {
      await api.createBigDataDataset(formData)
      setShowCreateModal(false)
      setFormData({ name: '', description: '', size: 0, format: 'csv' })
      const result = await api.getBigData()
      if (Array.isArray(result)) setData(result[0] ?? null)
      else setData(result)
    } catch (err: any) {
      setFormError(err.message || 'Failed to create dataset')
    } finally {
      setFormLoading(false)
    }
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingDataset) return
    setFormLoading(true)
    setFormError(null)
    try {
      await api.updateBigDataDataset(editingDataset.name, formData)
      setEditingDataset(null)
      setFormData({ name: '', description: '', size: 0, format: 'csv' })
      const result = await api.getBigData()
      if (Array.isArray(result)) setData(result[0] ?? null)
      else setData(result)
    } catch (err: any) {
      setFormError(err.message || 'Failed to update dataset')
    } finally {
      setFormLoading(false)
    }
  }

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete dataset "${name}"?`)) return
    try {
      await api.deleteBigDataDataset(name)
      const result = await api.getBigData()
      if (Array.isArray(result)) setData(result[0] ?? null)
      else setData(result)
      setSelectedIds((prev) => { const n = new Set(prev); n.delete(name); return n })
    } catch (err: any) {
      alert(err.message || 'Failed to delete dataset')
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} selected dataset(s)?`)) return
    try {
      await Promise.all(Array.from(selectedIds).map((id) => api.deleteBigDataDataset(id)))
      setSelectedIds(new Set())
      const result = await api.getBigData()
      if (Array.isArray(result)) setData(result[0] ?? null)
      else setData(result)
    } catch (err: any) {
      alert(err.message || 'Failed to delete selected datasets')
    }
  }

  const toggleSelect = (name: string) => {
    setSelectedIds((prev) => {
      const n = new Set(prev)
      if (n.has(name)) n.delete(name)
      else n.add(name)
      return n
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredDatasets.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(filteredDatasets.map((d) => d.name)))
  }

  const exportCSV = () => {
    const headers = ['Name', 'Size', 'Rows', 'Format']
    const rows = filteredDatasets.map((d) => [d.name, d.size, d.rows, d.format])
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'datasets.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(filteredDatasets, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'datasets.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const openEditModal = (dataset: BigData['datasets'][0]) => {
    setEditingDataset(dataset)
    setFormData({ name: dataset.name, description: '', size: parseFloat(dataset.size) || 0, format: dataset.format })
    setFormError(null)
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-pulse-slow flex items-center gap-3"><Database className="w-6 h-6 text-cyan-400" /><span className="text-slate-400">Loading...</span></div></div>
  if (error) return <div className="flex items-center justify-center h-64"><XCircle className="w-12 h-12 text-red-400" /></div>
  if (!data) return null

  const totalRows = data.datasets.reduce((s, d) => s + d.rows, 0)
  const avgDur = data.queries.length > 0 ? data.queries.reduce((s, q) => s + q.duration_ms, 0) / data.queries.length : 0
  const successRate = data.queries.length > 0 ? Math.round((data.queries.filter((q) => q.status === 'completed' || q.status === 'success').length / data.queries.length) * 100) : 0

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Database className="w-8 h-8 text-cyan-400" />
        <div>
          <h1 className="text-2xl font-bold gradient-text">Big Data Platform</h1>
          <p className="text-sm text-[var(--muted)]">Storage, datasets, queries & pipeline</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[{ l: 'Datasets', v: data.datasets.length, I: Layers, c: '#06b6d4' }, { l: 'Total Rows', v: fmtN(totalRows), I: BarChart3, c: '#8b5cf6' }, { l: 'Avg Query', v: fmtD(avgDur), I: Timer, c: '#f59e0b' }, { l: 'Success', v: `${successRate}%`, I: CheckCircle2, c: '#10b981' }].map((s) => (
          <div key={s.l} className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 card-hover">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: `${s.c}15` }}>
                <s.I className="w-5 h-5" style={{ color: s.c }} />
              </div>
              <div>
                <p className="text-xs text-[var(--muted)]">{s.l}</p>
                <p className="text-xl font-bold text-[var(--text)]">{s.v}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <ST icon={HardDrive} title="Storage" sub="Cluster capacity" />
          <Donut used={data.storage.used_tb} total={data.storage.total_tb} />
        </Card>
        <Card>
          <ST icon={Archive} title="Compression" sub="Efficiency" />
          <Compression ratio={data.storage.compression_ratio} used={data.storage.used_tb} />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <ST icon={BarChart3} title="Dataset Sizes" sub="Size comparison" />
          <DatasetBar ds={data.datasets} />
        </Card>
        <Card>
          <ST icon={Activity} title="Query Performance" sub="Duration trends" />
          <QueryChart qs={data.queries} />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <ST icon={Workflow} title="Pipeline" sub="Data flow" />
          <Pipeline />
        </Card>
        <Card>
          <ST icon={Boxes} title="Partitions" sub="Distribution" />
          <Partition />
        </Card>
      </div>

      <Card>
        <ST icon={Gauge} title="Index Performance" sub="Lookup efficiency" />
        <IndexPerf />
      </Card>

      <Card className="bg-gray-900 border-gray-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Datasets</h2>
              <p className="text-xs text-gray-400">{filteredDatasets.length} of {data.datasets.length} datasets</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500 w-48"
              />
            </div>
            <button onClick={() => { setFormData({ name: '', description: '', size: 0, format: 'csv' }); setFormError(null); setShowCreateModal(true) }} className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors">
              <Plus className="w-4 h-4" /> Create
            </button>
            <button onClick={exportCSV} className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-100 text-sm font-medium rounded-lg border border-gray-700 transition-colors">
              <Download className="w-4 h-4" /> CSV
            </button>
            <button onClick={exportJSON} className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-100 text-sm font-medium rounded-lg border border-gray-700 transition-colors">
              <Download className="w-4 h-4" /> JSON
            </button>
            {selectedIds.size > 0 && (
              <button onClick={handleBulkDelete} className="flex items-center gap-1.5 px-3 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors">
                <Trash2 className="w-4 h-4" /> Delete ({selectedIds.size})
              </button>
            )}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-4 text-gray-400 font-medium w-10">
                  <button onClick={toggleSelectAll} className="text-gray-400 hover:text-gray-100 transition-colors">
                    {selectedIds.size === filteredDatasets.length && filteredDatasets.length > 0 ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                  </button>
                </th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Name</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Size</th>
                <th className="text-right py-3 px-4 text-gray-400 font-medium">Rows</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Format</th>
                <th className="text-right py-3 px-4 text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDatasets.map((d, i) => (
                <tr key={i} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/50 transition-colors">
                  <td className="py-3 px-4">
                    <button onClick={() => toggleSelect(d.name)} className="text-gray-400 hover:text-gray-100 transition-colors">
                      {selectedIds.has(d.name) ? <CheckSquare className="w-4 h-4 text-cyan-400" /> : <Square className="w-4 h-4" />}
                    </button>
                  </td>
                  <td className="py-3 px-4 text-gray-100 font-medium">{d.name}</td>
                  <td className="py-3 px-4 text-gray-400">{d.size}</td>
                  <td className="py-3 px-4 text-right text-gray-400">{fmtN(d.rows)}</td>
                  <td className="py-3 px-4"><FmtBadge f={d.format} /></td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => openEditModal(d)} className="p-1.5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors" title="Edit">
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => handleDelete(d.name)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors" title="Delete">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredDatasets.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400">No datasets found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {(showCreateModal || editingDataset) && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => { setShowCreateModal(false); setEditingDataset(null) }}>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100">{editingDataset ? 'Edit Dataset' : 'Create Dataset'}</h3>
              <button onClick={() => { setShowCreateModal(false); setEditingDataset(null) }} className="text-gray-400 hover:text-gray-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={editingDataset ? handleEdit : handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  placeholder="Dataset name"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500 resize-none"
                  placeholder="Dataset description"
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Size (bytes)</label>
                  <input
                    type="number"
                    value={formData.size || ''}
                    onChange={(e) => setFormData((f) => ({ ...f, size: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                    placeholder="0"
                    min="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Format</label>
                  <select
                    value={formData.format}
                    onChange={(e) => setFormData((f) => ({ ...f, format: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                    <option value="parquet">Parquet</option>
                    <option value="avro">Avro</option>
                    <option value="orc">ORC</option>
                    <option value="delta">Delta</option>
                  </select>
                </div>
              </div>
              {formError && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  <span className="text-sm text-red-400">{formError}</span>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setShowCreateModal(false); setEditingDataset(null) }} className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-100 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={formLoading} className="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                  {formLoading ? 'Saving...' : editingDataset ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <Card>
        <ST icon={Search} title="Query History" sub="Recent executions" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">ID</th>
                <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Type</th>
                <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Duration</th>
                <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Rows</th>
                <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.queries.map((q) => (
                <tr key={q.id} className="border-b border-[var(--border)] last:border-0 hover:bg-gray-900/5">
                  <td className="py-3 px-4 font-mono text-xs text-[var(--text)]">{q.id}</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded text-xs bg-slate-500/15 text-slate-400 border border-slate-500/20">{q.type}</span></td>
                  <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtD(q.duration_ms)}</td>
                  <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtN(q.rows_scanned)}</td>
                  <td className="py-3 px-4"><Badge status={q.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
