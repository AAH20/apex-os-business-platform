import { useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Activity, AlertCircle, Bot, CheckCircle2, Clock, Cpu, FileJson, FileSpreadsheet, Loader2, MessageSquare, Network, Pencil, Plus, Radio, RefreshCw, Search, Server, Shield, Signal, Trash2, TrendingUp, X } from 'lucide-react'
import { api } from '../api/client'
import type { Agent, AgentReachData } from '../api/client'

// ─── Types ───────────────────────────────────────────────────────────────────
interface Channel { id: string; name: string; type: string; throughput: number }
interface Route { source: string; target: string; messages: number; success_rate: number }
interface LogEntry { id: string; timestamp: string; agent: string; channel: string; message: string; status: 'success' | 'error' | 'pending'; latency_ms: number }
interface LBNode { id: string; name: string; status: 'healthy' | 'degraded' | 'down'; connections: number; cpu_percent: number; memory_percent: number; region: string }

// ─── Helpers ─────────────────────────────────────────────────────────────────
const COLORS = ['#06b6d4', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#ec4899', '#14b8a6']
const avatarColor = (id: string) => { let h = 0; for (let i = 0; i < id.length; i++) h = id.charCodeAt(i) + ((h << 5) - h); return COLORS[Math.abs(h) % COLORS.length] }
const initials = (n: string) => n.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
const fmt = (n: number) => n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : n.toLocaleString()
const uid = () => Math.random().toString(36).slice(2, 10)

function genLogs(agents: Agent[], channels: Channel[]): LogEntry[] {
  const msgs = ['Process inquiry', 'Route ticket', 'Handle refund', 'Escalate', 'Query KB', 'Generate response', 'Validate intent', 'Update CRM', 'Send notification', 'Analyze sentiment', 'Extract entities', 'Summarize', 'Classify priority', 'Trigger workflow', 'Sync backend']
  const sts: LogEntry['status'][] = ['success', 'success', 'success', 'success', 'error', 'pending']
  const now = Date.now()
  return Array.from({ length: 25 }, (_, i) => ({
    id: uid(), timestamp: new Date(now - i * 3000 - Math.random() * 2000).toISOString(),
    agent: agents[Math.floor(Math.random() * agents.length)]?.name ?? 'Unknown',
    channel: channels[Math.floor(Math.random() * channels.length)]?.name ?? 'Unknown',
    message: msgs[Math.floor(Math.random() * msgs.length)],
    status: sts[Math.floor(Math.random() * sts.length)],
    latency_ms: Math.floor(Math.random() * 200) + 10,
  })).sort((a, b) => +new Date(b.timestamp) - +new Date(a.timestamp))
}

function genLB(): LBNode[] {
  const regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
  const sts: LBNode['status'][] = ['healthy', 'healthy', 'healthy', 'degraded']
  return regions.map((r, i) => ({ id: `lb-${i}`, name: `LB-${r.split('-')[0].toUpperCase()}-${i + 1}`, status: sts[i], connections: Math.floor(Math.random() * 5000) + 1000, cpu_percent: Math.floor(Math.random() * 60) + 20, memory_percent: Math.floor(Math.random() * 50) + 30, region: r }))
}

// ─── Network Graph (SVG) ─────────────────────────────────────────────────────
function NetworkGraph({ agents, routes }: { agents: Agent[]; routes: Route[] }) {
  const W = 600, H = 320, cx = W / 2, cy = H / 2
  const nodes = agents.slice(0, 8).map((a, i) => {
    const angle = (2 * Math.PI * i) / Math.min(agents.length, 8)
    return { ...a, x: cx + 180 * Math.cos(angle), y: cy + 110 * Math.sin(angle) }
  })
  const edges = routes.slice(0, 12).map(r => {
    const s = nodes.find(n => n.name === r.source), t = nodes.find(n => n.name === r.target)
    return s && t ? { sx: s.x, sy: s.y, tx: t.x, ty: t.y, w: r.messages } : null
  }).filter(Boolean) as { sx: number; sy: number; tx: number; ty: number; w: number }[]
  return (
    <div className="glass rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div><h3 className="text-base font-semibold text-[var(--text)]">Agent Network</h3><p className="text-xs text-[var(--muted)] mt-0.5">Connection topology & message flow</p></div>
        <div className="p-2 rounded-lg bg-[var(--accent2)]/10"><Network className="w-4 h-4 text-[var(--accent2)]" /></div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        <defs><filter id="glow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        {edges.map((e, i) => {
          const mx = (e.sx + e.tx) / 2, my = (e.sy + e.ty) / 2 - 20
          return <g key={i}>
            <path d={`M${e.sx},${e.sy} Q${mx},${my} ${e.tx},${e.ty}`} fill="none" stroke="var(--accent)" strokeWidth={Math.min(3, 1 + e.w / 500)} opacity={0.5} filter="url(#glow)" />
            <circle cx={e.tx} cy={e.ty} r={3} fill="var(--accent2)" opacity={0.8}><animate attributeName="r" values="2;4;2" dur="2s" repeatCount="indefinite" /></circle>
          </g>
        })}
        {nodes.map(n => (
          <g key={n.id}>
            <circle cx={n.x} cy={n.y} r={22} fill={avatarColor(n.id)} opacity={0.15}><animate attributeName="r" values="22;26;22" dur="3s" repeatCount="indefinite" /></circle>
            <circle cx={n.x} cy={n.y} r={16} fill={avatarColor(n.id)} opacity={0.9} filter="url(#glow)" />
            <text x={n.x} y={n.y + 4} textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">{initials(n.name)}</text>
            <text x={n.x} y={n.y + 34} textAnchor="middle" fill="var(--muted)" fontSize="9">{n.name.slice(0, 10)}</text>
          </g>
        ))}
      </svg>
    </div>
  )
}

// ─── Agent Card ──────────────────────────────────────────────────────────────
function AgentCard({ agent, rank }: { agent: Agent; rank: number }) {
  const c = avatarColor(agent.id), active = agent.status === 'active'
  const cpu = Math.floor(Math.random() * 60) + 20
  const mem = Math.floor(Math.random() * 50) + 30
  return (
    <div className="glass card-hover rounded-xl p-4 animate-fade-in">
      <div className="flex items-center gap-3 mb-3">
        <div className="relative">
          <div className="w-11 h-11 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: c, boxShadow: `0 0 12px ${c}40` }}>{initials(agent.name)}</div>
          <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[var(--surface)] ${active ? 'bg-emerald-400 animate-pulse-slow' : agent.status === 'idle' ? 'bg-amber-400' : 'bg-red-400'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2"><h4 className="text-sm font-semibold text-[var(--text)] truncate">{agent.name}</h4>{rank < 3 && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 font-medium">#{rank + 1}</span>}</div>
          <span className={`inline-flex items-center gap-1 mt-0.5 text-[10px] px-1.5 py-0.5 rounded-full ${active ? 'bg-emerald-500/10 text-emerald-400' : agent.status === 'idle' ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-emerald-400 animate-pulse-slow' : agent.status === 'idle' ? 'bg-amber-400' : 'bg-red-400'}`} />{agent.status}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-[var(--surface)]/50 rounded-lg p-2"><p className="text-[10px] text-[var(--muted)] flex items-center gap-1"><MessageSquare className="w-3 h-3 text-[var(--accent)]" />Messages</p><p className="text-sm font-bold text-[var(--text)]">{fmt(agent.messages_processed)}</p></div>
        <div className="bg-[var(--surface)]/50 rounded-lg p-2"><p className="text-[10px] text-[var(--muted)] flex items-center gap-1"><Clock className="w-3 h-3 text-[var(--warning)]" />Latency</p><p className="text-sm font-bold text-[var(--text)]">{agent.latency_ms}ms</p></div>
      </div>
      <div className="space-y-1.5">
        {([{ l: 'CPU', v: cpu, icon: <Cpu className="w-3 h-3" /> }, { l: 'MEM', v: mem, icon: <Server className="w-3 h-3" /> }] as { l: string; v: number; icon: ReactNode }[]).map(({ l, v, icon }) => (
          <div key={l} className="flex items-center gap-2">
            <span className="text-[10px] text-[var(--muted)] w-7 flex items-center gap-1">{icon}{l}</span>
            <div className="flex-1 h-1.5 bg-[var(--surface)] rounded-full overflow-hidden"><div className="h-full rounded-full transition-all duration-700" style={{ width: `${v}%`, backgroundColor: v > 80 ? 'var(--danger)' : v > 60 ? 'var(--warning)' : 'var(--accent)' }} /></div>
            <span className="text-[10px] text-[var(--text)] w-7 text-right">{v}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Message Flow ────────────────────────────────────────────────────────────
function MessageFlow({ logs }: { logs: LogEntry[] }) {
  return (
    <div className="glass rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div><h3 className="text-base font-semibold text-[var(--text)]">Message Flow</h3><p className="text-xs text-[var(--muted)] mt-0.5">Live processing feed</p></div>
        <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-slow" /><span className="text-[10px] text-emerald-400 font-medium">LIVE</span></div>
      </div>
      <div className="space-y-1.5 max-h-[340px] overflow-y-auto pr-1">
        {logs.slice(0, 15).map(log => (
          <div key={log.id} className="flex items-center gap-2 p-2 rounded-lg bg-[var(--surface)]/50 border border-[var(--border)] hover:border-[var(--accent)]/30 transition-colors">
            <div className="shrink-0">{log.status === 'success' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : log.status === 'error' ? <AlertCircle className="w-3.5 h-3.5 text-red-400" /> : <Clock className="w-3.5 h-3.5 text-amber-400 animate-pulse" />}</div>
            <div className="flex-1 min-w-0"><p className="text-xs text-[var(--text)] truncate">{log.message}</p><p className="text-[10px] text-[var(--muted)]">{log.agent} → {log.channel}</p></div>
            <span className="text-[10px] text-[var(--muted)] shrink-0">{log.latency_ms}ms</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Performance Table ───────────────────────────────────────────────────────
function PerfTable({ agents }: { agents: Agent[] }) {
  const sorted = useMemo(() => [...agents].sort((a, b) => b.messages_processed - a.messages_processed).slice(0, 6), [agents])
  return (
    <div className="glass rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div><h3 className="text-base font-semibold text-[var(--text)]">Performance</h3><p className="text-xs text-[var(--muted)] mt-0.5">Agent comparison</p></div>
        <div className="p-2 rounded-lg bg-emerald-500/10"><TrendingUp className="w-4 h-4 text-emerald-400" /></div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="text-[var(--muted)] border-b border-[var(--border)]"><th className="text-left py-2 font-medium">Agent</th><th className="text-right py-2 font-medium">Messages</th><th className="text-right py-2 font-medium">Latency</th><th className="text-right py-2 font-medium">Success</th></tr></thead>
          <tbody>
            {sorted.map((a, i) => (
              <tr key={a.id} className="border-b border-[var(--border)]/50 hover:bg-[var(--surface)]/30 transition-colors">
                <td className="py-2"><div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white" style={{ backgroundColor: avatarColor(a.id) }}>{i + 1}</span><span className="text-[var(--text)] font-medium truncate max-w-[100px]">{a.name}</span></div></td>
                <td className="py-2 text-right text-[var(--text)]">{fmt(a.messages_processed)}</td>
                <td className="py-2 text-right text-[var(--warning)]">{a.latency_ms}ms</td>
                <td className="py-2 text-right text-emerald-400">{(95 + Math.random() * 5).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Load Balancer ───────────────────────────────────────────────────────────
function LoadBalancer({ nodes }: { nodes: LBNode[] }) {
  return (
    <div className="glass rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div><h3 className="text-base font-semibold text-[var(--text)]">Load Balancers</h3><p className="text-xs text-[var(--muted)] mt-0.5">Regional health</p></div>
        <div className="p-2 rounded-lg bg-[var(--warning)]/10"><Shield className="w-4 h-4 text-[var(--warning)]" /></div>
      </div>
      <div className="space-y-2">
        {nodes.map(n => (
          <div key={n.id} className="p-3 rounded-lg bg-[var(--surface)]/50 border border-[var(--border)] hover:border-[var(--accent)]/30 transition-colors">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2"><Server className="w-3.5 h-3.5 text-[var(--accent)]" /><span className="text-xs font-medium text-[var(--text)]">{n.name}</span><span className="text-[10px] text-[var(--muted)]">{n.region}</span></div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${n.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400' : n.status === 'degraded' ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'}`}>{n.status}</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div><p className="text-[10px] text-[var(--muted)]">Conns</p><p className="text-xs font-bold text-[var(--text)]">{fmt(n.connections)}</p></div>
              <div><p className="text-[10px] text-[var(--muted)]">CPU</p><div className="flex items-center gap-1"><div className="flex-1 h-1 bg-[var(--surface)] rounded-full"><div className="h-full rounded-full" style={{ width: `${n.cpu_percent}%`, backgroundColor: n.cpu_percent > 80 ? 'var(--danger)' : 'var(--success)' }} /></div><span className="text-[10px] text-[var(--text)]">{n.cpu_percent}%</span></div></div>
              <div><p className="text-[10px] text-[var(--muted)]">MEM</p><div className="flex items-center gap-1"><div className="flex-1 h-1 bg-[var(--surface)] rounded-full"><div className="h-full rounded-full" style={{ width: `${n.memory_percent}%`, backgroundColor: n.memory_percent > 80 ? 'var(--danger)' : 'var(--accent)' }} /></div><span className="text-[10px] text-[var(--text)]">{n.memory_percent}%</span></div></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Normalize API response ──────────────────────────────────────────────────
function normalizeResponse(raw: AgentReachData | Agent[]): AgentReachData {
  if (Array.isArray(raw)) {
    return { id: 'agent-reach-001', agents: raw, channels: [], routes: [] }
  }
  return {
    id: 'agent-reach-001',
    agents: Array.isArray(raw.agents) ? raw.agents : [],
    channels: Array.isArray(raw.channels) ? raw.channels : [],
    routes: Array.isArray(raw.routes) ? raw.routes : [],
  }
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function AgentReach() {
  const [data, setData] = useState<AgentReachData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [lbNodes] = useState<LBNode[]>(genLB)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [modalOpen, setModalOpen] = useState(false)
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)
  const [formData, setFormData] = useState({ name: '', status: 'active', messages_processed: 0, latency_ms: 0 })
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const result = await api.getAgentReach()
      const normalized = normalizeResponse(result)
      setData(normalized)
      setLogs(genLogs(normalized.agents, normalized.channels))
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])
  useEffect(() => {
    if (!autoRefresh || !data) return
    const t = setInterval(() => { setLogs(genLogs(data.agents, data.channels)) }, 5000)
    return () => clearInterval(t)
  }, [autoRefresh, data])

  // ─── CRUD Handlers ──────────────────────────────────────────────────────────
  const filteredAgents = useMemo(() => {
    if (!data) return []
    const q = searchQuery.toLowerCase().trim()
    if (!q) return data.agents
    return data.agents.filter(a => a.name.toLowerCase().includes(q) || a.status.toLowerCase().includes(q))
  }, [data, searchQuery])

  const openCreateModal = () => {
    setEditingAgent(null)
    setFormData({ name: '', status: 'active', messages_processed: 0, latency_ms: 0 })
    setModalOpen(true)
  }

  const openEditModal = (agent: Agent) => {
    setEditingAgent(agent)
    setFormData({ name: agent.name, status: agent.status, messages_processed: agent.messages_processed, latency_ms: agent.latency_ms })
    setModalOpen(true)
  }

  const closeModal = () => { setModalOpen(false); setEditingAgent(null) }

  const handleSave = async () => {
    if (!formData.name.trim()) return
    setSaving(true)
    try {
      if (editingAgent) {
        await api.updateAgent(editingAgent.id, formData)
      } else {
        await api.createAgent(formData)
      }
      closeModal()
      await fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Save failed') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: string) => {
    setDeleting(id)
    try {
      await api.deleteAgent(id)
      setSelectedIds(prev => { const n = new Set(prev); n.delete(id); return n })
      await fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Delete failed') }
    finally { setDeleting(null) }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    setBulkDeleting(true)
    try {
      await Promise.all(Array.from(selectedIds).map(id => api.deleteAgent(id)))
      setSelectedIds(new Set())
      await fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Bulk delete failed') }
    finally { setBulkDeleting(false) }
  }

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredAgents.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(filteredAgents.map(a => a.id)))
  }

  const exportCSV = () => {
    if (!data) return
    const headers = ['ID', 'Name', 'Status', 'Messages Processed', 'Latency (ms)']
    const rows = filteredAgents.map(a => [a.id, a.name, a.status, a.messages_processed, a.latency_ms])
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = 'agents.csv'; link.click()
    URL.revokeObjectURL(url)
  }

  const exportJSON = () => {
    if (!data) return
    const blob = new Blob([JSON.stringify(filteredAgents, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = 'agents.json'; link.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="flex flex-col items-center gap-3"><Loader2 className="w-8 h-8 text-[var(--accent)] animate-spin" /><p className="text-sm text-[var(--muted)]">Loading agent reach…</p></div></div>
  if (error) return <div className="flex items-center justify-center h-64"><div className="glass rounded-xl p-6 text-center max-w-md"><AlertCircle className="w-10 h-10 text-[var(--danger)] mx-auto mb-3" /><p className="text-[var(--text)] font-medium mb-2">Error loading data</p><p className="text-sm text-[var(--muted)] mb-4">{error}</p><button onClick={fetchData} className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity">Retry</button></div></div>
  if (!data || (data.agents.length === 0 && data.channels.length === 0 && data.routes.length === 0)) return <div className="flex items-center justify-center h-64"><p className="text-[var(--muted)]">No agent reach data available</p></div>

  const activeCount = data.agents.filter(a => a.status === 'active').length
  const totalMsg = data.agents.reduce((s, a) => s + a.messages_processed, 0)
  const avgLat = data.agents.length > 0 ? Math.round(data.agents.reduce((s, a) => s + a.latency_ms, 0) / data.agents.length) : 0
  const sorted = [...data.agents].sort((a, b) => b.messages_processed - a.messages_processed)

  const throughputData = data.channels.map(c => ({ name: c.name, throughput: c.throughput, fill: 'var(--accent)' }))
  const routeSuccessData = [
    { name: 'Success', value: data.routes.filter(r => r.success_rate >= 90).length, color: '#10b981' },
    { name: 'Degraded', value: data.routes.filter(r => r.success_rate >= 70 && r.success_rate < 90).length, color: '#f59e0b' },
    { name: 'Failed', value: data.routes.filter(r => r.success_rate < 70).length, color: '#ef4444' },
  ].filter(d => d.value > 0)

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div><h1 className="text-2xl font-bold text-[var(--text)]">Agent <span className="gradient-text">Reach</span></h1><p className="text-sm text-[var(--muted)] mt-1">Monitor agent performance, channels, and message routing</p></div>
        <div className="flex items-center gap-2">
          <button onClick={() => setAutoRefresh(!autoRefresh)} className={`p-2 rounded-lg border transition-colors ${autoRefresh ? 'bg-[var(--accent)]/10 border-[var(--accent)] text-[var(--accent)]' : 'bg-[var(--surface)] border-[var(--border)] text-[var(--muted)]'}`} title="Auto-refresh"><RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin-slow' : ''}`} /></button>
          <button onClick={fetchData} className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--accent)] transition-colors" title="Refresh"><Signal className="w-4 h-4" /></button>
        </div>
      </div>

      {/* CRUD Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-3 bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="flex items-center gap-2">
          <button onClick={openCreateModal} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors">
            <Plus className="w-4 h-4" /> Create
          </button>
          <button onClick={exportCSV} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-800 text-gray-100 text-sm font-medium hover:bg-gray-700 transition-colors border border-gray-700">
            <FileSpreadsheet className="w-4 h-4" /> CSV
          </button>
          <button onClick={exportJSON} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-800 text-gray-100 text-sm font-medium hover:bg-gray-700 transition-colors border border-gray-700">
            <FileJson className="w-4 h-4" /> JSON
          </button>
          {selectedIds.size > 0 && (
            <button onClick={handleBulkDelete} disabled={bulkDeleting} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-600/20 text-red-400 text-sm font-medium hover:bg-red-600/30 transition-colors border border-red-600/30">
              {bulkDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />} Delete ({selectedIds.size})
            </button>
          )}
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-9 pr-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm placeholder-gray-500 focus:outline-none focus:border-cyan-500 w-64"
          />
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { t: 'Total Agents', v: data.agents.length, s: `${activeCount} active`, i: <Bot className="w-5 h-5 text-[var(--accent)]" />, c: 'var(--accent)', tr: 12 },
          { t: 'Active', v: activeCount, s: `${data.agents.length - activeCount} idle`, i: <Activity className="w-5 h-5 text-emerald-400" />, c: 'var(--success)', tr: 8 },
          { t: 'Avg Latency', v: `${avgLat}ms`, s: 'All agents', i: <Clock className="w-5 h-5 text-[var(--warning)]" />, c: 'var(--warning)', tr: -5 },
          { t: 'Messages', v: fmt(totalMsg), s: 'Processed today', i: <MessageSquare className="w-5 h-5 text-[var(--accent2)]" />, c: 'var(--accent2)', tr: 23 },
        ].map(({ t, v, s, i, c, tr }) => (
          <div key={t} className="glass card-hover rounded-xl p-4 animate-fade-in">
            <div className="flex items-start justify-between mb-2"><span className="text-xs font-medium text-[var(--muted)]">{t}</span><div className="p-1.5 rounded-lg" style={{ backgroundColor: `${c}15` }}>{i}</div></div>
            <div className="text-xl font-bold text-[var(--text)] mb-1">{v}</div>
            <p className="text-[10px] text-[var(--muted)] mb-1">{s}</p>
            <div className="flex items-center gap-1"><TrendingUp className={`w-3 h-3 ${tr >= 0 ? 'text-emerald-400' : 'text-red-400'}`} /><span className={`text-[10px] font-semibold ${tr >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{tr >= 0 ? '+' : ''}{tr}%</span></div>
          </div>
        ))}
      </div>

      {/* Network Graph + Message Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <NetworkGraph agents={data.agents} routes={data.routes} />
        <MessageFlow logs={logs} />
      </div>

      {/* Agent Cards */}
      {data.agents.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-3"><h2 className="text-lg font-semibold text-[var(--text)]">Agents</h2><span className="text-xs text-[var(--muted)]">{data.agents.length} total</span></div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {sorted.map((a, i) => <AgentCard key={a.id} agent={a} rank={i} />)}
          </div>
        </section>
      )}

      {/* Agent Table with CRUD */}
      {filteredAgents.length > 0 && (
        <section className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-gray-800">
            <h2 className="text-lg font-semibold text-gray-100">All Agents</h2>
            <span className="text-xs text-gray-400">{filteredAgents.length} agents</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-3 px-4 font-medium w-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === filteredAgents.length && filteredAgents.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500"
                    />
                  </th>
                  <th className="text-left py-3 px-4 font-medium">Name</th>
                  <th className="text-left py-3 px-4 font-medium">Status</th>
                  <th className="text-right py-3 px-4 font-medium">Messages</th>
                  <th className="text-right py-3 px-4 font-medium">Latency</th>
                  <th className="text-right py-3 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAgents.map(agent => (
                  <tr key={agent.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 px-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(agent.id)}
                        onChange={() => toggleSelect(agent.id)}
                        className="rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500"
                      />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ backgroundColor: avatarColor(agent.id) }}>{initials(agent.name)}</div>
                        <span className="text-gray-100 font-medium">{agent.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${agent.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : agent.status === 'idle' ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${agent.status === 'active' ? 'bg-emerald-400' : agent.status === 'idle' ? 'bg-amber-400' : 'bg-red-400'}`} />
                        {agent.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-100">{fmt(agent.messages_processed)}</td>
                    <td className="py-3 px-4 text-right text-amber-400">{agent.latency_ms}ms</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openEditModal(agent)} className="p-1.5 rounded-lg text-gray-400 hover:text-cyan-400 hover:bg-cyan-400/10 transition-colors" title="Edit">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(agent.id)} disabled={deleting === agent.id} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50" title="Delete">
                          {deleting === agent.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {data.channels.length > 0 && (
          <div className="glass rounded-xl p-5 animate-fade-in">
            <div className="flex items-center justify-between mb-3"><div><h3 className="text-base font-semibold text-[var(--text)]">Channel Throughput</h3><p className="text-xs text-[var(--muted)] mt-0.5">Messages/sec by channel</p></div><div className="p-2 rounded-lg bg-[var(--accent)]/10"><Radio className="w-4 h-4 text-[var(--accent)]" /></div></div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={throughputData}>
                <defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent)" stopOpacity={0.9} /><stop offset="100%" stopColor="var(--accent2)" stopOpacity={0.4} /></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
                <YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => fmt(v)} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} formatter={(v: number) => [fmt(v), 'Throughput']} />
                <Bar dataKey="throughput" fill="url(#barGrad)" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {data.routes.length > 0 && (
          <div className="glass rounded-xl p-5 animate-fade-in">
            <div className="flex items-center justify-between mb-3"><div><h3 className="text-base font-semibold text-[var(--text)]">Route Success Rate</h3><p className="text-xs text-[var(--muted)] mt-0.5">Distribution by health</p></div><div className="p-2 rounded-lg bg-emerald-500/10"><CheckCircle2 className="w-4 h-4 text-emerald-400" /></div></div>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={routeSuccessData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={4} dataKey="value">
                  {routeSuccessData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Form Modal (Create/Edit) */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gray-900 rounded-xl border border-gray-800 w-full max-w-md mx-4 shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h3 className="text-lg font-semibold text-gray-100">{editingAgent ? 'Edit Agent' : 'Create Agent'}</h3>
              <button onClick={closeModal} className="p-1 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-gray-800 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData(d => ({ ...d, name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
                  placeholder="Enter agent name"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                <select
                  value={formData.status}
                  onChange={e => setFormData(d => ({ ...d, status: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
                >
                  <option value="active">Active</option>
                  <option value="idle">Idle</option>
                  <option value="inactive">Inactive</option>
                  <option value="degraded">Degraded</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Messages Processed</label>
                  <input
                    type="number"
                    value={formData.messages_processed}
                    onChange={e => setFormData(d => ({ ...d, messages_processed: Number(e.target.value) }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
                    min="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Latency (ms)</label>
                  <input
                    type="number"
                    value={formData.latency_ms}
                    onChange={e => setFormData(d => ({ ...d, latency_ms: Number(e.target.value) }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:border-cyan-500"
                    min="0"
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-800">
              <button onClick={closeModal} className="px-4 py-2 rounded-lg text-gray-300 text-sm hover:bg-gray-800 transition-colors">
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name.trim() || saving}
                className="px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : editingAgent ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Performance Table + Load Balancer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {data.agents.length > 0 && <PerfTable agents={data.agents} />}
        <LoadBalancer nodes={lbNodes} />
      </div>
    </div>
  )
}
