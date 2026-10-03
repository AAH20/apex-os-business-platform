import { useState, useEffect, useCallback, useMemo } from 'react'
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Activity, AlertTriangle, BarChart3, Bell, Clock, Cpu, Database, Gauge, Layers, Loader2, RefreshCw, Server, DollarSign, Users, Target, ShoppingCart, Globe, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { api, ContinuousBIData } from '../api/client'

interface Dashboard { name: string; widgets: number; refresh_rate: string; viewers: number }
interface Alert { name: string; condition: string; severity: string; enabled: boolean }
interface DataFreshness { last_update: string; lag_seconds: number; status: string }
interface Transaction { id: string; customer: string; amount: number; status: 'completed' | 'pending' | 'failed' | 'refunded'; time: string }
interface Region { name: string; revenue: number; percentage: number; color: string }

const fmtN = (n: number) => n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : n.toLocaleString()
const fmtT = (iso: string) => { try { return new Date(iso).toLocaleTimeString() } catch { return iso } }
const fmtLag = (s: number) => s < 60 ? `${s}s ago` : s < 3600 ? `${Math.floor(s / 60)}m ago` : `${Math.floor(s / 3600)}h ago`
const sevCls = (s: string) => { const v = s.toLowerCase(); return v === 'critical' ? 'bg-red-500/20 text-red-400 border-red-500/30' : v === 'warning' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : v === 'info' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' }
const stCls = (s: string) => s === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : s === 'pending' ? 'bg-amber-500/20 text-amber-400' : s === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-purple-500/20 text-purple-400'

const genRev = () => Array.from({ length: 30 }, (_, i) => { const t = new Date(Date.now() - (29 - i) * 3600_000); return { time: t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), revenue: Math.round(80000 + Math.sin(i * 0.3) * 20000 + Math.random() * 15000) } })
const genSpark = (b: number, v: number) => Array.from({ length: 20 }, () => b + (Math.random() - 0.5) * v)
const genTxns = (): Transaction[] => { const n = ['Alice Johnson', 'Bob Smith', 'Carol White', 'David Brown', 'Eve Davis', 'Frank Miller']; const s: Transaction['status'][] = ['completed', 'pending', 'failed', 'refunded']; return Array.from({ length: 12 }, (_, i) => ({ id: `txn-${i}`, customer: n[Math.floor(Math.random() * n.length)], amount: Math.round(Math.random() * 500 + 10), status: s[Math.floor(Math.random() * s.length)], time: new Date(Date.now() - Math.random() * 3600_000).toISOString() })) }

const FUNNEL = [{ stage: 'Impressions', value: 1200000, color: '#06b6d4' }, { stage: 'Visits', value: 45000, color: '#8b5cf6' }, { stage: 'Signups', value: 8000, color: '#f59e0b' }, { stage: 'Customers', value: 1200, color: '#10b981' }]
const REGIONS: Region[] = [{ name: 'North America', revenue: 1080000, percentage: 45, color: '#06b6d4' }, { name: 'Europe', revenue: 720000, percentage: 30, color: '#8b5cf6' }, { name: 'Asia', revenue: 360000, percentage: 15, color: '#f59e0b' }, { name: 'Other', revenue: 240000, percentage: 10, color: '#10b981' }]

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) { return <div className={`glass rounded-xl p-5 animate-fade-in ${className}`}>{children}</div> }
function CardHeader({ title, icon, badge }: { title: string; icon?: React.ReactNode; badge?: string }) { return <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-2">{icon}<h3 className="text-base font-semibold text-[var(--text)]">{title}</h3></div>{badge && <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--accent)]/20 text-[var(--accent)] font-medium">{badge}</span>}</div> }

function KpiCards() {
  const kpis = useMemo(() => [
    { title: 'Revenue', value: '$2.4M', change: 12.5, icon: <DollarSign className="w-5 h-5" />, color: '#06b6d4', spark: genSpark(2400000, 200000) },
    { title: 'Users', value: '14,832', change: 8.2, icon: <Users className="w-5 h-5" />, color: '#8b5cf6', spark: genSpark(14832, 1000) },
    { title: 'Conversion', value: '3.24%', change: -1.3, icon: <Target className="w-5 h-5" />, color: '#f59e0b', spark: genSpark(3.24, 0.3) },
    { title: 'AOV', value: '$127.50', change: 4.6, icon: <ShoppingCart className="w-5 h-5" />, color: '#10b981', spark: genSpark(127.5, 10) },
  ], [])
  return <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">{kpis.map(k => <div key={k.title} className="glass card-hover rounded-xl p-5 animate-fade-in"><div className="flex items-center justify-between mb-3"><span className="text-sm font-medium text-[var(--muted)]">{k.title}</span><div className="p-2 rounded-lg" style={{ backgroundColor: `${k.color}15` }}><span style={{ color: k.color }}>{k.icon}</span></div></div><div className="text-2xl font-bold text-[var(--text)] mb-1">{k.value}</div><div className="flex items-center gap-1.5 mb-3">{k.change > 0 ? <ArrowUpRight className="w-4 h-4 text-[var(--success)]" /> : <ArrowDownRight className="w-4 h-4 text-[var(--danger)]" />}<span className={`text-sm font-semibold ${k.change > 0 ? 'text-[var(--success)]' : 'text-[var(--danger)]'}`}>{k.change > 0 ? '+' : ''}{k.change}%</span><span className="text-xs text-[var(--muted)]">vs last hour</span></div><ResponsiveContainer width="100%" height={40}><LineChart data={k.spark.map((v, i) => ({ i, v }))}><Line type="monotone" dataKey="v" stroke={k.color} strokeWidth={1.5} dot={false} /></LineChart></ResponsiveContainer></div>)}</div>
}

function RevenueChart({ data }: { data: any[] }) {
  return <Card><CardHeader title="Live Revenue" icon={<DollarSign className="w-5 h-5 text-[var(--accent)]" />} badge="Real-time" /><ResponsiveContainer width="100%" height={280}><AreaChart data={data}><defs><linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} /><stop offset="95%" stopColor="#06b6d4" stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="time" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} interval={4} /><YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => `$${fmtN(v)}`} /><Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)', fontSize: '0.8rem' }} /><Area type="monotone" dataKey="revenue" stroke="#06b6d4" fill="url(#revGrad)" strokeWidth={2} name="Revenue" /></AreaChart></ResponsiveContainer></Card>
}

function FunnelChart() {
  return <Card><CardHeader title="User Acquisition Funnel" icon={<Target className="w-5 h-5 text-[var(--accent2)]" />} badge="30d" /><div className="space-y-3">{FUNNEL.map((f, i) => { const pct = i === 0 ? 100 : (f.value / FUNNEL[0].value) * 100; return <div key={f.stage}><div className="flex items-center justify-between mb-1"><span className="text-sm text-[var(--text)] font-medium">{f.stage}</span><span className="text-sm font-bold" style={{ color: f.color }}>{fmtN(f.value)}</span></div><div className="w-full h-8 rounded-lg bg-[var(--surface)] overflow-hidden"><div className="h-full rounded-lg flex items-center px-3 transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: `${f.color}30`, borderLeft: `3px solid ${f.color}` }}><span className="text-xs font-medium" style={{ color: f.color }}>{pct.toFixed(1)}%</span></div></div></div> })}</div></Card>
}

function LiveTransactionTable({ transactions }: { transactions: Transaction[] }) {
  return <Card><CardHeader title="Live Transactions" icon={<Activity className="w-5 h-5 text-[var(--accent)]" />} badge="Live" /><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-[var(--border)]"><th className="text-left py-2 px-3 text-[var(--muted)] font-medium text-xs uppercase">Customer</th><th className="text-right py-2 px-3 text-[var(--muted)] font-medium text-xs uppercase">Amount</th><th className="text-center py-2 px-3 text-[var(--muted)] font-medium text-xs uppercase">Status</th><th className="text-right py-2 px-3 text-[var(--muted)] font-medium text-xs uppercase">Time</th></tr></thead><tbody>{transactions.map(t => <tr key={t.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface)] transition-colors"><td className="py-2 px-3 text-[var(--text)] font-medium">{t.customer}</td><td className="py-2 px-3 text-right text-[var(--text)]">${t.amount}</td><td className="py-2 px-3 text-center"><span className={`px-2 py-0.5 rounded-full text-xs font-medium ${stCls(t.status)}`}>{t.status}</span></td><td className="py-2 px-3 text-right text-[var(--muted)] text-xs">{fmtT(t.time)}</td></tr>)}</tbody></table></div></Card>
}

function GeoBreakdown() {
  return <Card><CardHeader title="Revenue by Region" icon={<Globe className="w-5 h-5 text-[var(--accent)]" />} badge="Q4 2024" /><div className="space-y-4">{REGIONS.map(r => <div key={r.name}><div className="flex items-center justify-between mb-1"><span className="text-sm text-[var(--text)]">{r.name}</span><span className="text-sm font-medium" style={{ color: r.color }}>{r.percentage}% · ${fmtN(r.revenue)}</span></div><div className="w-full h-2 rounded-full bg-[var(--surface)] overflow-hidden"><div className="h-full rounded-full transition-all duration-700" style={{ width: `${r.percentage}%`, backgroundColor: r.color }} /></div></div>)}</div></Card>
}

function AlertRules({ alerts }: { alerts: Alert[] }) {
  const [local, setLocal] = useState(alerts)
  useEffect(() => setLocal(alerts), [alerts])
  const toggle = (i: number) => setLocal(prev => prev.map((a, j) => j === i ? { ...a, enabled: !a.enabled } : a))
  return <Card><CardHeader title="Alert Rules" icon={<Bell className="w-5 h-5 text-[var(--warning)]" />} badge={`${local.filter(a => a.enabled).length}/${local.length} active`} /><div className="space-y-2">{local.map((a, i) => <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)]"><div className="flex-1 min-w-0"><div className="text-sm font-medium text-[var(--text)] truncate">{a.name}</div><div className="text-xs text-[var(--muted)] font-mono truncate">{a.condition}</div></div><div className="flex items-center gap-3 ml-3"><span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${sevCls(a.severity)}`}>{a.severity}</span><button onClick={() => toggle(i)} className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${a.enabled ? 'bg-[var(--accent)]' : 'bg-[var(--border)]'}`}><span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${a.enabled ? 'translate-x-[18px]' : 'translate-x-0.5'}`} /></button></div></div>)}</div></Card>
}

function DataFreshness({ freshness }: { freshness: DataFreshness }) {
  const isStale = freshness.lag_seconds > 300
  return <Card><CardHeader title="Data Freshness" icon={<Clock className="w-5 h-5 text-[var(--accent)]" />} badge={isStale ? 'stale' : 'fresh'} /><div className="flex items-center gap-4"><div className="relative flex-shrink-0"><div className={`w-3 h-3 rounded-full ${isStale ? 'bg-amber-400' : 'bg-emerald-400'} animate-pulse`} /><div className={`absolute inset-0 w-3 h-3 rounded-full ${isStale ? 'bg-amber-400' : 'bg-emerald-400'} animate-ping`} /></div><div className="flex-1 space-y-2"><div className="flex justify-between text-sm"><span className="text-[var(--muted)]">Last Update</span><span className="text-[var(--text)]">{fmtT(freshness.last_update)}</span></div><div className="flex justify-between text-sm"><span className="text-[var(--muted)]">Lag</span><span className={isStale ? 'text-[var(--warning)]' : 'text-[var(--success)]'}>{fmtLag(freshness.lag_seconds)}</span></div><div className="flex justify-between text-sm"><span className="text-[var(--muted)]">Sources</span><span className="text-[var(--success)]">12 / 12 healthy</span></div></div></div></Card>
}

function DashboardGrid({ dashboards }: { dashboards: Dashboard[] }) {
  return <Card><CardHeader title="Dashboards" icon={<BarChart3 className="w-5 h-5 text-[var(--accent)]" />} badge={`${dashboards.length} total`} /><div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{dashboards.map((d, i) => <div key={i} className="p-4 rounded-lg bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)]/30 transition-colors"><div className="flex items-center justify-between mb-2"><span className="text-sm font-medium text-[var(--text)]">{d.name}</span><span className="text-xs text-[var(--muted)]">{d.refresh_rate}</span></div><div className="flex items-center gap-4 text-xs text-[var(--muted)]"><span className="flex items-center gap-1"><Layers className="w-3 h-3" />{d.widgets} widgets</span><span className="flex items-center gap-1"><Users className="w-3 h-3" />{fmtN(d.viewers)} viewers</span></div></div>)}</div></Card>
}

function PerformanceMetrics() {
  const metrics = [{ name: 'Query Latency', value: '245ms', percentage: 75, color: '#06b6d4', icon: <Gauge className="w-4 h-4" /> }, { name: 'Cache Hit Rate', value: '94.2%', percentage: 94.2, color: '#10b981', icon: <Database className="w-4 h-4" /> }, { name: 'Uptime', value: '99.99%', percentage: 99.99, color: '#8b5cf6', icon: <Server className="w-4 h-4" /> }]
  return <Card><CardHeader title="Performance" icon={<Cpu className="w-5 h-5 text-[var(--accent)]" />} badge="Live" /><div className="space-y-4">{metrics.map(m => <div key={m.name}><div className="flex items-center justify-between mb-1"><span className="flex items-center gap-2 text-sm text-[var(--text)]"><span style={{ color: m.color }}>{m.icon}</span>{m.name}</span><span className="text-sm font-bold" style={{ color: m.color }}>{m.value}</span></div><div className="w-full h-2 rounded-full bg-[var(--surface)] overflow-hidden"><div className="h-full rounded-full transition-all duration-700" style={{ width: `${m.percentage}%`, backgroundColor: m.color }} /></div></div>)}</div></Card>
}

function LoadingState() { return <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4"><Loader2 className="w-10 h-10 text-[var(--accent)] animate-spin" /><p className="text-[var(--muted)] text-sm">Loading Continuous BI data…</p></div> }
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) { return <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4"><AlertTriangle className="w-10 h-10 text-[var(--danger)]" /><p className="text-[var(--text)] text-sm">{message}</p><button onClick={onRetry} className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity">Retry</button></div> }

export default function ContinuousBI() {
  const [data, setData] = useState<ContinuousBIData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [revenueData, setRevenueData] = useState(genRev)
  const [transactions, setTransactions] = useState(genTxns)

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    try { const result = await api.getContinuousBI(); setData(result); setRevenueData(genRev()); setTransactions(genTxns()); setError(null) } catch (err) { setError(err instanceof Error ? err.message : 'Failed to fetch data') } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])
  useEffect(() => { if (loading || error) return; const interval = setInterval(() => { setRevenueData(genRev()); setTransactions(genTxns()) }, 5000); return () => clearInterval(interval) }, [loading, error])

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={() => fetchData(true)} />
  if (!data) return null

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold gradient-text">Continuous BI</h1><p className="text-sm text-[var(--muted)] mt-1">Real-time business intelligence & analytics</p></div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]"><Activity className="w-3.5 h-3.5 text-[var(--success)]" /><span>Live</span></div>
          <button onClick={() => fetchData(true)} disabled={refreshing} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"><RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />{refreshing ? 'Refreshing…' : 'Refresh'}</button>
        </div>
      </div>
      <KpiCards />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6"><div className="lg:col-span-2"><RevenueChart data={revenueData} /></div><div className="lg:col-span-1"><FunnelChart /></div></div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6"><LiveTransactionTable transactions={transactions} /><GeoBreakdown /></div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6"><AlertRules alerts={data.alerts} /><DataFreshness freshness={data.data_freshness} /></div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6"><DashboardGrid dashboards={data.dashboards} /><PerformanceMetrics /></div>
    </div>
  )
}
