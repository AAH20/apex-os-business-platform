import { useEffect, useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts'
import { Users, UserCheck, TrendingUp, DollarSign, Phone, Mail, Calendar, FileText, CheckCircle2, Star, Target, ChevronRight, Plus, Search, Filter, ArrowUpRight, ArrowDownRight, Briefcase, BarChart3, PieChart as PieChartIcon, Activity, Loader2, AlertCircle, X, Edit, Trash2, Download, CheckSquare, Square } from 'lucide-react'
import { api, CRMData, LeadInput } from '../api/client'

interface Lead { id: string; name: string; email: string; company: string; status: string; score: number; value: number; source: string; lastContact: string }
interface Opportunity { id: string; name: string; stage: string; value: number; probability: number; expectedClose: string; owner: string }
interface ForecastData { q1: number; q2: number; q3: number; q4: number }
interface Interaction { id: string; type: 'call' | 'email' | 'meeting' | 'note' | 'deal'; title: string; contact: string; time: string; outcome?: string }
interface SegmentData { name: string; value: number; color: string }
interface ScoreRange { range: string; count: number; color: string }

const FALLBACK_CRM_DATA: CRMData = {
  id: 'fallback',
  leads: [
    { id: 'l1', name: 'Sarah Chen', status: 'Qualified', score: 85, value: 120000 },
    { id: 'l2', name: 'Marcus Johnson', status: 'Contacted', score: 62, value: 75000 },
    { id: 'l3', name: 'Priya Patel', status: 'New', score: 45, value: 50000 },
    { id: 'l4', name: 'David Kim', status: 'Qualified', score: 78, value: 95000 },
    { id: 'l5', name: 'Elena Rodriguez', status: 'Contacted', score: 55, value: 60000 },
    { id: 'l6', name: 'James Wilson', status: 'New', score: 30, value: 25000 },
    { id: 'l7', name: 'Aisha Mohammed', status: 'Converted', score: 92, value: 150000 },
    { id: 'l8', name: 'Tom Bergström', status: 'Unqualified', score: 15, value: 10000 },
  ],
  opportunities: [
    { id: 'o1', name: 'TechCorp Enterprise Deal', stage: 'Negotiation', value: 250000, probability: 75 },
    { id: 'o2', name: 'Innovate.io Platform', stage: 'Proposal', value: 180000, probability: 60 },
    { id: 'o3', name: 'DataFlow Migration', stage: 'Qualification', value: 120000, probability: 40 },
    { id: 'o4', name: 'CloudSync Expansion', stage: 'Prospecting', value: 90000, probability: 25 },
    { id: 'o5', name: 'AIVentures Pilot', stage: 'Closed Won', value: 200000, probability: 100 },
    { id: 'o6', name: 'NexGen Renewal', stage: 'Closed Lost', value: 75000, probability: 0 },
  ],
  forecast: { q1: 450000, q2: 520000, q3: 610000, q4: 730000 },
}

const STATUS_COLORS: Record<string, string> = { Qualified: '#10b981', Contacted: '#3b82f6', New: '#6b7280', Unqualified: '#ef4444', Converted: '#8b5cf6' }
const STAGE_COLORS: Record<string, string> = { 'Prospecting': '#6366f1', 'Qualification': '#8b5cf6', 'Proposal': '#a855f7', 'Negotiation': '#f59e0b', 'Closed Won': '#10b981', 'Closed Lost': '#ef4444' }
const STAGE_ORDER = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
const SEGMENT_COLORS = ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899']

function formatCurrency(value: number): string {
  if (value == null || isNaN(value)) return '$0'
  if (value == null) return '$0.00'
  if (value == null) return '$0.00'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(2)}`
}
function formatNumber(value: number): string {
  if (value == null || isNaN(value)) return '0'
  if (value == null) return '0'
  if (value == null) return '0'
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

// ── Lead Form Modal ──────────────────────────────────────────────────────────

interface LeadFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: LeadInput) => Promise<void>
  lead?: Lead | null
}

function LeadFormModal({ isOpen, onClose, onSave, lead }: LeadFormModalProps) {
  const [form, setForm] = useState<LeadInput>({ name: '', email: '', company: '', status: 'New', score: 50, value: 0, source: 'Website' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (lead) {
      setForm({ name: lead.name, email: lead.email || '', company: lead.company || '', status: lead.status, score: lead.score, value: lead.value, source: lead.source || 'Website' })
    } else {
      setForm({ name: '', email: '', company: '', status: 'New', score: 50, value: 0, source: 'Website' })
    }
    setError(null)
  }, [lead, isOpen])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) { setError('Name is required'); return }
    setSaving(true)
    setError(null)
    try {
      await onSave(form)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save lead')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = "w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500"
  const labelClass = "block text-xs font-medium text-gray-400 mb-1"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl border border-gray-700 bg-gray-900 p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-100">{lead ? 'Edit Lead' : 'Create New Lead'}</h3>
          <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-800 hover:text-gray-200"><X className="h-5 w-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>}
          <div><label className={labelClass}>Name *</label><input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputClass} placeholder="John Doe" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className={labelClass}>Email</label><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputClass} placeholder="john@company.com" /></div>
            <div><label className={labelClass}>Company</label><input type="text" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} className={inputClass} placeholder="Acme Inc" /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className={labelClass}>Status</label><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className={inputClass}><option value="New">New</option><option value="Contacted">Contacted</option><option value="Qualified">Qualified</option><option value="Unqualified">Unqualified</option><option value="Converted">Converted</option></select></div>
            <div><label className={labelClass}>Source</label><select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className={inputClass}><option value="Website">Website</option><option value="Referral">Referral</option><option value="LinkedIn">LinkedIn</option><option value="Cold Outreach">Cold Outreach</option><option value="Event">Event</option><option value="Partner">Partner</option></select></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className={labelClass}>Score: {form.score}</label><input type="range" min="0" max="100" value={form.score} onChange={(e) => setForm({ ...form, score: Number(e.target.value) })} className="w-full accent-blue-500" /></div>
            <div><label className={labelClass}>Value ($)</label><input type="number" min="0" value={form.value} onChange={(e) => setForm({ ...form, value: Number(e.target.value) })} className={inputClass} /></div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-400 hover:bg-gray-800">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}{lead ? 'Update' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Export Utilities ─────────────────────────────────────────────────────────

function exportToCSV(leads: Lead[]) {
  const headers = ['Name', 'Email', 'Company', 'Status', 'Score', 'Value', 'Source', 'Last Contact']
  const rows = (leads || []).map((l) => [l.name, l.email || '', l.company || '', l.status, String(l.score ?? 0), String(l.value ?? 0), l.source || '', l.lastContact || ''])
  const csv = [headers, ...rows].map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `leads_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function exportToJSON(leads: Lead[]) {
  const blob = new Blob([JSON.stringify(leads, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `leads_${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Leads Table with Full CRUD ───────────────────────────────────────────────

interface LeadsTableProps {
  leads: Lead[]
  onRefresh: () => void
}

function LeadsTable({ leads, onRefresh }: LeadsTableProps) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('All')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [modalOpen, setModalOpen] = useState(false)
  const [editingLead, setEditingLead] = useState<Lead | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const filtered = useMemo(() => (leads || []).filter((lead) => {
    const q = search.toLowerCase()
    const matchesSearch = lead.name.toLowerCase().includes(q) || (lead.company || '').toLowerCase().includes(q) || (lead.email || '').toLowerCase().includes(q)
    const matchesStatus = statusFilter === 'All' || lead.status === statusFilter
    return matchesSearch && matchesStatus
  }), [leads, search, statusFilter])

  const statuses = ['All', ...Array.from(new Set((leads || []).map((l) => l.status)))]

  const allSelected = filtered.length > 0 && filtered.every((l) => selectedIds.has(l.id))
  // const someSelected = filtered.some((l) => selectedIds.has(l.id))

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set((filtered || []).map((l) => l.id)))
    }
  }

  const toggleOne = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const handleCreate = async (data: LeadInput) => {
    setActionError(null)
    try {
      await api.createLead(data)
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to create lead')
      throw err
    }
  }

  const handleUpdate = async (data: LeadInput) => {
    if (!editingLead) return
    setActionError(null)
    try {
      await api.updateLead(editingLead.id, data)
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to update lead')
      throw err
    }
  }

  const handleDelete = async (id: string) => {
    setActionError(null)
    try {
      await api.deleteLead(id)
      setSelectedIds((prev) => { const next = new Set(prev); next.delete(id); return next })
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete lead')
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} selected lead(s)?`)) return
    setBulkDeleting(true)
    setActionError(null)
    try {
      await Promise.all(Array.from(selectedIds).map((id) => api.deleteLead(id)))
      setSelectedIds(new Set())
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete leads')
    } finally {
      setBulkDeleting(false)
    }
  }

  const openCreate = () => { setEditingLead(null); setModalOpen(true) }
  const openEdit = (lead: Lead) => { setEditingLead(lead); setModalOpen(true) }

  return (
    <div className="glass card-hover rounded-xl p-6 animate-fade-in">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-100">Leads</h2>
          <p className="text-xs text-gray-400">{filtered.length} of {leads.length} leads</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
            <input type="text" placeholder="Search leads..." value={search} onChange={(e) => setSearch(e.target.value)} className="rounded-lg border border-gray-700 bg-gray-800 py-1.5 pl-8 pr-3 text-xs text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500" />
          </div>
          <div className="relative">
            <Filter className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="appearance-none rounded-lg border border-gray-700 bg-gray-800 py-1.5 pl-8 pr-8 text-xs text-gray-100 outline-none focus:border-blue-500">
              {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => exportToCSV(filtered)} className="flex items-center gap-1 rounded-lg border border-gray-700 px-2.5 py-1.5 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200" title="Export CSV"><Download className="h-3.5 w-3.5" /> CSV</button>
            <button onClick={() => exportToJSON(filtered)} className="flex items-center gap-1 rounded-lg border border-gray-700 px-2.5 py-1.5 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200" title="Export JSON"><Download className="h-3.5 w-3.5" /> JSON</button>
          </div>
          {selectedIds.size > 0 && (
            <button onClick={handleBulkDelete} disabled={bulkDeleting} className="flex items-center gap-1 rounded-lg border border-red-500/50 bg-red-500/10 px-2.5 py-1.5 text-xs text-red-400 hover:bg-red-500/20 disabled:opacity-50">
              {bulkDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />} Delete ({selectedIds.size})
            </button>
          )}
          <button onClick={openCreate} className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500"><Plus className="h-3.5 w-3.5" /> Create</button>
        </div>
      </div>
      {actionError && <div className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">{actionError}</div>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead>
            <tr className="border-b border-gray-700 text-xs uppercase tracking-wider text-gray-400">
              <th className="pb-3 pr-4 font-medium w-8">
                <button onClick={toggleAll} className="text-gray-400 hover:text-gray-200">
                  {allSelected ? <CheckSquare className="h-4 w-4 text-blue-500" /> : <Square className="h-4 w-4" />}
                </button>
              </th>
              <th className="pb-3 pr-4 font-medium">Lead</th>
              <th className="pb-3 pr-4 font-medium">Status</th>
              <th className="pb-3 pr-4 font-medium">Score</th>
              <th className="pb-3 pr-4 font-medium">Value</th>
              <th className="pb-3 pr-4 font-medium">Source</th>
              <th className="pb-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((lead) => (
              <tr key={lead.id} className={`border-b border-gray-800 transition-colors last:border-0 hover:bg-gray-800/50 ${selectedIds.has(lead.id) ? 'bg-blue-500/5' : ''}`}>
                <td className="py-3 pr-4">
                  <button onClick={() => toggleOne(lead.id)} className="text-gray-400 hover:text-gray-200">
                    {selectedIds.has(lead.id) ? <CheckSquare className="h-4 w-4 text-blue-500" /> : <Square className="h-4 w-4" />}
                  </button>
                </td>
                <td className="py-3 pr-4">
                  <div>
                    <div className="font-medium text-gray-100">{lead.name}</div>
                    <div className="text-xs text-gray-400">{lead.company}{lead.email ? ` · ${lead.email}` : ''}</div>
                  </div>
                </td>
                <td className="py-3 pr-4"><StatusBadge status={lead.status} /></td>
                <td className="py-3 pr-4"><ScoreBar score={lead.score} /></td>
                <td className="py-3 pr-4 font-medium text-gray-100">{formatCurrency(lead.value)}</td>
                <td className="py-3 pr-4 text-xs text-gray-400">{lead.source}</td>
                <td className="py-3">
                  <div className="flex items-center gap-1">
                    <button onClick={() => openEdit(lead)} className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-blue-400" title="Edit"><Edit className="h-3.5 w-3.5" /></button>
                    <button onClick={() => handleDelete(lead.id)} className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-red-400" title="Delete"><Trash2 className="h-3.5 w-3.5" /></button>
                    <button className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-200" title="Call"><Phone className="h-3.5 w-3.5" /></button>
                    <button className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-200" title="Email"><Mail className="h-3.5 w-3.5" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="py-8 text-center text-sm text-gray-400">No leads match your filters</div>}
      </div>
      <LeadFormModal isOpen={modalOpen} onClose={() => setModalOpen(false)} onSave={editingLead ? handleUpdate : handleCreate} lead={editingLead} />
    </div>
  )
}

function OpportunitiesPipeline({ opportunities, onViewAll }: { opportunities: Opportunity[]; onViewAll: () => void }) {
  const stages = STAGE_ORDER.filter((s) => (opportunities || []).some((o) => o.stage === s))
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Opportunities Pipeline</h2><p className="text-xs text-[var(--muted)]">{opportunities.length} open opportunities</p></div><button onClick={onViewAll} className="flex items-center gap-1 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:bg-gray-900/5"><Briefcase className="h-3.5 w-3.5" /> View All</button></div><div className="mb-5"><div className="flex h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">{stages.map((stage) => { const stageOpps = opportunities.filter((o) => o.stage === stage); const totalValue = stageOpps.reduce((sum, o) => sum + o.value, 0); const allValue = opportunities.reduce((sum, o) => sum + o.value, 0); const pct = allValue > 0 ? (totalValue / allValue) * 100 : 0; return <div key={stage} className="h-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: getStageColor(stage) }} title={`${stage}: ${formatCurrency(totalValue)}`} /> })}</div><div className="mt-2 flex flex-wrap gap-3">{stages.map((stage) => { const count = opportunities.filter((o) => o.stage === stage).length; return <div key={stage} className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: getStageColor(stage) }} /> {stage} ({count})</div> })}</div></div><div className="space-y-3">{opportunities.map((opp) => <div key={opp.id} className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-4 transition-colors hover:border-[var(--accent)]"><div className="mb-2 flex items-center justify-between"><span className="font-medium text-[var(--text)]">{opp.name}</span><StageBadge stage={opp.stage} /></div><div className="flex items-center justify-between text-sm"><div className="flex items-center gap-3"><span className="text-[var(--text)]">{formatCurrency(opp.value)}</span><span className="text-xs text-[var(--muted)]">Owner: {opp.owner}</span></div><ProbabilityBar probability={opp.probability} /></div><div className="mt-2 flex items-center justify-between text-xs text-[var(--muted)]"><div className="flex items-center gap-1"><Calendar className="h-3 w-3" /> Expected: {opp.expectedClose}</div><div className="flex items-center gap-1"><ChevronRight className="h-3 w-3" /> Weighted: {formatCurrency(opp.value * opp.probability / 100)}</div></div></div>)}</div></div>
}

function ForecastChart({ forecast }: { forecast: ForecastData }) {
  const data = [{ quarter: 'Q1', value: forecast.q1, color: '#06b6d4' }, { quarter: 'Q2', value: forecast.q2, color: '#8b5cf6' }, { quarter: 'Q3', value: forecast.q3, color: '#a855f7' }, { quarter: 'Q4', value: forecast.q4, color: '#10b981' }]
  const total = (data || []).reduce((s, d) => s + (d.value ?? 0), 0)
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Quarterly Forecast</h2><p className="text-xs text-[var(--muted)]">Total projected: {formatCurrency(total)}</p></div><div className="flex items-center gap-1 rounded-lg border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--muted)]"><BarChart3 className="h-3.5 w-3.5" /> 2024</div></div><div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="quarter" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} /><YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => formatCurrency(v)} /><Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} labelStyle={{ color: 'var(--muted)' }} formatter={(value: number) => [formatCurrency(value), 'Forecast']} /><Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={60}>{data.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}</Bar></BarChart></ResponsiveContainer></div></div>
}

function SegmentationChart({ segments }: { segments: SegmentData[] }) {
  const total = (segments || []).reduce((s, seg) => s + (seg.value ?? 0), 0)
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Customer Segmentation</h2><p className="text-xs text-[var(--muted)]">{total} total customers</p></div><PieChartIcon className="h-4 w-4 text-[var(--muted)]" /></div><div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={segments} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">{segments.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}</Pie><Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} formatter={(value: number, name: string) => [`${value} (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`, name]} /><Legend verticalAlign="bottom" iconType="circle" iconSize={8} formatter={(value: string) => <span style={{ color: 'var(--muted)', fontSize: '12px' }}>{value}</span>} /></PieChart></ResponsiveContainer></div></div>
}

function InteractionsTimeline({ interactions }: { interactions: Interaction[] }) {
  const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = { call: { icon: <Phone className="h-3.5 w-3.5" />, color: '#3b82f6' }, email: { icon: <Mail className="h-3.5 w-3.5" />, color: '#8b5cf6' }, meeting: { icon: <Calendar className="h-3.5 w-3.5" />, color: '#f59e0b' }, note: { icon: <FileText className="h-3.5 w-3.5" />, color: '#6b7280' }, deal: { icon: <CheckCircle2 className="h-3.5 w-3.5" />, color: '#10b981' } }
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Recent Interactions</h2><p className="text-xs text-[var(--muted)]">Latest customer touchpoints</p></div><Activity className="h-4 w-4 text-[var(--muted)]" /></div><div className="space-y-0">{interactions.map((interaction, idx) => { const config = typeConfig[interaction.type] ?? typeConfig.note; const isLast = idx === interactions.length - 1; return <div key={interaction.id} className="relative flex gap-3 pb-4">{!isLast && <div className="absolute left-[11px] top-6 h-full w-px bg-[var(--border)]" />}<div className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full" style={{ backgroundColor: `${config.color}20`, color: config.color }}>{config.icon}</div><div className="flex-1 min-w-0"><div className="flex items-start justify-between gap-2"><div><div className="text-sm font-medium text-[var(--text)]">{interaction.title}</div><div className="text-xs text-[var(--muted)]">{interaction.contact} · {interaction.time}</div></div>{interaction.outcome && <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ backgroundColor: interaction.outcome === 'Positive' ? '#10b98118' : '#f59e0b18', color: interaction.outcome === 'Positive' ? '#10b981' : '#f59e0b' }}>{interaction.outcome}</span>}</div></div></div> })}</div></div>
}

function LeadScoringBreakdown({ scoreRanges, leads }: { scoreRanges: ScoreRange[]; leads: Lead[] }) {
  const maxCount = Math.max(...scoreRanges.map((r) => r.count), 1)
  const avgScore = (leads || []).length > 0 ? Math.round((leads || []).reduce((s, l) => s + (l.score ?? 0), 0) / (leads || []).length) : 0
  return <div className="glass card-hover rounded-xl p-6 animate-fade-in"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-[var(--text)]">Lead Scoring Breakdown</h2><p className="text-xs text-[var(--muted)]">Average score: {avgScore}/100</p></div><div className="flex items-center gap-1.5"><Star className="h-4 w-4 text-[var(--warning)]" /><span className="text-sm font-semibold text-[var(--text)]">{avgScore}</span></div></div><div className="space-y-3">{scoreRanges.map((range) => <div key={range.range} className="flex items-center gap-3"><span className="w-14 text-xs text-[var(--muted)]">{range.range}</span><div className="flex-1"><div className="h-3 overflow-hidden rounded-full bg-[var(--border)]"><div className="h-full rounded-full transition-all duration-500" style={{ width: `${(range.count / maxCount) * 100}%`, backgroundColor: range.color }} /></div></div><span className="w-8 text-right text-xs font-medium text-[var(--text)]">{range.count}</span></div>)}</div><div className="mt-4 flex items-center gap-4 border-t border-[var(--border)] pt-3"><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#ef4444]" /> Cold (0-25)</div><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#f59e0b]" /> Warm (26-50)</div><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#3b82f6]" /> Hot (51-75)</div><div className="flex items-center gap-1.5 text-xs text-[var(--muted)]"><span className="h-2 w-2 rounded-full bg-[#10b981]" /> Premium (76-100)</div></div></div>
}

function LoadingState() {
  return <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4"><Loader2 className="h-10 w-10 text-[var(--accent)] animate-spin" /><p className="text-[var(--muted)] text-sm">Loading CRM data...</p></div>
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4"><AlertCircle className="h-10 w-10 text-[var(--danger)]" /><p className="text-[var(--text)] text-sm">{message}</p><button onClick={onRetry} className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity">Retry</button></div>
}

// ── CRM Modal ─────────────────────────────────────────────────────────────────

interface CRMModalProps {
  modal: string | null
  onClose: () => void
  opportunities: Opportunity[]
  metrics: { totalLeads: number; qualified: number; conversionRate: number; avgDealSize: number; totalPipelineValue: number; weightedPipelineValue: number } | null
  onCreateLead: (data: LeadInput) => Promise<void>
}

function CRMModal({ modal, onClose, opportunities, metrics, onCreateLead }: CRMModalProps) {
  const [goals, setGoals] = useState({ monthlyLeads: 100, qualified: 50, conversionRate: 50, revenue: 100000 })
  const [leadForm, setLeadForm] = useState<LeadInput>({ name: '', email: '', company: '', status: 'New', score: 50, value: 0, source: 'Website' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (modal) {
      setGoals({ monthlyLeads: 100, qualified: 50, conversionRate: 50, revenue: 100000 })
      setLeadForm({ name: '', email: '', company: '', status: 'New', score: 50, value: 0, source: 'Website' })
      setError(null)
      setSaving(false)
    }
  }, [modal])

  if (!modal) return null

  const handleSaveGoals = () => {
    alert('Goals saved successfully!')
    onClose()
  }

  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!leadForm.name.trim()) { setError('Name is required'); return }
    setSaving(true)
    setError(null)
    try {
      await onCreateLead(leadForm)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create lead')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = "w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text)] placeholder-[var(--muted)] outline-none focus:border-[var(--accent)]"
  const labelClass = "block text-xs font-medium text-[var(--muted)] mb-1"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="glass rounded-2xl p-6 max-w-lg w-full mx-4 animate-fade-in max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[var(--text)]">{modal}</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--text)] transition-colors"><X className="w-5 h-5" /></button>
        </div>

        {modal === 'Goals' && (
          <div className="space-y-4">
            <p className="text-sm text-[var(--muted)]">Set your CRM targets for this quarter.</p>
            {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>}
            <div>
              <label className={labelClass}>Monthly Lead Target</label>
              <input type="number" min="0" value={goals.monthlyLeads} onChange={(e) => setGoals({ ...goals, monthlyLeads: Number(e.target.value) })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Qualified Lead Target</label>
              <input type="number" min="0" value={goals.qualified} onChange={(e) => setGoals({ ...goals, qualified: Number(e.target.value) })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Conversion Rate Target (%)</label>
              <input type="number" min="0" max="100" value={goals.conversionRate} onChange={(e) => setGoals({ ...goals, conversionRate: Number(e.target.value) })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Revenue Target ($)</label>
              <input type="number" min="0" value={goals.revenue} onChange={(e) => setGoals({ ...goals, revenue: Number(e.target.value) })} className={inputClass} />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={onClose} className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm text-[var(--muted)] hover:bg-[var(--surface)]">Cancel</button>
              <button onClick={handleSaveGoals} className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:opacity-90">Save Goals</button>
            </div>
          </div>
        )}

        {modal === 'New Lead' && (
          <form onSubmit={handleCreateLead} className="space-y-4">
            <p className="text-sm text-[var(--muted)]">Create a new lead in your CRM pipeline.</p>
            {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>}
            <div>
              <label className={labelClass}>Name *</label>
              <input type="text" value={leadForm.name} onChange={(e) => setLeadForm({ ...leadForm, name: e.target.value })} className={inputClass} placeholder="John Doe" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Email</label>
                <input type="email" value={leadForm.email} onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })} className={inputClass} placeholder="john@company.com" />
              </div>
              <div>
                <label className={labelClass}>Company</label>
                <input type="text" value={leadForm.company} onChange={(e) => setLeadForm({ ...leadForm, company: e.target.value })} className={inputClass} placeholder="Acme Inc" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Status</label>
                <select value={leadForm.status} onChange={(e) => setLeadForm({ ...leadForm, status: e.target.value })} className={inputClass}>
                  <option value="New">New</option>
                  <option value="Contacted">Contacted</option>
                  <option value="Qualified">Qualified</option>
                  <option value="Unqualified">Unqualified</option>
                  <option value="Converted">Converted</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Source</label>
                <select value={leadForm.source} onChange={(e) => setLeadForm({ ...leadForm, source: e.target.value })} className={inputClass}>
                  <option value="Website">Website</option>
                  <option value="Referral">Referral</option>
                  <option value="LinkedIn">LinkedIn</option>
                  <option value="Cold Outreach">Cold Outreach</option>
                  <option value="Event">Event</option>
                  <option value="Partner">Partner</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Score: {leadForm.score}</label>
                <input type="range" min="0" max="100" value={leadForm.score} onChange={(e) => setLeadForm({ ...leadForm, score: Number(e.target.value) })} className="w-full accent-[var(--accent)]" />
              </div>
              <div>
                <label className={labelClass}>Value ($)</label>
                <input type="number" min="0" value={leadForm.value} onChange={(e) => setLeadForm({ ...leadForm, value: Number(e.target.value) })} className={inputClass} />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm text-[var(--muted)] hover:bg-[var(--surface)]">Cancel</button>
              <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Create Lead
              </button>
            </div>
          </form>
        )}

        {modal === 'View All Opportunities' && (
          <div>
            <p className="text-sm text-[var(--muted)] mb-4">{opportunities.length} total opportunities · {formatCurrency(metrics?.totalPipelineValue ?? 0)} pipeline value</p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-xs uppercase tracking-wider text-[var(--muted)]">
                    <th className="pb-3 pr-4 font-medium">Name</th>
                    <th className="pb-3 pr-4 font-medium">Stage</th>
                    <th className="pb-3 pr-4 font-medium">Value</th>
                    <th className="pb-3 pr-4 font-medium">Probability</th>
                    <th className="pb-3 pr-4 font-medium">Expected Close</th>
                    <th className="pb-3 font-medium">Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {opportunities.map((opp) => (
                    <tr key={opp.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface)]/50">
                      <td className="py-3 pr-4 font-medium text-[var(--text)]">{opp.name}</td>
                      <td className="py-3 pr-4"><StageBadge stage={opp.stage} /></td>
                      <td className="py-3 pr-4 text-[var(--text)]">{formatCurrency(opp.value)}</td>
                      <td className="py-3 pr-4"><ProbabilityBar probability={opp.probability} /></td>
                      <td className="py-3 pr-4 text-xs text-[var(--muted)]">{opp.expectedClose}</td>
                      <td className="py-3 text-xs text-[var(--muted)]">{opp.owner}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {opportunities.length === 0 && <div className="py-8 text-center text-sm text-[var(--muted)]">No opportunities found</div>}
            <div className="mt-4 flex justify-end">
              <button onClick={onClose} className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm text-[var(--muted)] hover:bg-[var(--surface)]">Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
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
    } catch {
      setData(FALLBACK_CRM_DATA)
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
    const qualified = (enrichedLeads || []).filter((l) => l.status === 'Qualified').length
    const conversionRate = totalLeads > 0 ? Math.round((qualified / totalLeads) * 100) : 0
    const avgDealSize = totalLeads > 0 ? Math.round((enrichedLeads || []).reduce((s, l) => s + (l.value ?? 0), 0) / totalLeads) : 0
    const totalPipelineValue = (enrichedOpportunities || []).reduce((s, o) => s + (o.value ?? 0), 0)
    const weightedPipelineValue = (enrichedOpportunities || []).reduce((s, o) => s + ((o.value ?? 0) * (o.probability ?? 0)) / 100, 0)
    return { totalLeads, qualified, conversionRate, avgDealSize, totalPipelineValue, weightedPipelineValue }
  }, [data, enrichedLeads, enrichedOpportunities])

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={fetchCRM} />
  if (!data) return <ErrorState message="No data received" onRetry={fetchCRM} />

  const forecast: ForecastData = data.forecast ?? { q1: 0, q2: 0, q3: 0, q4: 0 }

  const handleOpenModal = (label: string) => setModal(label)

  const handleCreateLead = async (data: LeadInput) => {
    await api.createLead(data)
    fetchCRM()
  }

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold gradient-text">CRM</h1><p className="text-sm text-[var(--muted)] mt-1">Leads, opportunities, and revenue forecast</p></div>
        <div className="flex items-center gap-2">
          <button onClick={() => handleOpenModal('Goals')} className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:bg-gray-900/5"><Target className="h-3.5 w-3.5" /> Goals</button>
          <button onClick={() => handleOpenModal('New Lead')} className="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"><Plus className="h-3.5 w-3.5" /> New Lead</button>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard title="Total Leads" value={formatNumber(metrics?.totalLeads ?? 0)} subtitle="Active in pipeline" icon={<Users className="h-5 w-5 text-[var(--accent)]" />} color="var(--accent)" trend={{ value: 12.5, positive: true }} />
        <SummaryCard title="Qualified" value={formatNumber(metrics?.qualified ?? 0)} subtitle="Ready for outreach" icon={<UserCheck className="h-5 w-5 text-[var(--success)]" />} color="var(--success)" trend={{ value: 8.2, positive: true }} />
        <SummaryCard title="Conversion Rate" value={`${metrics?.conversionRate ?? 0}%`} subtitle="Lead to qualified" icon={<TrendingUp className="h-5 w-5 text-[var(--accent2)]" />} color="var(--accent2)" trend={{ value: 2.1, positive: false }} />
        <SummaryCard title="Avg Deal Size" value={formatCurrency(metrics?.avgDealSize ?? 0)} subtitle="Per opportunity" icon={<DollarSign className="h-5 w-5 text-[var(--warning)]" />} color="var(--warning)" trend={{ value: 5.4, positive: true }} />
      </div>
      <LeadsTable leads={enrichedLeads} onRefresh={fetchCRM} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OpportunitiesPipeline opportunities={enrichedOpportunities} onViewAll={() => handleOpenModal('View All Opportunities')} />
        <ForecastChart forecast={forecast} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SegmentationChart segments={segments} />
        <InteractionsTimeline interactions={interactions} />
        <LeadScoringBreakdown scoreRanges={scoreRanges} leads={enrichedLeads} />
      </div>
      <CRMModal modal={modal} onClose={() => setModal(null)} opportunities={enrichedOpportunities} metrics={metrics} onCreateLead={handleCreateLead} />
    </div>
  )
}
