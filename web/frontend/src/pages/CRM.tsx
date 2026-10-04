import { useEffect, useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts'
import { Users, UserCheck, TrendingUp, DollarSign, Phone, Mail, Calendar, FileText, CheckCircle2, Star, Target, ChevronRight, Plus, Search, Filter, MoreHorizontal, ArrowUpRight, ArrowDownRight, Briefcase, BarChart3, PieChart as PieChartIcon, Activity, Loader2, AlertCircle, X } from 'lucide-react'
import { api, CRMData } from '../api/client'

interface Lead { id: string; name: string; email: string; company: string; status: string; score: number; value: number; source: string; lastContact: string }
interface Opportunity { id: string; name: string; stage: string; value: number; probability: number; expectedClose: string; owner: string }
interface ForecastData { q1: number; q2: number; q3: number; q4: number }
interface Interaction { id: string; type: 'call' | 'email' | 'meeting' | 'note' | 'deal'; title: string; contact: string; time: string; outcome?: string }
interface SegmentData { name: string; value: number; color: string }
interface ScoreRange { range: string; count: number; color: string }

const STATUS_COLORS: Record<string, string> = { Qualified: '#10b981', Contacted: '#3b82f6', New: '#6b7280', Unqualified: '#ef4444', Converted: '#8b5cf6' }
const STAGE_COLORS: Record<string, string> = { 'Prospecting': '#6366f1', 'Qualification': '#8b5cf6', 'Proposal': '#a855f7', 'Negotiation': '#f59e0b', 'Closed Won': '#10b981', 'Closed Lost': '#ef4444' }
const STAGE_ORDER = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
const SEGMENT_COLORS = ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899']

function formatCurrency(value: number): string {
  if (value == null || isNaN(value)) return '$0'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(2)}`
}
function formatNumber(value: number): string {
  if (value == null || isNaN(value)) return '0'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toLocaleString()
}
function getStatusColor(status: string): string { return STATUS_COLORS[status] ?? '#6b7280' }
function getStageColor(stage: string): string { return STAGE_COLORS[stage] ?? '#6b7280' }
function getScoreColor(score: number): string { if (score >= 75) return '#10b981'; if (score >= 50) return '#f59e0b'; return '#ef4444' }
function getScoreLabel(score: number): string { if (score >= 75) return 'Hot'; if (score >= 50) return 'Warm'; return 'Cold' }

function generateInteractions(leads: Lead[], opportunities: Opportunity[]): Interaction[] {
  const interactions: Interaction[] = []
  const now = Date.now()
  leads.slice(0, 4).forEach((lead, i) => {
    interactions.push({ id: `int-lead-${lead.id}`, type: i % 2 === 0 ? 'call' : 'email', title: i % 2 === 0 ? `Discovery call with ${lead.name}` : `Follow-up email to ${lead.name}`, contact: lead.name, time: new Date(now - (i + 1) * 3600000 * 5).toLocaleString(), outcome: i % 2 === 0 ? 'Positive' : 'Pending' })
  })
  opportunities.slice(0, 3).forEach((opp, i) => {
    interactions.push({ id: `int-opp-${opp.id}`, type: i === 0 ? 'meeting' : i === 1 ? 'note' : 'deal', title: i === 0 ? `Demo: ${opp.name}` : i === 1 ? `Notes: ${opp.name}` : `Proposal sent: ${opp.name}`, contact: opp.owner, time: new Date(now - (i + 1) * 3600000 * 12).toLocaleString(), outcome: i === 2 ? 'Sent' : undefined })
  })
  return interactions.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
}

function generateSegments(leads: Lead[]): SegmentData[] {
  const segments: Record<string, number> = { Enterprise: 0, 'Mid-Market': 0, SMB: 0, Startup: 0 }
  leads.forEach((lead) => { if (lead.value >= 100000) segments['Enterprise']++; else if (lead.value >= 50000) segments['Mid-Market']++; else if (lead.value >= 10000) segments['SMB']++; else segments['Startup']++ })
  return Object.entries(segments).map(([name, value], i) => ({ name, value, color: SEGMENT_COLORS[i % SEGMENT_COLORS.length] }))
}

function generateScoreRanges(leads: Lead[]): ScoreRange[] {
  const ranges = [{ range: '0-25', min: 0, max: 25, color: '#ef4444' }, { range: '26-50', min: 26, max: 50, color: '#f59e0b' }, { range: '51-75', min: 51, max: 75, color: '#3b82f6' }, { range: '76-100', min: 76, max: 100, color: '#10b981' }]
  return ranges.map((r) => ({ range: r.range, count: leads.filter((l) => l.score >= r.min && l.score <= r.max).length, color: r.color }))
}

function StatusBadge({ status }: { status: string }) {
  const color = getStatusColor(status)
  return <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium" style={{ backgroundColor: `${color}18`, color, border: `1px solid ${color}35` }}><span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />{status}</span>
}

function StageBadge({ stage }: { stage: string }) {
  const color = getStageColor(stage)
  return <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" style={{ backgroundColor: `${color}18`, color, border: `1px solid ${color}35` }}>{stage}</span>
}

function ScoreBar({ score }: { score: number }) {
  const clamped = Math.min(100, Math.max(0, score || 0))
  const color = getScoreColor(clamped)
  const label = getScoreLabel(clamped)
  return <div className="flex items-center gap-2"><div className="h-2 w-20 overflow-hidden rounded-full bg-[var(--border)]"><div className="h-full rounded-full transition-all duration-500" style={{ width: `${clamped}%`, backgroundColor: color }} /></div><span className="text-xs font-medium" style={{ color }}>{clamped}</span><span className="rounded px-1.5 py-0.5 text-[10px] font-semibold" style={{ backgroundColor: `${color}18`, color }}>{label}</span></div>
}

function ProbabilityBar({ probability }: { probability: number }) {
  const clamped = Math.min(100, Math.max(0, probability || 0))
  return <div className="flex items-center gap-2"><div className="h-2 w-16 overflow-hidden rounded-full bg-[var(--border)]"><div className="h-full rounded-full bg-cyan-500 transition-all duration-500" style={{ width: `${clamped}%` }} /></div><span className="text-xs text-[var(--muted)]">{clamped}%</span></div>
}

interface SummaryCardProps { title: string; value: string; subtitle: string; icon: React.ReactNode; color: string; trend?: { value: number; positive: boolean } }
function SummaryCard({ title, value, subtitle, icon, color, trend }: SummaryCardProps) {
  return <div className="glass card-hover rounded-xl p-5 animate-fade-in"><div className="flex items-start justify-between"><div className="flex-1"><span className="text-sm font-medium text-[var(--muted)]">{title}</span><div className="mt-2 text-2xl font-bold text-[var(--text)]">{value}</div><div className="mt-1 text-xs text-[var(--muted)]">{subtitle}</div>{trend && <div className="mt-2 flex items-center gap-1">{trend.positive ? <ArrowUpRight className="h-3.5 w-3.5 text-[var(--success)]" /> : <ArrowDownRight className="h-3.5 w-3.5 text-[var(--danger)]" />}<span className={`text-xs font-semibold ${trend.positive ? 'text-[var(--success)]' : 'text-[var(--danger)]'}`}>{trend.positive ? '+' : ''}{trend.value}%</span><span className="text-xs text-[var(--muted)]">vs last month</span></div>}</div><div className="rounded-lg p-2.5" style={{ backgroundColor: `${color}15` }}>{icon}</div></div></div>
}

function LeadsTable({ leads, onAdd }: { leads: Lead[]; onAdd: () => void }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('All')
  const filtered = useMemo(() => leads.filter((lead) => { const matchesSearch = lead.name.toLowerCase().includes(search.toLowerCase()) || lead.company.toLowerCase().includes(search.toLowerCase()); const matchesStatus = statusFilter === 'All' || lead.status === statusFilter; return matchesSearch && matchesStatus }), [leads, search, statusFilter])
  const statuses = ['All', ...Array.from(new Set(leads.map((l) => l.status)))]
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Leads</h2><p className="text-xs text-[var(--muted)]">{filtered.length} of {leads.length} leads</p></div><div className="flex items-center gap-2"><div className="relative"><Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--muted)]" /><input type="text" placeholder="Search leads..." value={search} onChange={(e) => setSearch(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--bg)] py-1.5 pl-8 pr-3 text-xs text-[var(--text)] placeholder-[var(--muted)] outline-none focus:border-[var(--accent)]" /></div><div className="relative"><Filter className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--muted)]" /><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="appearance-none rounded-lg border border-[var(--border)] bg-[var(--bg)] py-1.5 pl-8 pr-8 text-xs text-[var(--text)] outline-none focus:border-[var(--accent)]">{statuses.map((s) => <option key={s} value={s}>{s}</option>)}</select></div><button onClick={onAdd} className="flex items-center gap-1 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"><Plus className="h-3.5 w-3.5" /> Add</button></div></div><div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead><tr className="border-b border-[var(--border)] text-xs uppercase tracking-wider text-[var(--muted)]"><th className="pb-3 pr-4 font-medium">Lead</th><th className="pb-3 pr-4 font-medium">Status</th><th className="pb-3 pr-4 font-medium">Score</th><th className="pb-3 pr-4 font-medium">Value</th><th className="pb-3 pr-4 font-medium">Source</th><th className="pb-3 font-medium">Actions</th></tr></thead><tbody>{filtered.map((lead) => <tr key={lead.id} className="border-b border-[var(--border)] transition-colors last:border-0 hover:bg-white/5"><td className="py-3 pr-4"><div><div className="font-medium text-[var(--text)]">{lead.name}</div><div className="text-xs text-[var(--muted)]">{lead.company}</div></div></td><td className="py-3 pr-4"><StatusBadge status={lead.status} /></td><td className="py-3 pr-4"><ScoreBar score={lead.score} /></td><td className="py-3 pr-4 font-medium text-[var(--text)]">{formatCurrency(lead.value)}</td><td className="py-3 pr-4 text-xs text-[var(--muted)]">{lead.source}</td><td className="py-3"><div className="flex items-center gap-1"><button className="rounded p-1 text-[var(--muted)] hover:bg-white/10 hover:text-[var(--text)]" title="Call"><Phone className="h-3.5 w-3.5" /></button><button className="rounded p-1 text-[var(--muted)] hover:bg-white/10 hover:text-[var(--text)]" title="Email"><Mail className="h-3.5 w-3.5" /></button><button className="rounded p-1 text-[var(--muted)] hover:bg-white/10 hover:text-[var(--text)]" title="More"><MoreHorizontal className="h-3.5 w-3.5" /></button></div></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="py-8 text-center text-sm text-[var(--muted)]">No leads match your filters</div>}</div></div>
}

function OpportunitiesPipeline({ opportunities, onViewAll }: { opportunities: Opportunity[]; onViewAll: () => void }) {
  const stages = STAGE_ORDER.filter((s) => opportunities.some((o) => o.stage === s))
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Opportunities Pipeline</h2><p className="text-xs text-[var(--muted)]">{opportunities.length} open opportunities</p></div><button onClick={onViewAll} className="flex items-center gap-1 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:bg-white/5"><Briefcase className="h-3.5 w-3.5" /> View All</button></div><div className="mb-5"><div className="flex h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">{stages.map((stage) => { const stageOpps = opportunities.filter((o) => o.stage === stage); const totalValue = stageOpps.reduce((sum, o) => sum + o.value, 0); const allValue = opportunities.reduce((sum, o) => sum + o.value, 0); const pct = allValue > 0 ? (totalValue / allValue) * 100 : 0; return <div key={stage} className="h-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: getStageColor(stage) }} title={`${stage}: ${formatCurrency(totalValue)}`} /> })}</div><div className="mt-2 flex flex-wrap gap-3">{stages.map((stage) => { const count = opportunities.filter((o) => o.stage === stage).length; return <div key={stage} className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: getStageColor(stage) }} /> {stage} ({count})</div> })}</div></div><div className="space-y-3">{opportunities.map((opp) => <div key={opp.id} className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-4 transition-colors hover:border-[var(--accent)]"><div className="mb-2 flex items-center justify-between"><span className="font-medium text-[var(--text)]">{opp.name}</span><StageBadge stage={opp.stage} /></div><div className="flex items-center justify-between text-sm"><div className="flex items-center gap-3"><span className="text-[var(--text)]">{formatCurrency(opp.value)}</span><span className="text-xs text-[var(--muted)]">Owner: {opp.owner}</span></div><ProbabilityBar probability={opp.probability} /></div><div className="mt-2 flex items-center justify-between text-xs text-[var(--muted)]"><div className="flex items-center gap-1"><Calendar className="h-3 w-3" /> Expected: {opp.expectedClose}</div><div className="flex items-center gap-1"><ChevronRight className="h-3 w-3" /> Weighted: {formatCurrency(opp.value * opp.probability / 100)}</div></div></div>)}</div></div>
}

function ForecastChart({ forecast }: { forecast: ForecastData }) {
  const data = [{ quarter: 'Q1', value: forecast.q1, color: '#06b6d4' }, { quarter: 'Q2', value: forecast.q2, color: '#8b5cf6' }, { quarter: 'Q3', value: forecast.q3, color: '#a855f7' }, { quarter: 'Q4', value: forecast.q4, color: '#10b981' }]
  const total = data.reduce((s, d) => s + d.value, 0)
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Quarterly Forecast</h2><p className="text-xs text-[var(--muted)]">Total projected: {formatCurrency(total)}</p></div><div className="flex items-center gap-1 rounded-lg border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--muted)]"><BarChart3 className="h-3.5 w-3.5" /> 2024</div></div><div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="quarter" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} /><YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => formatCurrency(v)} /><Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} labelStyle={{ color: 'var(--muted)' }} formatter={(value: number) => [formatCurrency(value), 'Forecast']} /><Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={60}>{data.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}</Bar></BarChart></ResponsiveContainer></div></div>
}

function SegmentationChart({ segments }: { segments: SegmentData[] }) {
  const total = segments.reduce((s, seg) => s + seg.value, 0)
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Customer Segmentation</h2><p className="text-xs text-[var(--muted)]">{total} total customers</p></div><PieChartIcon className="h-4 w-4 text-[var(--muted)]" /></div><div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={segments} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">{segments.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}</Pie><Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} formatter={(value: number, name: string) => [`${value} (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`, name]} /><Legend verticalAlign="bottom" iconType="circle" iconSize={8} formatter={(value: string) => <span style={{ color: 'var(--muted)', fontSize: '12px' }}>{value}</span>} /></PieChart></ResponsiveContainer></div></div>
}

function InteractionsTimeline({ interactions }: { interactions: Interaction[] }) {
  const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = { call: { icon: <Phone className="h-3.5 w-3.5" />, color: '#3b82f6' }, email: { icon: <Mail className="h-3.5 w-3.5" />, color: '#8b5cf6' }, meeting: { icon: <Calendar className="h-3.5 w-3.5" />, color: '#f59e0b' }, note: { icon: <FileText className="h-3.5 w-3.5" />, color: '#6b7280' }, deal: { icon: <CheckCircle2 className="h-3.5 w-3.5" />, color: '#10b981' } }
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Recent Interactions</h2><p className="text-xs text-[var(--muted)]">Latest customer touchpoints</p></div><Activity className="h-4 w-4 text-[var(--muted)]" /></div><div className="space-y-0">{interactions.map((interaction, idx) => { const config = typeConfig[interaction.type] ?? typeConfig.note; const isLast = idx === interactions.length - 1; return <div key={interaction.id} className="relative flex gap-3 pb-4">{!isLast && <div className="absolute left-[11px] top-6 h-full w-px bg-[var(--border)]" />}<div className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full" style={{ backgroundColor: `${config.color}20`, color: config.color }}>{config.icon}</div><div className="flex-1 min-w-0"><div className="flex items-start justify-between gap-2"><div><div className="text-sm font-medium text-[var(--text)]">{interaction.title}</div><div className="text-xs text-[var(--muted)]">{interaction.contact} · {interaction.time}</div></div>{interaction.outcome && <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ backgroundColor: interaction.outcome === 'Positive' ? '#10b98118' : '#f59e0b18', color: interaction.outcome === 'Positive' ? '#10b981' : '#f59e0b' }}>{interaction.outcome}</span>}</div></div></div> })}</div></div>
}

function LeadScoringBreakdown({ scoreRanges, leads }: { scoreRanges: ScoreRange[]; leads: Lead[] }) {
  const maxCount = Math.max(...scoreRanges.map((r) => r.count), 1)
  const avgScore = leads.length > 0 ? Math.round(leads.reduce((s, l) => s + l.score, 0) / leads.length) : 0
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Lead Scoring Breakdown</h2><p className="text-xs text-[var(--muted)]">Average score: {avgScore}/100</p></div><div className="flex items-center gap-1.5"><Star className="h-4 w-4 text-[var(--warning)]" /><span className="text-sm font-semibold text-[var(--text)]">{avgScore}</span></div></div><div className="space-y-3">{scoreRanges.map((range) => <div key={range.range} className="flex items-center gap-3"><span className="w-14 text-xs text-[var(--muted)]">{range.range}</span><div className="flex-1"><div className="h-3 overflow-hidden rounded-full bg-[var(--border)]"><div className="h-full rounded-full transition-all duration-500" style={{ width: `${(range.count / maxCount) * 100}%`, backgroundColor: range.color }} /></div></div><span className="w-8 text-right text-xs font-medium text-[var(--text)]">{range.count}</span></div>)}</div><div className="mt-4 flex items-center gap-4 border-t border-[var(--border)] pt-3"><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#ef4444]" /> Cold (0-25)</div><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#f59e0b]" /> Warm (26-50)</div><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#3b82f6]" /> Hot (51-75)</div><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#10b981]" /> Premium (76-100)</div></div></div>
}

function LoadingState() {
  return <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4"><Loader2 className="h-10 w-10 text-[var(--accent)] animate-spin" /><p className="text-[var(--muted)] text-sm">Loading CRM data...</p></div>
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4"><AlertCircle className="h-10 w-10 text-[var(--danger)]" /><p className="text-[var(--text)] text-sm">{message}</p><button onClick={onRetry} className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity">Retry</button></div>
}

export default function CRM() {
  const [data, setData] = useState<CRMData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modal, setModal] = useState<string | null>(null)

  const fetchCRM = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.getCRM()
      // Normalize: handle both array and object responses
      const normalized: CRMData = Array.isArray(result) ? result[0] : result
      setData(normalized)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load CRM data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCRM() }, [])

  const enrichedLeads: Lead[] = useMemo(() => {
    if (!data || !Array.isArray(data.leads)) return []
    const sources = ['Website', 'Referral', 'LinkedIn', 'Cold Outreach', 'Event', 'Partner']
    const companies = ['TechCorp', 'Innovate.io', 'DataFlow', 'CloudSync', 'AIVentures', 'NexGen', 'Pinnacle', 'Vertex', 'Quantum', 'Zenith', 'Atlas', 'Beacon', 'Catalyst', 'Dynamo', 'Eclipse']
    return data.leads.map((lead, i) => ({ ...lead, email: `${(lead.name || '').toLowerCase().replace(/\s/g, '.')}@${companies[i % companies.length].toLowerCase()}.com`, company: companies[i % companies.length], source: sources[i % sources.length], lastContact: new Date(Date.now() - (i + 1) * 86400000 * 2).toLocaleDateString() }))
  }, [data])

  const enrichedOpportunities: Opportunity[] = useMemo(() => {
    if (!data || !Array.isArray(data.opportunities)) return []
    const owners = ['Alex Thompson', 'Jordan Lee', 'Casey Rivera', 'Morgan Blake', 'Taylor Reed']
    return data.opportunities.map((opp, i) => ({ ...opp, expectedClose: new Date(Date.now() + (i + 1) * 30 * 86400000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }), owner: owners[i % owners.length] }))
  }, [data])

  const interactions = useMemo(() => generateInteractions(enrichedLeads, enrichedOpportunities), [enrichedLeads, enrichedOpportunities])
  const segments = useMemo(() => generateSegments(enrichedLeads), [enrichedLeads])
  const scoreRanges = useMemo(() => generateScoreRanges(enrichedLeads), [enrichedLeads])

  const metrics = useMemo(() => {
    if (!data) return null
    const totalLeads = enrichedLeads.length
    const qualified = enrichedLeads.filter((l) => l.status === 'Qualified').length
    const conversionRate = totalLeads > 0 ? Math.round((qualified / totalLeads) * 100) : 0
    const avgDealSize = totalLeads > 0 ? Math.round(enrichedLeads.reduce((s, l) => s + l.value, 0) / totalLeads) : 0
    const totalPipelineValue = enrichedOpportunities.reduce((s, o) => s + o.value, 0)
    const weightedPipelineValue = enrichedOpportunities.reduce((s, o) => s + (o.value * o.probability) / 100, 0)
    return { totalLeads, qualified, conversionRate, avgDealSize, totalPipelineValue, weightedPipelineValue }
  }, [data, enrichedLeads, enrichedOpportunities])

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={fetchCRM} />
  if (!data) return <ErrorState message="No data received" onRetry={fetchCRM} />

  const forecast: ForecastData = data.forecast ?? { q1: 0, q2: 0, q3: 0, q4: 0 }

  const handleOpenModal = (label: string) => setModal(label)

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold gradient-text">CRM</h1><p className="text-sm text-[var(--muted)] mt-1">Leads, opportunities, and revenue forecast</p></div>
        <div className="flex items-center gap-2">
          <button onClick={() => handleOpenModal('Goals')} className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:bg-white/5"><Target className="h-3.5 w-3.5" /> Goals</button>
          <button onClick={() => handleOpenModal('New Lead')} className="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"><Plus className="h-3.5 w-3.5" /> New Lead</button>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard title="Total Leads" value={formatNumber(metrics?.totalLeads ?? 0)} subtitle="Active in pipeline" icon={<Users className="h-5 w-5 text-[var(--accent)]" />} color="var(--accent)" trend={{ value: 12.5, positive: true }} />
        <SummaryCard title="Qualified" value={formatNumber(metrics?.qualified ?? 0)} subtitle="Ready for outreach" icon={<UserCheck className="h-5 w-5 text-[var(--success)]" />} color="var(--success)" trend={{ value: 8.2, positive: true }} />
        <SummaryCard title="Conversion Rate" value={`${metrics?.conversionRate ?? 0}%`} subtitle="Lead to qualified" icon={<TrendingUp className="h-5 w-5 text-[var(--accent2)]" />} color="var(--accent2)" trend={{ value: 2.1, positive: false }} />
        <SummaryCard title="Avg Deal Size" value={formatCurrency(metrics?.avgDealSize ?? 0)} subtitle="Per opportunity" icon={<DollarSign className="h-5 w-5 text-[var(--warning)]" />} color="var(--warning)" trend={{ value: 5.4, positive: true }} />
      </div>
      <LeadsTable leads={enrichedLeads} onAdd={() => handleOpenModal('Add Lead')} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OpportunitiesPipeline opportunities={enrichedOpportunities} onViewAll={() => handleOpenModal('View All Opportunities')} />
        <ForecastChart forecast={forecast} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SegmentationChart segments={segments} />
        <InteractionsTimeline interactions={interactions} />
        <LeadScoringBreakdown scoreRanges={scoreRanges} leads={enrichedLeads} />
      </div>
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
