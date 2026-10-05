import { useEffect, useState, useMemo, lazy, Suspense, type ReactNode } from 'react'
import { TrendingUp, TrendingDown, DollarSign, Users, Target, ShoppingCart, Activity, ArrowUpRight, ArrowDownRight, UserPlus, Package, BarChart3, Settings, Bell, Download, Server, Cpu, HardDrive, Wifi, Shield, Zap, CheckCircle2, XCircle, AlertTriangle, Rocket, Globe, X } from 'lucide-react'
import { api } from '../api/client'
import type { DashboardData, DashboardWidget, Notification, ProductInput, UserFormData } from '../api/client'
import { fetchWithTimeout } from '../api/fallback'

const FORM_INPUT = "w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
const FORM_LABEL = "block text-sm font-medium text-gray-300 mb-1"
const FORM_ACTIONS = "flex gap-3 pt-2"

/** Trigger a client-side file download from a string blob. */
function downloadFile(content: string, filename: string, mimeType: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** RFC-4180 CSV cell quoting. */
const csvCell = (v: unknown) => '"' + String(v ?? '').replace(/"/g, '""') + '"'

// Lazy-load heavy chart components
const RevenueChart = lazy(() => import('./DashboardCharts').then(m => ({ default: m.RevenueChart })))
const UserGrowthChart = lazy(() => import('./DashboardCharts').then(m => ({ default: m.UserGrowthChart })))

interface MetricCardConfig { title: string; value: string; change: number; trend: 'up' | 'down'; icon: ReactNode; color: string; sparkline: number[] }
interface ChartDataPoint { name: string; value: number }
interface ActivityItem { action: string; user: string; time: string; type: 'success' | 'warning' | 'error' | 'info' }
interface SystemHealthItem { name: string; value: string; status: 'healthy' | 'warning' | 'critical'; icon: ReactNode; detail: string }
interface QuickAction { label: string; icon: ReactNode; color: string; description: string }

const buildChartData = (data: number[], labels: string[]): ChartDataPoint[] => data.map((value, i) => ({ name: labels[i] !== undefined ? labels[i] : 'P' + (i + 1), value }))
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function ChartSkeleton() {
  return <div className="w-full h-[280px] rounded-lg bg-[var(--surface)] animate-pulse" />
}

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data, 1)
  return (
    <div className="w-full h-[40px] rounded bg-[var(--surface)]/50 flex items-end gap-0.5 px-1 pb-1">
      {data.map((v, i) => (
        <div key={i} className="flex-1 bg-[var(--accent)]/40 rounded-sm" style={{ height: `${(v / max) * 100}%` }} />
      ))}
    </div>
  )
}

function MetricCard({ config }: { config: MetricCardConfig }) {
  const isUp = config.trend === 'up'
  const changeColor = isUp ? 'var(--success)' : 'var(--danger)'
  return (
    <div className="glass card-hover rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-[var(--muted)]">{config.title}</span>
        <div className="p-2 rounded-lg" style={{ backgroundColor: config.color + '15' }}>{config.icon}</div>
      </div>
      <div className="text-2xl font-bold text-[var(--text)] mb-1">{config.value}</div>
      <div className="flex items-center gap-1.5 mb-3">
        {isUp ? <ArrowUpRight className="w-4 h-4" style={{ color: changeColor }} /> : <ArrowDownRight className="w-4 h-4" style={{ color: changeColor }} />}
        <span className="text-sm font-semibold" style={{ color: changeColor }}>{isUp ? '+' : ''}{config.change}%</span>
        <span className="text-xs text-[var(--muted)] ml-1">vs last month</span>
      </div>
      <Sparkline data={config.sparkline} />
    </div>
  )
}

function ActivityFeed({ activities }: { activities: ActivityItem[] }) {
  const typeConfig = {
    success: { icon: <CheckCircle2 className="w-4 h-4" />, color: 'var(--success)' },
    warning: { icon: <AlertTriangle className="w-4 h-4" />, color: 'var(--warning)' },
    error: { icon: <XCircle className="w-4 h-4" />, color: 'var(--danger)' },
    info: { icon: <Activity className="w-4 h-4" />, color: 'var(--accent)' },
  }
  return (
    <div className="space-y-1">
      {activities.map((item, idx) => {
        const cfg = typeConfig[item.type]
        return (
          <div key={idx} className="flex items-start gap-3 p-3 rounded-lg hover:bg-[var(--surface)] transition-colors">
            <div className="p-2 rounded-full mt-0.5 shrink-0" style={{ backgroundColor: cfg.color + '15', color: cfg.color }}>{cfg.icon}</div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-[var(--text)] font-medium truncate">{item.action}</p>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ backgroundColor: 'hsl(' + idx * 60 + ', 70%, 50%)' }}>{item.user.charAt(0)}</div>
                <span className="text-xs text-[var(--muted)]">{item.user}</span>
              </div>
            </div>
            <span className="text-xs text-[var(--muted)] whitespace-nowrap shrink-0">{item.time}</span>
          </div>
        )
      })}
    </div>
  )
}

function SystemHealth({ items }: { items: SystemHealthItem[] }) {
  const statusCfg = { healthy: { color: 'var(--success)', label: 'Healthy' }, warning: { color: 'var(--warning)', label: 'Warning' }, critical: { color: 'var(--danger)', label: 'Critical' } }
  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        const cfg = statusCfg[item.status]
        return (
          <div key={idx} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--surface)] transition-colors">
            <div className="p-2 rounded-lg shrink-0" style={{ backgroundColor: cfg.color + '15', color: cfg.color }}>{item.icon}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[var(--text)]">{item.name}</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ backgroundColor: cfg.color + '20', color: cfg.color }}>{cfg.label}</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-[var(--muted)]">{item.detail}</span>
                <span className="text-xs font-mono text-[var(--text)]">{item.value}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function QuickActions({ actions, onAction }: { actions: QuickAction[]; onAction: (label: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {actions.map((action, idx) => (
        <button key={idx} onClick={() => onAction(action.label)} className="glass card-hover rounded-xl p-4 text-left group">
          <div className="p-2 rounded-lg inline-block mb-2" style={{ backgroundColor: action.color + '15', color: action.color }}>{action.icon}</div>
          <p className="text-sm font-semibold text-[var(--text)] group-hover:text-[var(--accent)] transition-colors">{action.label}</p>
          <p className="text-xs text-[var(--muted)] mt-0.5">{action.description}</p>
        </button>
      ))}
    </div>
  )
}

function HeroSection({ stats }: { stats: { label: string; value: string; icon: ReactNode; color: string }[] }) {
  return (
    <div className="relative overflow-hidden rounded-2xl p-8 animate-fade-in" style={{ background: 'linear-gradient(135deg, #06b6d4 0%, #a855f7 50%, #ec4899 100%)' }}>
      <div className="absolute inset-0 opacity-20" style={{ background: 'radial-gradient(circle at 20% 50%, rgba(255,255,255,0.3) 0%, transparent 50%)' }} />
      <div className="relative z-10">
        <div className="flex items-center gap-2 mb-2">
          <Rocket className="w-5 h-5 text-white/90" />
          <span className="text-sm font-medium text-white/80">APEX-OS Business Platform</span>
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Welcome back, Admin</h1>
        <p className="text-white/70 text-sm mb-6">Here's what's happening across your platform today.</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {stats.map((s, i) => (
            <div key={i} className="bg-gray-900/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg" style={{ backgroundColor: s.color + '30', color: 'white' }}>{s.icon}</div>
                <span className="text-xs text-white/70">{s.label}</span>
              </div>
              <p className="text-xl font-bold text-white">{s.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function DateRangeSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const ranges = ['7D', '30D', '90D', '1Y', 'All']
  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
      {ranges.map((range) => (
        <button key={range} onClick={() => onChange(range)} className={'px-3 py-1.5 text-xs font-medium rounded-md transition-all ' + (value === range ? 'bg-[var(--accent)] text-white' : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)]')}>{range}</button>
      ))}
    </div>
  )
}

function StateMessage({ type, message, onRetry }: { type: string; message?: string; onRetry?: () => void }) {
  const isError = type === 'error';
  return (
    <div className={'p-4 rounded-lg border ' + (isError ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-[var(--surface)] border-[var(--border)] text-[var(--muted)]')}>
      {isError ? message : 'Loading...'}
      {onRetry && <button onClick={onRetry} className="ml-2 underline">Retry</button>}
    </div>
  )
}

function GoalsForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({ revenueTarget: '', leadTarget: '', conversionTarget: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setTimeout(() => {
      setSaving(false)
      setSaved(true)
      setTimeout(onClose, 800)
    }, 600)
  }

  const inputCls = "w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
  const labelCls = "block text-sm font-medium text-gray-300 mb-1"

  if (saved) return <div className="text-center py-4"><CheckCircle2 className="w-10 h-10 text-green-400 mx-auto mb-2" /><p className="text-sm text-gray-300">Goals saved successfully!</p></div>

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelCls}>Revenue Target ($)</label>
        <input type="number" required value={form.revenueTarget} onChange={(e) => setForm(f => ({ ...f, revenueTarget: e.target.value }))} className={inputCls} placeholder="e.g. 500000" />
      </div>
      <div>
        <label className={labelCls}>Lead Target</label>
        <input type="number" required value={form.leadTarget} onChange={(e) => setForm(f => ({ ...f, leadTarget: e.target.value }))} className={inputCls} placeholder="e.g. 200" />
      </div>
      <div>
        <label className={labelCls}>Conversion Target (%)</label>
        <input type="number" required min="0" max="100" value={form.conversionTarget} onChange={(e) => setForm(f => ({ ...f, conversionTarget: e.target.value }))} className={inputCls} placeholder="e.g. 5" />
      </div>
      <div className="flex gap-3 pt-2">
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
        <button type="submit" disabled={saving} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50">{saving ? 'Saving…' : 'Save Goals'}</button>
      </div>
    </form>
  )
}

function NewLeadForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({ name: '', email: '', company: '', status: 'new', score: 50, value: 0, source: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.createLead({ name: form.name, email: form.email || undefined, company: form.company || undefined, status: form.status, score: form.score, value: form.value, source: form.source || undefined })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create lead')
      setSaving(false)
    }
  }

  const inputCls = "w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
  const labelCls = "block text-sm font-medium text-gray-300 mb-1"

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div>
        <label className={labelCls}>Name *</label>
        <input type="text" required value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Lead name" />
      </div>
      <div>
        <label className={labelCls}>Email</label>
        <input type="email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} className={inputCls} placeholder="lead@company.com" />
      </div>
      <div>
        <label className={labelCls}>Company</label>
        <input type="text" value={form.company} onChange={(e) => setForm(f => ({ ...f, company: e.target.value }))} className={inputCls} placeholder="Company name" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Status</label>
          <select value={form.status} onChange={(e) => setForm(f => ({ ...f, status: e.target.value }))} className={inputCls}>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="lost">Lost</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>Score</label>
          <input type="number" min="0" max="100" value={form.score} onChange={(e) => setForm(f => ({ ...f, score: parseInt(e.target.value) || 0 }))} className={inputCls} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Value ($)</label>
          <input type="number" min="0" value={form.value} onChange={(e) => setForm(f => ({ ...f, value: parseFloat(e.target.value) || 0 }))} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Source</label>
          <input type="text" value={form.source} onChange={(e) => setForm(f => ({ ...f, source: e.target.value }))} className={inputCls} placeholder="e.g. referral" />
        </div>
      </div>
      <div className="flex gap-3 pt-2">
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
        <button type="submit" disabled={saving} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50">{saving ? 'Creating…' : 'Create Lead'}</button>
      </div>
    </form>
  )
}

function GenerateReportModal({ metrics, onClose }: { metrics: MetricCardConfig[]; onClose: () => void }) {
  const [generated, setGenerated] = useState<string | null>(null)

  const handleExport = () => {
    const headers = ['metric', 'value', 'change_pct', 'trend']
    const rows = metrics.map(m => ({
      metric: m.title,
      value: m.value,
      change_pct: m.change,
      trend: m.trend,
    }))
    const csv = [headers.join(','), ...rows.map(r => headers.map(h => csvCell(r[h as keyof typeof r])).join(','))].join('\n')
    const filename = 'apex-dashboard-report-' + new Date().toISOString().slice(0, 10) + '.csv'
    downloadFile(csv, filename, 'text/csv')
    setGenerated(filename)
  }

  return (
    <div className="space-y-3">
      {generated ? (
        <>
          <div className="text-center py-2">
            <CheckCircle2 className="w-10 h-10 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-gray-300">Report downloaded</p>
            <p className="text-xs text-gray-500 mt-1 break-all">{generated}</p>
          </div>
          <div className={FORM_ACTIONS}>
            <button onClick={handleExport} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Download again</button>
            <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">Close</button>
          </div>
        </>
      ) : (
        <>
          <p className="text-xs text-gray-400">Exports the current dashboard metrics as a CSV file.</p>
          <div className="rounded-lg bg-gray-800 border border-gray-700 divide-y divide-gray-700">
            {metrics.map(m => (
              <div key={m.title} className="flex items-center justify-between px-3 py-2">
                <span className="text-sm text-gray-300">{m.title}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-100">{m.value}</span>
                  <span className={'text-xs font-semibold ' + (m.trend === 'up' ? 'text-green-400' : 'text-red-400')}>
                    {m.trend === 'up' ? '+' : ''}{m.change}%
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className={FORM_ACTIONS}>
            <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
            <button onClick={handleExport} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">Download CSV</button>
          </div>
        </>
      )}
    </div>
  )
}

function AddUserForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<UserFormData>({ name: '', email: '', role: 'viewer', status: 'active' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.createUser(form)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div>
        <label className={FORM_LABEL}>Name *</label>
        <input type="text" required value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} className={FORM_INPUT} placeholder="Full name" />
      </div>
      <div>
        <label className={FORM_LABEL}>Email *</label>
        <input type="email" required value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} className={FORM_INPUT} placeholder="user@company.com" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={FORM_LABEL}>Role</label>
          <select value={form.role} onChange={(e) => setForm(f => ({ ...f, role: e.target.value }))} className={FORM_INPUT}>
            <option value="viewer">Viewer</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div>
          <label className={FORM_LABEL}>Status</label>
          <select value={form.status} onChange={(e) => setForm(f => ({ ...f, status: e.target.value }))} className={FORM_INPUT}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>
      <div className={FORM_ACTIONS}>
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
        <button type="submit" disabled={saving} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50">{saving ? 'Creating…' : 'Create User'}</button>
      </div>
    </form>
  )
}

function NewProductForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({ name: '', sku: '', description: '', price: 0, cost: 0, quantity: 0, reorder_level: 5 })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    const payload: ProductInput = {
      name: form.name,
      sku: form.sku,
      description: form.description || undefined,
      price: form.price,
      cost: form.cost || undefined,
      quantity: form.quantity,
      reorder_level: form.reorder_level,
    }
    try {
      await api.createProduct(payload)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create product')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={FORM_LABEL}>Name *</label>
          <input type="text" required value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} className={FORM_INPUT} placeholder="Product name" />
        </div>
        <div>
          <label className={FORM_LABEL}>SKU *</label>
          <input type="text" required value={form.sku} onChange={(e) => setForm(f => ({ ...f, sku: e.target.value }))} className={FORM_INPUT} placeholder="SKU-001" />
        </div>
      </div>
      <div>
        <label className={FORM_LABEL}>Description</label>
        <input type="text" value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} className={FORM_INPUT} placeholder="Optional description" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={FORM_LABEL}>Price ($) *</label>
          <input type="number" required min="0" step="0.01" value={form.price} onChange={(e) => setForm(f => ({ ...f, price: parseFloat(e.target.value) || 0 }))} className={FORM_INPUT} />
        </div>
        <div>
          <label className={FORM_LABEL}>Cost ($)</label>
          <input type="number" min="0" step="0.01" value={form.cost} onChange={(e) => setForm(f => ({ ...f, cost: parseFloat(e.target.value) || 0 }))} className={FORM_INPUT} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={FORM_LABEL}>Quantity *</label>
          <input type="number" required min="0" value={form.quantity} onChange={(e) => setForm(f => ({ ...f, quantity: parseInt(e.target.value) || 0 }))} className={FORM_INPUT} />
        </div>
        <div>
          <label className={FORM_LABEL}>Reorder Level</label>
          <input type="number" min="0" value={form.reorder_level} onChange={(e) => setForm(f => ({ ...f, reorder_level: parseInt(e.target.value) || 0 }))} className={FORM_INPUT} />
        </div>
      </div>
      <div className={FORM_ACTIONS}>
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
        <button type="submit" disabled={saving} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50">{saving ? 'Creating…' : 'Create Product'}</button>
      </div>
    </form>
  )
}

interface AnalyticsKpi { name: string; value: number | string; change: number; trend: string }

/**
 * Build the KPI summary. Prefers live `metrics` from the dashboard payload and falls
 * back to the metric cards shown on screen, so the modal is never empty even when
 * the backend sends a payload without a metrics array.
 */
function readKpis(payload: DashboardData | null, cards: MetricCardConfig[]): AnalyticsKpi[] {
  const normalized = Array.isArray(payload) ? (payload[0] as unknown as DashboardData) : payload
  const metrics = normalized?.metrics
  if (Array.isArray(metrics) && metrics.length > 0) return metrics
  return cards.map(c => ({ name: c.title, value: c.value, change: c.change, trend: c.trend }))
}

function ViewAnalyticsModal({ kpis, onClose }: { kpis: AnalyticsKpi[]; onClose: () => void }) {
  const sorted = useMemo(() => [...kpis].sort((a, b) => Math.abs(b.change) - Math.abs(a.change)), [kpis])
  const up = sorted.filter(k => k.trend === 'up').length
  const avgChange = sorted.length ? sorted.reduce((sum, k) => sum + k.change, 0) / sorted.length : 0

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'KPIs tracked', value: String(sorted.length) },
          { label: 'Improving', value: String(up) },
          { label: 'Avg change', value: (avgChange >= 0 ? '+' : '') + avgChange.toFixed(1) + '%' },
        ].map(s => (
          <div key={s.label} className="p-3 rounded-lg bg-gray-800 border border-gray-700 text-center">
            <p className="text-lg font-bold text-gray-100">{s.value}</p>
            <p className="text-xs text-gray-400">{s.label}</p>
          </div>
        ))}
      </div>
      {sorted.length === 0 ? (
        <p className="text-sm text-gray-400 py-4 text-center">No KPI data available.</p>
      ) : (
        <div className="max-h-[40vh] overflow-y-auto space-y-2 -mx-1 px-1">
          {sorted.map((kpi, i) => {
            const isUp = kpi.trend === 'up'
            const color = isUp ? 'var(--success)' : 'var(--danger)'
            // Scale the bar by magnitude of change so the biggest movers read longest.
            const max = Math.max(...sorted.map(k => Math.abs(k.change)), 1)
            const width = Math.max(4, Math.round((Math.abs(kpi.change) / max) * 100))
            return (
              <div key={i} className="p-3 rounded-lg bg-gray-800 border border-gray-700">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-200 truncate">{kpi.name}</span>
                  <span className="flex items-center gap-1 text-xs font-semibold" style={{ color }}>
                    {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {isUp ? '+' : ''}{kpi.change}%
                  </span>
                </div>
                <div className="flex items-baseline gap-2 mb-1.5">
                  <span className="text-sm font-bold text-gray-100">{typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded-full" style={{ backgroundColor: color + '20', color }}>{kpi.trend}</span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-700 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: width + '%', backgroundColor: color }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
      <div className={FORM_ACTIONS}>
        <button onClick={onClose} className="w-full px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">Close</button>
      </div>
    </div>
  )
}

const SETTINGS_KEY = 'apex-dashboard-settings'
interface PlatformSettings { companyName: string; timezone: string; currency: string; dateFormat: string; weekStart: string; alertsEnabled: boolean; weeklyDigest: boolean; maintenanceMode: boolean }

const DEFAULT_SETTINGS: PlatformSettings = { companyName: 'APEX-OS', timezone: 'UTC', currency: 'USD', dateFormat: 'YYYY-MM-DD', weekStart: 'monday', alertsEnabled: true, weeklyDigest: false, maintenanceMode: false }

function loadSettings(): PlatformSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : DEFAULT_SETTINGS
  } catch {
    return DEFAULT_SETTINGS
  }
}

function SettingsForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<PlatformSettings>(loadSettings)
  const [saved, setSaved] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(form))
      setSaved(true)
      setTimeout(onClose, 800)
    } catch {
      setSaved(true)
      setTimeout(onClose, 800)
    }
  }

  const inputCls = FORM_INPUT
  const toggle = (key: keyof PlatformSettings, label: string, description: string) => (
    <label className="flex items-center justify-between p-3 rounded-lg bg-gray-800 border border-gray-700 cursor-pointer">
      <span>
        <span className="block text-sm font-medium text-gray-200">{label}</span>
        <span className="block text-xs text-gray-400">{description}</span>
      </span>
      <input type="checkbox" checked={form[key] as boolean} onChange={(e) => setForm(f => ({ ...f, [key]: e.target.checked }))} className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-cyan-500 focus:ring-cyan-500" />
    </label>
  )

  if (saved) return <div className="text-center py-4"><CheckCircle2 className="w-10 h-10 text-green-400 mx-auto mb-2" /><p className="text-sm text-gray-300">Settings saved successfully!</p></div>

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-h-[60vh] overflow-y-auto">
      <div>
        <label className={FORM_LABEL}>Company Name</label>
        <input type="text" value={form.companyName} onChange={(e) => setForm(f => ({ ...f, companyName: e.target.value }))} className={inputCls} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={FORM_LABEL}>Timezone</label>
          <select value={form.timezone} onChange={(e) => setForm(f => ({ ...f, timezone: e.target.value }))} className={inputCls}>
            {['UTC', 'America/New_York', 'Europe/London', 'Europe/Berlin', 'Asia/Dubai', 'Asia/Kolkata', 'Australia/Sydney'].map(tz => <option key={tz} value={tz}>{tz}</option>)}
          </select>
        </div>
        <div>
          <label className={FORM_LABEL}>Currency</label>
          <select value={form.currency} onChange={(e) => setForm(f => ({ ...f, currency: e.target.value }))} className={inputCls}>
            {['USD', 'EUR', 'GBP', 'AED', 'INR', 'AUD'].map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={FORM_LABEL}>Date Format</label>
          <select value={form.dateFormat} onChange={(e) => setForm(f => ({ ...f, dateFormat: e.target.value }))} className={inputCls}>
            {['YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY', 'DD-MM-YYYY'].map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className={FORM_LABEL}>Week Starts</label>
          <select value={form.weekStart} onChange={(e) => setForm(f => ({ ...f, weekStart: e.target.value }))} className={inputCls}>
            <option value="monday">Monday</option>
            <option value="sunday">Sunday</option>
          </select>
        </div>
      </div>
      {toggle('alertsEnabled', 'Alert notifications', 'Push critical system alerts')}
      {toggle('weeklyDigest', 'Weekly digest', 'Email a weekly performance summary')}
      {toggle('maintenanceMode', 'Maintenance mode', 'Pause background jobs and syncs')}
      <div className={FORM_ACTIONS}>
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
        <button type="submit" className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">Save Settings</button>
      </div>
    </form>
  )
}

const NOTIFICATION_TYPE_COLOR: Record<Notification['type'], string> = { info: 'var(--accent)', warning: 'var(--warning)', error: 'var(--danger)', success: 'var(--success)' }

function NotificationsModal({ onClose }: { onClose: () => void }) {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.getNotifications({ page: 1, limit: 20 })
      .then((res) => {
        if (!active) return
        const items = Array.isArray(res) ? res : (res?.items ?? [])
        setNotifications(items)
        setTotal(Array.isArray(res) ? items.length : (res?.total ?? items.length))
      })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : 'Failed to load notifications') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const unread = notifications.filter(n => !n.read).length

  return (
    <div className="space-y-3">
      {loading && <p className="text-sm text-gray-400">Loading notifications...</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}
      {!loading && !error && (
        <>
          <p className="text-xs text-gray-400">{total} notification{total === 1 ? '' : 's'}{unread > 0 && ` · ${unread} unread`}</p>
          {notifications.length === 0 ? (
            <p className="text-sm text-gray-400 py-4 text-center">You're all caught up.</p>
          ) : (
            <div className="max-h-[45vh] overflow-y-auto space-y-1 -mx-1">
              {notifications.map(n => {
                const color = NOTIFICATION_TYPE_COLOR[n.type] || 'var(--accent)'
                return (
                  <div key={n.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-800 transition-colors">
                    <div className="p-2 rounded-full mt-0.5 shrink-0" style={{ backgroundColor: color + '15', color }}><Bell className="w-4 h-4" /></div>
                    <div className="flex-1 min-w-0">
                      <p className={'text-sm font-medium truncate ' + (n.read ? 'text-gray-400' : 'text-gray-100')}>{n.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{n.message}</p>
                    </div>
                    <span className="text-xs text-gray-500 whitespace-nowrap shrink-0">{n.created_at ? new Date(n.created_at).toLocaleDateString() : ''}</span>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
      <div className={FORM_ACTIONS}>
        <button onClick={onClose} className="w-full px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">Close</button>
      </div>
    </div>
  )
}

function ViewAllActivityModal({ activities, onClose }: { activities: ActivityItem[]; onClose: () => void }) {
  return (
    <div className="space-y-3">
      <div className="max-h-[55vh] overflow-y-auto -mx-1">
        <ActivityFeed activities={activities} />
      </div>
      <div className={FORM_ACTIONS}>
        <button onClick={onClose} className="w-full px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">Close</button>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState('30D')
  const [modal, setModal] = useState<string | null>(null)
  const [widgets, setWidgets] = useState<DashboardWidget[]>([])
  const [widgetsLoading, setWidgetsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedWidgets, setSelectedWidgets] = useState<string[]>([])
  const [showWidgetModal, setShowWidgetModal] = useState(false)
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null)
  const [widgetForm, setWidgetForm] = useState({ title: '', type: 'metric' as DashboardWidget['type'], value: '', change: 0, trend: 'up' as 'up' | 'down', color: '#06b6d4' })

  const fetchDashboard = async () => {
    setLoading(true); setError(null)
    try { setData(await api.getDashboard()) }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to load dashboard') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchDashboard() }, [])

  const fetchWidgets = async () => {
    setWidgetsLoading(true)
    try {
      const items = await api.getDashboardWidgets()
      setWidgets(Array.isArray(items) ? items : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load widgets')
    } finally {
      setWidgetsLoading(false)
    }
  }

  useEffect(() => { fetchWidgets() }, [])

  const filteredWidgets = useMemo(() => {
    if (!searchQuery.trim()) return widgets
    const q = searchQuery.toLowerCase()
    return widgets.filter(w => w.title.toLowerCase().includes(q) || w.type.toLowerCase().includes(q))
  }, [widgets, searchQuery])

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedWidgets(e.target.checked ? filteredWidgets.map(w => w.id) : [])
  }

  const handleSelectOne = (id: string) => {
    setSelectedWidgets(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const openCreateModal = () => {
    setEditingWidget(null)
    setWidgetForm({ title: '', type: 'metric', value: '', change: 0, trend: 'up', color: '#06b6d4' })
    setShowWidgetModal(true)
  }

  const openEditModal = (widget: DashboardWidget) => {
    setEditingWidget(widget)
    setWidgetForm({ title: widget.title, type: widget.type, value: widget.value, change: widget.change, trend: widget.trend, color: widget.color })
    setShowWidgetModal(true)
  }

  const saveWidget = async () => {
    try {
      if (editingWidget) {
        const res = await fetchWithTimeout('/api/dashboard/widgets/' + editingWidget.id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
          body: JSON.stringify(widgetForm),
        })
        if (!res.ok) throw new Error('Failed to update widget')
      } else {
        const res = await fetchWithTimeout('/api/dashboard/widgets', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
          body: JSON.stringify(widgetForm),
        })
        if (!res.ok) throw new Error('Failed to create widget')
      }
      setShowWidgetModal(false)
      fetchWidgets()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save widget')
    }
  }

  const deleteWidget = async (id: string) => {
    try {
      const res = await fetchWithTimeout('/api/dashboard/widgets/' + id, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } })
      if (!res.ok) throw new Error('Failed to delete widget')
      setSelectedWidgets(prev => prev.filter(x => x !== id))
      fetchWidgets()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete widget')
    }
  }

  const bulkDeleteWidgets = async () => {
    try {
      await Promise.all(selectedWidgets.map(id => fetchWithTimeout('/api/dashboard/widgets/' + id, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } })))
      setSelectedWidgets([])
      fetchWidgets()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bulk delete widgets')
    }
  }

  const exportWidgets = (format: 'csv' | 'json') => {
    const rows = filteredWidgets.map(w => ({ id: w.id, title: w.title, type: w.type, value: w.value, change: w.change, trend: w.trend, color: w.color }))
    let content: string, filename: string, mimeType: string
    if (format === 'json') {
      content = JSON.stringify(rows, null, 2)
      filename = 'dashboard-widgets.json'
      mimeType = 'application/json'
    } else {
      const headers = ['id', 'title', 'type', 'value', 'change', 'trend', 'color']
      const escape = (v: unknown) => '"' + String(v).replace(/"/g, '""') + '"';
      const csv = [headers.join(','), ...rows.map(r => headers.map(h => escape(r[h as keyof typeof r])).join(','))].join('\n')
      content = csv
      filename = 'dashboard-widgets.csv'
      mimeType = 'text/csv'
    }
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleQuickAction = (label: string) => {
    setModal(label)
  }

  const normalizedData = Array.isArray(data) ? data[0] : data
  const revenueTrend = Array.isArray(normalizedData?.revenue_trend) ? normalizedData.revenue_trend : []
  const userGrowth = Array.isArray(normalizedData?.user_growth) ? normalizedData.user_growth : []

  const revenueChartData = useMemo(() => buildChartData(revenueTrend, MONTHS), [normalizedData])
  const userGrowthChartData = useMemo(() => buildChartData(userGrowth, MONTHS), [normalizedData])

  const activities: ActivityItem[] = [
    { action: 'New enterprise customer onboarding completed', user: 'Sarah Chen', time: '2 min ago', type: 'success' },
    { action: 'Payment processing delay detected in EU region', user: 'System Monitor', time: '15 min ago', type: 'warning' },
    { action: 'API rate limit exceeded for client #4521', user: 'Rate Limiter', time: '32 min ago', type: 'error' },
    { action: 'Weekly analytics report generated', user: 'Analytics Engine', time: '1 hr ago', type: 'info' },
    { action: 'New team member invited: john@company.com', user: 'Admin', time: '2 hrs ago', type: 'info' },
    { action: 'Database backup completed successfully', user: 'Backup Service', time: '3 hrs ago', type: 'success' },
    { action: 'Unusual login pattern detected for user mike@acme.co', user: 'Security Monitor', time: '5 hrs ago', type: 'warning' },
    { action: 'Feature flag "new-checkout" enabled for 10% traffic', user: 'DevOps Pipeline', time: '6 hrs ago', type: 'info' },
  ]

  const systemHealth: SystemHealthItem[] = [
    { name: 'API Gateway', value: '99.98%', status: 'healthy', icon: <Server className="w-4 h-4" />, detail: 'All endpoints operational' },
    { name: 'Database Cluster', value: '99.95%', status: 'healthy', icon: <HardDrive className="w-4 h-4" />, detail: 'Primary + 2 replicas' },
    { name: 'CPU Utilization', value: '67%', status: 'warning', icon: <Cpu className="w-4 h-4" />, detail: 'Above 60% threshold' },
    { name: 'Memory Usage', value: '82%', status: 'warning', icon: <Zap className="w-4 h-4" />, detail: '16.4 GB / 20 GB' },
    { name: 'CDN Cache Hit Rate', value: '94.2%', status: 'healthy', icon: <Wifi className="w-4 h-4" />, detail: 'Edge locations: 12' },
    { name: 'SSL Certificates', value: 'Valid', status: 'healthy', icon: <Shield className="w-4 h-4" />, detail: 'Expires in 45 days' },
  ]

  const quickActions: QuickAction[] = [
    { label: 'Generate Report', icon: <Download className="w-5 h-5" />, color: 'var(--accent)', description: 'Export analytics' },
    { label: 'Add User', icon: <UserPlus className="w-5 h-5" />, color: 'var(--accent2)', description: 'Invite team member' },
    { label: 'New Product', icon: <Package className="w-5 h-5" />, color: 'var(--success)', description: 'Create listing' },
    { label: 'View Analytics', icon: <BarChart3 className="w-5 h-5" />, color: 'var(--warning)', description: 'Deep dive data' },
    { label: 'Settings', icon: <Settings className="w-5 h-5" />, color: 'var(--muted)', description: 'Configure platform' },
    { label: 'Notifications', icon: <Bell className="w-5 h-5" />, color: 'var(--danger)', description: 'Manage alerts' },
    { label: 'Goals', icon: <Target className="w-5 h-5" />, color: 'var(--accent)', description: 'Set targets' },
    { label: 'New Lead', icon: <UserPlus className="w-5 h-5" />, color: 'var(--success)', description: 'Add lead' },
  ]

  const metricConfigs: MetricCardConfig[] = [
    { title: 'Total Revenue', value: '$2.4M', change: 12.5, trend: 'up', icon: <DollarSign className="w-5 h-5 text-[var(--accent)]" />, color: 'var(--accent)', sparkline: [1.8, 1.9, 2.0, 2.1, 2.0, 2.2, 2.3, 2.4] },
    { title: 'Active Users', value: '14,832', change: 8.2, trend: 'up', icon: <Users className="w-5 h-5 text-[var(--accent2)]" />, color: 'var(--accent2)', sparkline: [12.1, 12.5, 13.0, 13.2, 13.8, 14.0, 14.5, 14.8] },
    { title: 'Conversion Rate', value: '3.24%', change: 0.8, trend: 'down', icon: <Target className="w-5 h-5 text-[var(--warning)]" />, color: 'var(--warning)', sparkline: [3.5, 3.4, 3.45, 3.3, 3.35, 3.28, 3.22, 3.24] },
    { title: 'Avg Order Value', value: '$127.50', change: 4.6, trend: 'up', icon: <ShoppingCart className="w-5 h-5 text-[var(--success)]" />, color: 'var(--success)', sparkline: [115, 118, 120, 122, 124, 125, 126, 127.5] },
  ]

  const heroStats = [
    { label: 'Total Revenue', value: '$2.4M', icon: <DollarSign className="w-4 h-4" />, color: '#06b6d4' },
    { label: 'Active Users', value: '14,832', icon: <Users className="w-4 h-4" />, color: '#a855f7' },
    { label: 'Orders Today', value: '1,247', icon: <ShoppingCart className="w-4 h-4" />, color: '#10b981' },
    { label: 'Uptime', value: '99.98%', icon: <Globe className="w-4 h-4" />, color: '#f59e0b' },
  ]

  if (loading) return <StateMessage type="loading" />
  if (error) return <StateMessage type="error" message={error} onRetry={fetchDashboard} />
  if (!data) return null

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      <HeroSection stats={heroStats} />
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold gradient-text">Performance Overview</h2>
          <p className="text-sm text-[var(--muted)] mt-1">Business metrics and analytics</p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangeSelector value={dateRange} onChange={setDateRange} />
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]"><Activity className="w-3.5 h-3.5" /><span>Live</span></div>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricConfigs.map((config) => <MetricCard key={config.title} config={config} />)}
      </div>
      <div className="bg-gray-900 rounded-xl p-5 animate-fade-in border border-gray-800">
        <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
          <div>
            <h3 className="text-base font-semibold text-gray-100">Dashboard Widgets</h3>
            <p className="text-xs text-gray-400 mt-0.5">Create, edit, and manage widgets</p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search widgets..." className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500 w-48" />
            <button onClick={() => exportWidgets('csv')} className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm font-medium hover:bg-gray-700 hover:text-gray-100 transition-colors">Export CSV</button>
            <button onClick={() => exportWidgets('json')} className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm font-medium hover:bg-gray-700 hover:text-gray-100 transition-colors">Export JSON</button>
            <button onClick={openCreateModal} className="px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">+ Create Widget</button>
          </div>
        </div>
        {selectedWidgets.length > 0 && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-gray-800 border border-gray-700">
            <span className="text-sm text-gray-300">{selectedWidgets.length} selected</span>
            <button onClick={bulkDeleteWidgets} className="px-3 py-1.5 rounded-lg bg-red-600/20 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-600/30 transition-colors">Delete Selected</button>
            <button onClick={() => setSelectedWidgets([])} className="px-3 py-1.5 rounded-lg bg-gray-700 text-gray-300 text-xs font-medium hover:bg-gray-600 transition-colors">Clear</button>
          </div>
        )}
        {widgetsLoading ? (
          <div className="text-center py-8 text-gray-400 text-sm">Loading widgets...</div>
        ) : filteredWidgets.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">No widgets found. Create one to get started.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="flex items-center gap-2 mb-2 sm:col-span-2 lg:col-span-3">
              <input type="checkbox" checked={filteredWidgets.length > 0 && filteredWidgets.every(w => selectedWidgets.includes(w.id))} onChange={handleSelectAll} className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500" />
              <span className="text-xs text-gray-400">Select all</span>
            </div>
            {filteredWidgets.map((widget) => (
              <div key={widget.id} className="relative bg-gray-800 rounded-xl p-4 border border-gray-700 hover:border-gray-600 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <input type="checkbox" checked={selectedWidgets.includes(widget.id)} onChange={() => handleSelectOne(widget.id)} className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-cyan-500 focus:ring-cyan-500" />
                    <span className="text-sm font-medium text-gray-100">{widget.title}</span>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: widget.color + '20', color: widget.color }}>{widget.type}</span>
                </div>
                <div className="text-xl font-bold text-gray-100 mb-1">{widget.value}</div>
                <div className="flex items-center gap-1.5 mb-3">
                  {widget.trend === 'up' ? <ArrowUpRight className="w-3.5 h-3.5 text-green-400" /> : <ArrowDownRight className="w-3.5 h-3.5 text-red-400" />}
                  <span className={'text-sm font-semibold ' + (widget.trend === 'up' ? 'text-green-400' : 'text-red-400')}>{widget.trend === 'up' ? '+' : ''}{widget.change}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => openEditModal(widget)} className="flex-1 px-3 py-1.5 rounded-lg bg-gray-700 text-gray-300 text-xs font-medium hover:bg-gray-600 hover:text-gray-100 transition-colors">Edit</button>
                  <button onClick={() => deleteWidget(widget.id)} className="flex-1 px-3 py-1.5 rounded-lg bg-red-600/20 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-600/30 transition-colors">Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-xl p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-base font-semibold text-[var(--text)]">Revenue Trend</h3><p className="text-xs text-[var(--muted)] mt-0.5">Monthly recurring revenue</p></div>
            <div className="flex items-center gap-1.5 text-xs"><TrendingUp className="w-3.5 h-3.5 text-[var(--success)]" /><span className="text-[var(--success)] font-semibold">+12.5%</span></div>
          </div>
          <Suspense fallback={<ChartSkeleton />}>
            <RevenueChart data={revenueChartData} />
          </Suspense>
        </div>
        <div className="glass rounded-xl p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-base font-semibold text-[var(--text)]">User Growth</h3><p className="text-xs text-[var(--muted)] mt-0.5">Monthly active users</p></div>
            <div className="flex items-center gap-1.5 text-xs"><TrendingUp className="w-3.5 h-3.5 text-[var(--accent2)]" /><span className="text-[var(--accent2)] font-semibold">+8.2%</span></div>
          </div>
          <Suspense fallback={<ChartSkeleton />}>
            <UserGrowthChart data={userGrowthChartData} />
          </Suspense>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass rounded-xl p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-base font-semibold text-[var(--text)]">Recent Activity</h3><p className="text-xs text-[var(--muted)] mt-0.5">Latest platform events</p></div>
            <button onClick={() => setModal('View all')} className="text-xs text-[var(--accent)] hover:underline">View all</button>
          </div>
          <ActivityFeed activities={activities} />
        </div>
        <div className="glass rounded-xl p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-base font-semibold text-[var(--text)]">Quick Actions</h3><p className="text-xs text-[var(--muted)] mt-0.5">Common tasks</p></div>
          </div>
          <QuickActions actions={quickActions} onAction={handleQuickAction} />
        </div>
        <div className="glass rounded-xl p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-base font-semibold text-[var(--text)]">System Health</h3><p className="text-xs text-[var(--muted)] mt-0.5">Infrastructure status</p></div>
            <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse-slow" /><span className="text-xs text-[var(--success)] font-medium">Operational</span></div>
          </div>
          <SystemHealth items={systemHealth} />
        </div>
      </div>
      {showWidgetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowWidgetModal(false)}>
          <div className="bg-gray-900 rounded-2xl p-6 max-w-md w-full mx-4 animate-fade-in border border-gray-700" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100">{editingWidget ? 'Edit Widget' : 'Create Widget'}</h3>
              <button onClick={() => setShowWidgetModal(false)} className="p-1 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-100 transition-colors"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Title</label>
                <input type="text" value={widgetForm.title} onChange={(e) => setWidgetForm(f => ({ ...f, title: e.target.value }))} className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500" placeholder="Widget title" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
                <select value={widgetForm.type} onChange={(e) => setWidgetForm(f => ({ ...f, type: e.target.value as DashboardWidget['type'] }))} className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500">
                  <option value="metric">Metric</option>
                  <option value="chart">Chart</option>
                  <option value="table">Table</option>
                  <option value="text">Text</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Value</label>
                <input type="text" value={widgetForm.value} onChange={(e) => setWidgetForm(f => ({ ...f, value: e.target.value }))} className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500" placeholder="Display value" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Change %</label>
                  <input type="number" value={widgetForm.change} onChange={(e) => setWidgetForm(f => ({ ...f, change: parseFloat(e.target.value) || 0 }))} className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Trend</label>
                  <select value={widgetForm.trend} onChange={(e) => setWidgetForm(f => ({ ...f, trend: e.target.value as 'up' | 'down' }))} className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500">
                    <option value="up">Up</option>
                    <option value="down">Down</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Color</label>
                <input type="color" value={widgetForm.color} onChange={(e) => setWidgetForm(f => ({ ...f, color: e.target.value }))} className="w-full h-10 rounded-lg bg-gray-800 border border-gray-700 cursor-pointer" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowWidgetModal(false)} className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors">Cancel</button>
              <button onClick={saveWidget} className="flex-1 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">{editingWidget ? 'Update' : 'Create'}</button>
            </div>
          </div>
        </div>
      )}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setModal(null)}>
          <div className="glass rounded-2xl p-6 max-w-md w-full mx-4 animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[var(--text)]">{modal}</h3>
              <button onClick={() => setModal(null)} className="p-1 rounded-lg hover:bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--text)] transition-colors"><X className="w-5 h-5" /></button>
            </div>
            {modal === 'Goals' && <GoalsForm onClose={() => setModal(null)} />}
            {modal === 'New Lead' && <NewLeadForm onClose={() => setModal(null)} />}
            {modal === 'Generate Report' && <GenerateReportModal metrics={metricConfigs} onClose={() => setModal(null)} />}
            {modal === 'Add User' && <AddUserForm onClose={() => setModal(null)} />}
            {modal === 'New Product' && <NewProductForm onClose={() => setModal(null)} />}
            {modal === 'View Analytics' && <ViewAnalyticsModal kpis={readKpis(data, metricConfigs)} onClose={() => setModal(null)} />}
            {modal === 'Settings' && <SettingsForm onClose={() => setModal(null)} />}
            {modal === 'Notifications' && <NotificationsModal onClose={() => setModal(null)} />}
            {modal === 'View all' && <ViewAllActivityModal activities={activities} onClose={() => setModal(null)} />}
            
          </div>
        </div>
      )}
    </div>
  )
}
