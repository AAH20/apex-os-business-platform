import { useEffect, useState, useMemo, type ReactNode } from 'react'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { TrendingUp, DollarSign, Users, Target, ShoppingCart, Activity, ArrowUpRight, ArrowDownRight, UserPlus, Package, BarChart3, Settings, Bell, Download, Server, Cpu, HardDrive, Wifi, Shield, Zap, CheckCircle2, XCircle, AlertTriangle, Rocket, Globe, X } from 'lucide-react'
import { api } from '../api/client'
import type { DashboardData } from '../api/client'

interface MetricCardConfig { title: string; value: string; change: number; trend: 'up' | 'down'; icon: ReactNode; color: string; sparkline: number[] }
interface ChartDataPoint { name: string; value: number }
interface ActivityItem { action: string; user: string; time: string; type: 'success' | 'warning' | 'error' | 'info' }
interface SystemHealthItem { name: string; value: string; status: 'healthy' | 'warning' | 'critical'; icon: ReactNode; detail: string }
interface QuickAction { label: string; icon: ReactNode; color: string; description: string }
interface DashboardWidget { id: string; title: string; type: 'metric' | 'chart' | 'table' | 'text'; value: string; change: number; trend: 'up' | 'down'; color: string; sparkline: number[] }

const fmtCurrency = (v: number) => v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `$${(v / 1_000).toFixed(1)}K` : `$${v.toFixed(2)}`
const fmtNumber = (v: number) => v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `${(v / 1_000).toFixed(1)}K` : v.toLocaleString()
const buildChartData = (data: number[], labels: string[]): ChartDataPoint[] => data.map((value, i) => ({ name: labels[i] ?? `P${i + 1}`, value }))
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const chartData = data.map((v, i) => ({ i, v }))
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} activeDot={{ r: 3, fill: color, strokeWidth: 0 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function MetricCard({ config }: { config: MetricCardConfig }) {
  const isUp = config.trend === 'up'
  const changeColor = isUp ? 'var(--success)' : 'var(--danger)'
  return (
    <div className="glass card-hover rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-[var(--muted)]">{config.title}</span>
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${config.color}15` }}>{config.icon}</div>
      </div>
      <div className="text-2xl font-bold text-[var(--text)] mb-1">{config.value}</div>
      <div className="flex items-center gap-1.5 mb-3">
        {isUp ? <ArrowUpRight className="w-4 h-4" style={{ color: changeColor }} /> : <ArrowDownRight className="w-4 h-4" style={{ color: changeColor }} />}
        <span className="text-sm font-semibold" style={{ color: changeColor }}>{isUp ? '+' : ''}{config.change}%</span>
        <span className="text-xs text-[var(--muted)] ml-1">vs last month</span>
      </div>
      <Sparkline data={config.sparkline} color={config.color} />
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
            <div className="p-2 rounded-full mt-0.5 shrink-0" style={{ backgroundColor: `${cfg.color}15`, color: cfg.color }}>{cfg.icon}</div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-[var(--text)] font-medium truncate">{item.action}</p>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ backgroundColor: `hsl(${idx * 60}, 70%, 50%)` }}>{item.user.charAt(0)}</div>
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
            <div className="p-2 rounded-lg shrink-0" style={{ backgroundColor: `${cfg.color}15`, color: cfg.color }}>{item.icon}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[var(--text)]">{item.name}</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ backgroundColor: `${cfg.color}20`, color: cfg.color }}>{cfg.label}</span>
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
          <div className="p-2 rounded-lg inline-block mb-2" style={{ backgroundColor: `${action.color}15`, color: action.color }}>{action.icon}</div>
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
            <div key={i} className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${s.color}30`, color: 'white' }}>{s.icon}</div>
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
        <button key={range} onClick={() => onChange(range)} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${value === range ? 'bg-[var(--accent)] text-white' : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)]'}`}>{range}</button>
      ))}
    </div>
  )
}

function StateMessage({ type, message, onRetry }: { type: string; message?: string; onRetry?: () => void }) {
  const isError = type === 'error'
  return (
    <div className={`p-4 rounded-lg border ${isError ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-[var(--surface)] border-[var(--border)] text-[var(--muted)]'}`}>
      {isError ? message : 'Loading...'}
      {onRetry && <button onClick={onRetry} className="ml-2 underline">Retry</button>}
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
      const res = await api.getDashboard()
      const data = Array.isArray(res) ? res[0] : res
      setWidgets(Array.isArray(data) ? data : [data])
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
        const res = await fetch(`/api/dashboard/widgets/${editingWidget.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
          body: JSON.stringify(widgetForm),
        })
        if (!res.ok) throw new Error('Failed to update widget')
      } else {
        const res = await fetch('/api/dashboard/widgets', {
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
      const res = await fetch(`/api/dashboard/widgets/${id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } })
      if (!res.ok) throw new Error('Failed to delete widget')
      setSelectedWidgets(prev => prev.filter(x => x !== id))
      fetchWidgets()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete widget')
    }
  }

  const bulkDeleteWidgets = async () => {
    try {
      await Promise.all(selectedWidgets.map(id => fetch(`/api/dashboard/widgets/${id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } })))
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
      const escape = (v: unknown) => `"${String(v).replace(/"/g, '""')}"`
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
                  <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: `${widget.color}20`, color: widget.color }}>{widget.type}</span>
                </div>
                <div className="text-xl font-bold text-gray-100 mb-1">{widget.value}</div>
                <div className="flex items-center gap-1.5 mb-3">
                  {widget.trend === 'up' ? <ArrowUpRight className="w-3.5 h-3.5 text-green-400" /> : <ArrowDownRight className="w-3.5 h-3.5 text-red-400" />}
                  <span className={`text-sm font-semibold ${widget.trend === 'up' ? 'text-green-400' : 'text-red-400'}`}>{widget.trend === 'up' ? '+' : ''}{widget.change}%</span>
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
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={revenueChartData}>
              <defs><linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4} /><stop offset="100%" stopColor="#06b6d4" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => fmtCurrency(v)} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} labelStyle={{ color: 'var(--muted)' }} formatter={(v: number) => [fmtCurrency(v), 'Revenue']} />
              <Area type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2.5} fill="url(#revGrad)" dot={{ fill: '#06b6d4', strokeWidth: 0, r: 4 }} activeDot={{ r: 6, fill: '#06b6d4', stroke: '#07090e', strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="glass rounded-xl p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-base font-semibold text-[var(--text)]">User Growth</h3><p className="text-xs text-[var(--muted)] mt-0.5">Monthly active users</p></div>
            <div className="flex items-center gap-1.5 text-xs"><TrendingUp className="w-3.5 h-3.5 text-[var(--accent2)]" /><span className="text-[var(--accent2)] font-semibold">+8.2%</span></div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={userGrowthChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => fmtNumber(v)} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} labelStyle={{ color: 'var(--muted)' }} formatter={(v: number) => [fmtNumber(v), 'Users']} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={32}>
                {userGrowthChartData.map((_, i) => <Cell key={i} fill={i === userGrowthChartData.length - 1 ? '#a855f7' : `${'#a855f7'}${Math.round(40 + (i / userGrowthChartData.length) * 60).toString(16).padStart(2, '0')}`} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
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
            <p className="text-sm text-[var(--muted)]">This action is not yet implemented. It will be available in a future update.</p>
            <button onClick={() => setModal(null)} className="mt-4 w-full px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
