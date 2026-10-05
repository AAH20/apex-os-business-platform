import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DataSource, ETLJob, DataMart, DataModel } from '../api/client'
import { Database, HardDrive, Search, Layers, Activity, XCircle, Workflow, Boxes, Gauge, Plus, Edit2, Trash2, X, RefreshCw, Server, Table, Download } from 'lucide-react'
import { exportToCSV } from '../hooks/useKeyboardShortcuts'

const SC: Record<string, string> = { completed: '#10b981', running: '#3b82f6', pending: '#f59e0b', failed: '#ef4444', success: '#10b981', active: '#3b82f6', paused: '#f59e0b', inactive: '#64748b', error: '#ef4444', building: '#f59e0b', deprecated: '#64748b', draft: '#94a3b8' }
const FC: Record<string, { bg: string; text: string; border: string }> = { postgresql: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30' }, mysql: { bg: 'bg-cyan-500/15', text: 'text-cyan-400', border: 'border-cyan-500/30' }, s3: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' }, kafka: { bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30' }, api: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' }, csv: { bg: 'bg-rose-500/15', text: 'text-rose-400', border: 'border-rose-500/30' }, bigquery: { bg: 'bg-indigo-500/15', text: 'text-indigo-400', border: 'border-indigo-500/30' }, redshift: { bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30' } }

const fmtN = (n: number) => n == null ? '0' : n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : n.toLocaleString()
const fmtSize = (bytes: number) => bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : bytes >= 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : bytes >= 1e3 ? `${(bytes / 1e3).toFixed(1)} KB` : `${bytes} B`
const fmtD = (ms: number) => ms >= 60000 ? `${(ms / 60000).toFixed(1)}m` : ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`

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

type TabKey = 'sources' | 'etl' | 'marts' | 'models'

interface WarehouseItem { id: number; name: string; description?: string; status?: string; source_type?: string; schedule?: string; mart_type?: string; model_type?: string; schema_name?: string; size_bytes?: number; row_count?: number; duration_ms?: number; table_count?: number; mart_id?: number; tags?: string[]; created_at?: string }

const DataWarehouseManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('sources')
  const [sources, setSources] = useState<DataSource[]>([])
  const [etlJobs, setEtlJobs] = useState<ETLJob[]>([])
  const [marts, setMarts] = useState<DataMart[]>([])
  const [models, setModels] = useState<DataModel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingItem, setEditingItem] = useState<WarehouseItem | null>(null)
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<{ type: TabKey; id: number; name: string } | null>(null)

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [srcRes, etlRes, martRes, modelRes] = await Promise.all([
        api.listDataSources({ limit: 100 }),
        api.listETLJobs({ limit: 100 }),
        api.listDataMarts({ limit: 100 }),
        api.listDataModels({ limit: 100 }),
      ])
      setSources(srcRes)
      setEtlJobs(etlRes)
      setMarts(martRes)
      setModels(modelRes)
    } catch (e: any) {
      setError(e.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, [])

  const filteredSources = sources.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()) || s.source_type.toLowerCase().includes(searchQuery.toLowerCase()))
  const filteredJobs = etlJobs.filter(j => j.name.toLowerCase().includes(searchQuery.toLowerCase()) || j.status.toLowerCase().includes(searchQuery.toLowerCase()))
  const filteredMarts = marts.filter(m => m.name.toLowerCase().includes(searchQuery.toLowerCase()) || m.mart_type.toLowerCase().includes(searchQuery.toLowerCase()))
  const filteredModels = models.filter(m => m.name.toLowerCase().includes(searchQuery.toLowerCase()) || m.model_type.toLowerCase().includes(searchQuery.toLowerCase()))

  const handleDelete = async (type: TabKey, id: number, _name: string) => {
    try {
      if (type === 'sources') await api.deleteDataSource(id)
      else if (type === 'etl') await api.deleteETLJob(id)
      else if (type === 'marts') await api.deleteDataMart(id)
      else await api.deleteDataModel(id)
      setShowDeleteConfirm(null)
      await fetchAll()
    } catch (e: any) {
      alert(e.message || 'Delete failed')
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormLoading(true)
    setFormError(null)
    try {
      const form = e.target as HTMLFormElement
      const fd = new FormData(form)
      const name = fd.get('name') as string
      if (activeTab === 'sources') {
        await api.createDataSource({ name, description: fd.get('description') as string || undefined, source_type: fd.get('source_type') as string || undefined })
      } else if (activeTab === 'etl') {
        await api.createETLJob({ name, description: fd.get('description') as string || undefined, schedule: fd.get('schedule') as string || undefined })
      } else if (activeTab === 'marts') {
        await api.createDataMart({ name, description: fd.get('description') as string || undefined, mart_type: fd.get('mart_type') as string || undefined })
      } else {
        await api.createDataModel({ name, description: fd.get('description') as string || undefined, model_type: fd.get('model_type') as string || undefined })
      }
      setShowCreateModal(false)
      await fetchAll()
    } catch (e: any) {
      setFormError(e.message || 'Create failed')
    } finally {
      setFormLoading(false)
    }
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingItem) return
    setFormLoading(true)
    setFormError(null)
    try {
      const form = e.target as HTMLFormElement
      const fd = new FormData(form)
      const name = fd.get('name') as string
      if (activeTab === 'sources') {
        await api.updateDataSource(editingItem.id, { name, description: fd.get('description') as string || undefined, source_type: fd.get('source_type') as string || undefined })
      } else if (activeTab === 'etl') {
        await api.updateETLJob(editingItem.id, { name, description: fd.get('description') as string || undefined, schedule: fd.get('schedule') as string || undefined })
      } else if (activeTab === 'marts') {
        await api.updateDataMart(editingItem.id, { name, description: fd.get('description') as string || undefined, mart_type: fd.get('mart_type') as string || undefined })
      } else {
        await api.updateDataModel(editingItem.id, { name, description: fd.get('description') as string || undefined, model_type: fd.get('model_type') as string || undefined })
      }
      setEditingItem(null)
      await fetchAll()
    } catch (e: any) {
      setFormError(e.message || 'Update failed')
    } finally {
      setFormLoading(false)
    }
  }

  const openEdit = (item: WarehouseItem) => {
    setEditingItem(item)
    setFormError(null)
  }

  const tabs: { key: TabKey; label: string; icon: React.ElementType; count: number }[] = [
    { key: 'sources', label: 'Data Sources', icon: Server, count: sources.length },
    { key: 'etl', label: 'ETL Jobs', icon: Workflow, count: etlJobs.length },
    { key: 'marts', label: 'Data Marts', icon: Boxes, count: marts.length },
    { key: 'models', label: 'Data Models', icon: Table, count: models.length },
  ]

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-pulse-slow flex items-center gap-3"><Database className="w-6 h-6 text-cyan-400" /><span className="text-slate-400">Loading...</span></div></div>
  if (error) return <div className="flex items-center justify-center h-64"><XCircle className="w-12 h-12 text-red-400" /></div>

  const totalSize = (marts || []).reduce((s, m) => s + (m.size_bytes ?? 0), 0)
  const runningJobs = etlJobs.filter(j => j.status === 'running').length
  const failedJobs = etlJobs.filter(j => j.status === 'failed').length

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Database className="w-8 h-8 text-cyan-400" />
        <div>
          <h1 className="text-2xl font-bold gradient-text">Data Warehouse</h1>
          <p className="text-sm text-[var(--muted)]">Sources, ETL pipelines, marts & models</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[{ l: 'Sources', v: sources.length, I: Server, c: '#06b6d4' }, { l: 'ETL Jobs', v: etlJobs.length, I: Workflow, c: '#8b5cf6' }, { l: 'Data Marts', v: marts.length, I: Boxes, c: '#f59e0b' }, { l: 'Total Size', v: fmtSize(totalSize), I: HardDrive, c: '#10b981' }].map(s => (
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
        <Card>
          <ST icon={Activity} title="ETL Status" sub="Job health overview" />
          <div className="space-y-3">
            {[{ l: 'Running', v: runningJobs, c: '#3b82f6' }, { l: 'Failed', v: failedJobs, c: '#ef4444' }, { l: 'Completed', v: etlJobs.filter(j => j.status === 'completed').length, c: '#10b981' }, { l: 'Pending', v: etlJobs.filter(j => j.status === 'pending').length, c: '#f59e0b' }].map(item => (
              <div key={item.l} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: item.c }} />
                  <span className="text-sm text-[var(--muted)]">{item.l}</span>
                </div>
                <span className="text-sm font-semibold text-[var(--text)]">{item.v}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <ST icon={Gauge} title="Storage" sub="Mart sizes" />
          <div className="space-y-3">
            {marts.slice(0, 5).map(m => (
              <div key={m.id} className="flex items-center justify-between">
                <span className="text-sm text-[var(--muted)] truncate mr-2">{m.name}</span>
                <span className="text-sm font-semibold text-[var(--text)]">{fmtSize(m.size_bytes)}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <ST icon={Layers} title="Row Counts" sub="Model volumes" />
          <div className="space-y-3">
            {models.slice(0, 5).map(m => (
              <div key={m.id} className="flex items-center justify-between">
                <span className="text-sm text-[var(--muted)] truncate mr-2">{m.name}</span>
                <span className="text-sm font-semibold text-[var(--text)]">{fmtN(m.row_count)}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="text-lg font-semibold text-[var(--text)]">Warehouse Explorer</h2>
              <p className="text-xs text-[var(--muted)]">Browse and manage warehouse resources</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="Search..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className="pl-8 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500 w-48" />
            </div>
            <button onClick={() => { setFormError(null); setShowCreateModal(true) }} className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors">
              <Plus className="w-4 h-4" /> Create
            </button>
            <button onClick={fetchAll} className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-100 text-sm font-medium rounded-lg border border-gray-700 transition-colors">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
            <button onClick={() => { const data = activeTab === 'sources' ? sources : activeTab === 'etl' ? etlJobs : activeTab === 'marts' ? marts : models; exportToCSV(data as unknown as Record<string, unknown>[], `${activeTab}_export.csv`); }} className="flex items-center gap-1.5 px-3 py-2 bg-green-700 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors">
              <Download className="w-4 h-4" /> Export CSV
            </button>
          </div>
        </div>

        <div className="flex gap-1 mb-4 border-b border-[var(--border)]">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)} className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${activeTab === t.key ? 'bg-cyan-500/10 text-cyan-400 border-b-2 border-cyan-400' : 'text-[var(--muted)] hover:text-[var(--text)]'}`}>
              <t.icon className="w-4 h-4" />
              {t.label}
              <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs bg-gray-900/5">{t.count}</span>
            </button>
          ))}
        </div>

        {activeTab === 'sources' && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Name</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Type</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Status</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Tags</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSources.map(s => (
                  <tr key={s.id} className="border-b border-[var(--border)] last:border-0 hover:bg-gray-900/5">
                    <td className="py-3 px-4 text-[var(--text)] font-medium">{s.name}</td>
                    <td className="py-3 px-4"><FmtBadge f={s.source_type} /></td>
                    <td className="py-3 px-4"><Badge status={s.status} /></td>
                    <td className="py-3 px-4 text-[var(--muted)] text-xs">{s.tags.join(', ')}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openEdit(s)} className="p-1.5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors"><Edit2 className="w-3.5 h-3.5" /></button>
                        <button onClick={() => setShowDeleteConfirm({ type: 'sources', id: s.id, name: s.name })} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredSources.length === 0 && <tr><td colSpan={5} className="py-8 text-center text-gray-400">No data sources found</td></tr>}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'etl' && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Name</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Schedule</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Status</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Rows</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Duration</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map(j => (
                  <tr key={j.id} className="border-b border-[var(--border)] last:border-0 hover:bg-gray-900/5">
                    <td className="py-3 px-4 text-[var(--text)] font-medium">{j.name}</td>
                    <td className="py-3 px-4 text-[var(--muted)] font-mono text-xs">{j.schedule || '—'}</td>
                    <td className="py-3 px-4"><Badge status={j.status} /></td>
                    <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtN(j.row_count)}</td>
                    <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtD(j.duration_ms)}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openEdit(j)} className="p-1.5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors"><Edit2 className="w-3.5 h-3.5" /></button>
                        <button onClick={() => setShowDeleteConfirm({ type: 'etl', id: j.id, name: j.name })} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredJobs.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-gray-400">No ETL jobs found</td></tr>}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'marts' && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Name</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Type</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Schema</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Status</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Tables</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Size</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredMarts.map(m => (
                  <tr key={m.id} className="border-b border-[var(--border)] last:border-0 hover:bg-gray-900/5">
                    <td className="py-3 px-4 text-[var(--text)] font-medium">{m.name}</td>
                    <td className="py-3 px-4"><span className="px-2 py-0.5 rounded text-xs bg-slate-500/15 text-slate-400 border border-slate-500/20">{m.mart_type}</span></td>
                    <td className="py-3 px-4 text-[var(--muted)] font-mono text-xs">{m.schema_name || '—'}</td>
                    <td className="py-3 px-4"><Badge status={m.status} /></td>
                    <td className="py-3 px-4 text-right text-[var(--muted)]">{m.table_count}</td>
                    <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtSize(m.size_bytes)}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openEdit(m)} className="p-1.5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors"><Edit2 className="w-3.5 h-3.5" /></button>
                        <button onClick={() => setShowDeleteConfirm({ type: 'marts', id: m.id, name: m.name })} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredMarts.length === 0 && <tr><td colSpan={7} className="py-8 text-center text-gray-400">No data marts found</td></tr>}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'models' && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Name</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Type</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Mart</th>
                  <th className="text-left py-3 px-4 text-[var(--muted)] font-medium">Status</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Rows</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Size</th>
                  <th className="text-right py-3 px-4 text-[var(--muted)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredModels.map(m => (
                  <tr key={m.id} className="border-b border-[var(--border)] last:border-0 hover:bg-gray-900/5">
                    <td className="py-3 px-4 text-[var(--text)] font-medium">{m.name}</td>
                    <td className="py-3 px-4"><span className="px-2 py-0.5 rounded text-xs bg-slate-500/15 text-slate-400 border border-slate-500/20">{m.model_type}</span></td>
                    <td className="py-3 px-4 text-[var(--muted)] text-xs">{m.mart_id || '—'}</td>
                    <td className="py-3 px-4"><Badge status={m.status} /></td>
                    <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtN(m.row_count)}</td>
                    <td className="py-3 px-4 text-right text-[var(--muted)]">{fmtSize(m.size_bytes)}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openEdit(m)} className="p-1.5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors"><Edit2 className="w-3.5 h-3.5" /></button>
                        <button onClick={() => setShowDeleteConfirm({ type: 'models', id: m.id, name: m.name })} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredModels.length === 0 && <tr><td colSpan={7} className="py-8 text-center text-gray-400">No data models found</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {(showCreateModal || editingItem) && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100">{editingItem ? 'Edit' : 'Create'} {activeTab === 'sources' ? 'Data Source' : activeTab === 'etl' ? 'ETL Job' : activeTab === 'marts' ? 'Data Mart' : 'Data Model'}</h3>
              <button onClick={() => { setShowCreateModal(false); setEditingItem(null) }} className="text-gray-400 hover:text-gray-100"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={editingItem ? handleEdit : handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Name</label>
                <input name="name" type="text" defaultValue={editingItem?.name || ''} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500" placeholder="Name" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
                <textarea name="description" defaultValue={editingItem?.description || ''} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500 resize-none" placeholder="Description" rows={3} />
              </div>
              {activeTab === 'sources' && (
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Source Type</label>
                  <select name="source_type" defaultValue={editingItem?.source_type || 'postgresql'} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-cyan-500">
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                    <option value="s3">S3</option>
                    <option value="kafka">Kafka</option>
                    <option value="api">API</option>
                    <option value="csv">CSV</option>
                    <option value="bigquery">BigQuery</option>
                    <option value="redshift">Redshift</option>
                  </select>
                </div>
              )}
              {activeTab === 'etl' && (
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Schedule (cron)</label>
                  <input name="schedule" type="text" defaultValue={editingItem?.schedule || ''} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500" placeholder="0 * * * *" />
                </div>
              )}
              {activeTab === 'marts' && (
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Mart Type</label>
                  <select name="mart_type" defaultValue={editingItem?.mart_type || 'star'} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-cyan-500">
                    <option value="star">Star</option>
                    <option value="snowflake">Snowflake</option>
                    <option value="flat">Flat</option>
                    <option value="denormalized">Denormalized</option>
                  </select>
                </div>
              )}
              {activeTab === 'models' && (
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Model Type</label>
                  <select name="model_type" defaultValue={editingItem?.model_type || 'table'} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-cyan-500">
                    <option value="table">Table</option>
                    <option value="view">View</option>
                    <option value="materialized_view">Materialized View</option>
                    <option value="external">External</option>
                  </select>
                </div>
              )}
              {formError && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  <span className="text-sm text-red-400">{formError}</span>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setShowCreateModal(false); setEditingItem(null) }} className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-100 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors">Cancel</button>
                <button type="submit" disabled={formLoading} className="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">{formLoading ? 'Saving...' : editingItem ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-100 mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete <strong>{showDeleteConfirm.name}</strong>? This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-100 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm.type, showDeleteConfirm.id, showDeleteConfirm.name)} className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DataWarehouseManagement
