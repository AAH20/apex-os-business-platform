import { useState, useEffect, useMemo, useCallback } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, Wallet, Scale, BookOpen, ArrowUpRight, ArrowDownRight, Download, Search, Plus, Pencil, Trash2, X, CheckSquare, Square, CreditCard, Activity } from 'lucide-react'
import { api } from '../api/client'
import type { AccountingData } from '../api/client'

interface Account { id: string; name: string; type: string; balance: number }
interface JournalEntry { id: string; date: string; debit: string; credit: string; amount: number; description: string }
interface TrialBalance { debits: number; credits: number; balanced: boolean }

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
}
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
function getAccountTypeBadge(type: string): string {
  const badges: Record<string, string> = { asset: 'bg-cyan-500/10 text-cyan-400', liability: 'bg-purple-500/10 text-purple-400', equity: 'bg-emerald-500/10 text-emerald-400', revenue: 'bg-green-500/10 text-green-400', expense: 'bg-amber-500/10 text-amber-400' }
  return badges[type.toLowerCase()] || 'bg-slate-500/10 text-slate-400'
}
function getAccountTypeIcon(type: string) {
  const icons: Record<string, React.ReactNode> = { asset: <Wallet className="w-4 h-4" />, liability: <CreditCard className="w-4 h-4" />, equity: <Scale className="w-4 h-4" />, revenue: <TrendingUp className="w-4 h-4" />, expense: <BookOpen className="w-4 h-4" /> }
  return icons[type.toLowerCase()] || <BookOpen className="w-4 h-4" />
}
function getBalanceColor(balance: number): string {
  if (balance > 0) return 'text-emerald-400'
  if (balance < 0) return 'text-red-400'
  return 'text-slate-400'
}

function SummaryCard({ title, value, subtitle, icon, color }: { title: string; value: string; subtitle?: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="glass card-hover rounded-xl p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-[var(--muted)]">{title}</span>
        <div className="p-2 rounded-lg bg-[var(--surface)]">{icon}</div>
      </div>
      <div className={`text-2xl font-bold ${color} mb-1`}>{value}</div>
      {subtitle && <p className="text-xs text-[var(--muted)]">{subtitle}</p>}
    </div>
  )
}

function Dashboard({ accounts, journalEntries }: { accounts: Account[]; journalEntries: JournalEntry[] }) {
  const totalAssets = accounts.filter(a => a.type === 'asset').reduce((s, a) => s + a.balance, 0)
  const totalLiabilities = accounts.filter(a => a.type === 'liability').reduce((s, a) => s + a.balance, 0)
  const totalEquity = accounts.filter(a => a.type === 'equity').reduce((s, a) => s + a.balance, 0)
  const totalRevenue = accounts.filter(a => a.type === 'revenue').reduce((s, a) => s + a.balance, 0)
  const totalExpenses = accounts.filter(a => a.type === 'expense').reduce((s, a) => s + a.balance, 0)
  const netIncome = totalRevenue - totalExpenses

  const typeBreakdown = [
    { name: 'Assets', value: totalAssets, color: '#06b6d4' },
    { name: 'Liabilities', value: totalLiabilities, color: '#a855f7' },
    { name: 'Equity', value: totalEquity, color: '#10b981' },
    { name: 'Revenue', value: totalRevenue, color: '#22c55e' },
    { name: 'Expenses', value: totalExpenses, color: '#f59e0b' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <SummaryCard title="Total Assets" value={formatCurrency(totalAssets)} icon={<Wallet className="w-5 h-5 text-cyan-400" />} color="text-cyan-400" />
        <SummaryCard title="Total Liabilities" value={formatCurrency(totalLiabilities)} icon={<CreditCard className="w-5 h-5 text-purple-400" />} color="text-purple-400" />
        <SummaryCard title="Total Equity" value={formatCurrency(totalEquity)} icon={<Scale className="w-5 h-5 text-emerald-400" />} color="text-emerald-400" />
        <SummaryCard title="Revenue" value={formatCurrency(totalRevenue)} icon={<TrendingUp className="w-5 h-5 text-green-400" />} color="text-green-400" />
        <SummaryCard title="Net Income" value={formatCurrency(netIncome)} icon={<ArrowUpRight className="w-5 h-5 text-amber-400" />} color={netIncome >= 0 ? 'text-emerald-400' : 'text-red-400'} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-xl p-5">
          <h3 className="text-base font-semibold text-[var(--text)] mb-4">Account Type Breakdown</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={typeBreakdown} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {typeBreakdown.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="glass rounded-xl p-5">
          <h3 className="text-base font-semibold text-[var(--text)] mb-4">Recent Journal Entries</h3>
          <div className="space-y-2">
            {journalEntries.slice(0, 5).map(entry => (
              <div key={entry.id} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-[var(--surface)]/50 transition-colors">
                <div>
                  <div className="text-sm text-[var(--text)]">{entry.description}</div>
                  <div className="text-xs text-[var(--muted)]">{formatDate(entry.date)} · {entry.debit} → {entry.credit}</div>
                </div>
                <div className="text-sm font-mono font-medium text-[var(--text)]">{formatCurrency(entry.amount)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function ChartOfAccounts({ accounts, onExport, onCreate, onEdit, onDelete }: { accounts: Account[]; onExport: () => void; onCreate: () => void; onEdit: (account: Account) => void; onDelete: (id: string) => void }) {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)

  const accountTypes = ['all', 'asset', 'liability', 'equity', 'revenue', 'expense']
  const filteredAccounts = useMemo(() => {
    return accounts.filter(a => {
      const matchesSearch = a.name.toLowerCase().includes(search.toLowerCase()) || a.id.includes(search)
      const matchesType = typeFilter === 'all' || a.type === typeFilter
      return matchesSearch && matchesType
    })
  }, [accounts, search, typeFilter])

  const totalBalance = filteredAccounts.reduce((s, a) => s + a.balance, 0)
  const allSelected = filteredAccounts.length > 0 && filteredAccounts.every(a => selectedIds.has(a.id))

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedIds(next)
  }
  const toggleSelectAll = () => {
    setSelectedIds(allSelected ? new Set() : new Set(filteredAccounts.map(a => a.id)))
  }
  const handleBulkDelete = async () => {
    if (!confirm(`Delete ${selectedIds.size} accounts?`)) return
    try {
      await Promise.all(Array.from(selectedIds).map(id => api.deleteAccountingEntry(id)))
      setSelectedIds(new Set())
    } catch (err) { console.error(err) }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" />
          <input type="text" placeholder="Search accounts..." value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]" />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="px-3 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-sm text-[var(--text)]">
          {accountTypes.map(t => <option key={t} value={t}>{t === 'all' ? 'All Types' : t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
        <button onClick={onCreate} className="flex items-center gap-2 px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm font-medium hover:opacity-90"><Plus className="w-4 h-4" />Create</button>
        <button onClick={onExport} className="flex items-center gap-2 px-4 py-2 border border-[var(--border)] text-[var(--muted)] rounded-lg text-sm font-medium hover:bg-[var(--surface)]"><Download className="w-4 h-4" />Export</button>
        {selectedIds.size > 0 && <button onClick={handleBulkDelete} className="flex items-center gap-2 px-4 py-2 border border-red-500/50 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/10"><Trash2 className="w-4 h-4" />Delete ({selectedIds.size})</button>}
      </div>
      <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--surface)]">
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase w-10"><button onClick={toggleSelectAll}>{allSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}</button></th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Account</th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Type</th>
              <th className="text-right px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Balance</th>
              <th className="text-right px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAccounts.map(account => (
              <tr key={account.id} className="border-b border-[var(--border)]/50 hover:bg-[var(--surface)]/50 transition-colors">
                <td className="px-4 py-3"><button onClick={() => toggleSelect(account.id)}>{selectedIds.has(account.id) ? <CheckSquare className="w-4 h-4 text-[var(--accent)]" /> : <Square className="w-4 h-4 text-[var(--muted)]" />}</button></td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {getAccountTypeIcon(account.type)}
                    <div>
                      <div className="text-[var(--text)] font-medium">{account.name}</div>
                      <div className="text-xs text-[var(--muted)] font-mono">{account.id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded-full text-xs border ${getAccountTypeBadge(account.type)}`}>{account.type}</span></td>
                <td className={`px-4 py-3 text-right font-mono font-medium ${getBalanceColor(account.balance)}`}>{formatCurrency(account.balance)}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => onEdit(account)} className="p-1.5 text-[var(--muted)] hover:text-[var(--accent)] rounded transition-colors" title="Edit"><Pencil className="w-3.5 h-3.5" /></button>
                    <button onClick={() => setShowDeleteConfirm(account.id)} className="p-1.5 text-[var(--muted)] hover:text-red-400 rounded transition-colors" title="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-[var(--border)] bg-[var(--surface)]">
              <td colSpan={3} className="px-4 py-3 text-[var(--text)] font-semibold text-xs uppercase">Total ({filteredAccounts.length} accounts)</td>
              <td className={`px-4 py-3 text-right font-mono font-bold ${getBalanceColor(totalBalance)}`}>{formatCurrency(totalBalance)}</td>
              <td className="px-4 py-3"></td>
            </tr>
          </tfoot>
        </table>
      </div>
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowDeleteConfirm(null)}>
          <div className="glass rounded-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Delete Account?</h3>
            <p className="text-sm text-[var(--muted)] mb-4">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--muted)] text-sm">Cancel</button>
              <button onClick={() => { onDelete(showDeleteConfirm); setShowDeleteConfirm(null) }} className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function JournalEntries({ entries, onExport, onCreate, onEdit, onDelete, onBulkDelete }: { entries: JournalEntry[]; onExport: () => void; onCreate: () => void; onEdit: (entry: JournalEntry) => void; onDelete: (id: string) => void; onBulkDelete: () => void }) {
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)

  const filteredEntries = useMemo(() => {
    if (!search) return entries
    return entries.filter(e => e.description.toLowerCase().includes(search.toLowerCase()) || e.debit.includes(search) || e.credit.includes(search))
  }, [entries, search])

  const totalAmount = filteredEntries.reduce((s, e) => s + e.amount, 0)
  const allSelected = filteredEntries.length > 0 && filteredEntries.every(e => selectedIds.has(e.id))

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedIds(next)
  }
  const toggleSelectAll = () => {
    setSelectedIds(allSelected ? new Set() : new Set(filteredEntries.map(e => e.id)))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" />
          <input type="text" placeholder="Search entries..." value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]" />
        </div>
        <button onClick={onCreate} className="flex items-center gap-2 px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm font-medium hover:opacity-90"><Plus className="w-4 h-4" />Create</button>
        <button onClick={onExport} className="flex items-center gap-2 px-4 py-2 border border-[var(--border)] text-[var(--muted)] rounded-lg text-sm font-medium hover:bg-[var(--surface)]"><Download className="w-4 h-4" />Export</button>
        {selectedIds.size > 0 && <button onClick={onBulkDelete} className="flex items-center gap-2 px-4 py-2 border border-red-500/50 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/10"><Trash2 className="w-4 h-4" />Delete ({selectedIds.size})</button>}
      </div>
      <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--surface)]">
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase w-10"><button onClick={toggleSelectAll}>{allSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}</button></th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Date</th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Description</th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Debit</th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Credit</th>
              <th className="text-right px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Amount</th>
              <th className="text-right px-4 py-3 text-[var(--muted)] font-medium text-xs uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntries.map(entry => (
              <tr key={entry.id} className="border-b border-[var(--border)]/50 hover:bg-[var(--surface)]/50 transition-colors">
                <td className="px-4 py-3"><button onClick={() => toggleSelect(entry.id)}>{selectedIds.has(entry.id) ? <CheckSquare className="w-4 h-4 text-[var(--accent)]" /> : <Square className="w-4 h-4 text-[var(--muted)]" />}</button></td>
                <td className="px-4 py-3 text-[var(--text)] whitespace-nowrap">{formatDate(entry.date)}</td>
                <td className="px-4 py-3 text-[var(--text)] max-w-[200px] truncate" title={entry.description}>{entry.description}</td>
                <td className="px-4 py-3 text-cyan-400 font-mono text-xs">{entry.debit}</td>
                <td className="px-4 py-3 text-purple-400 font-mono text-xs">{entry.credit}</td>
                <td className="px-4 py-3 text-right font-mono font-medium text-[var(--text)]">{formatCurrency(entry.amount)}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => onEdit(entry)} className="p-1.5 text-[var(--muted)] hover:text-[var(--accent)] rounded transition-colors" title="Edit"><Pencil className="w-3.5 h-3.5" /></button>
                    <button onClick={() => setShowDeleteConfirm(entry.id)} className="p-1.5 text-[var(--muted)] hover:text-red-400 rounded transition-colors" title="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-[var(--border)] bg-[var(--surface)]">
              <td colSpan={5} className="px-4 py-3 text-[var(--text)] font-semibold text-xs uppercase">Total</td>
              <td className="px-4 py-3 text-right font-mono font-bold text-[var(--text)]">{formatCurrency(totalAmount)}</td>
              <td className="px-4 py-3"></td>
            </tr>
          </tfoot>
        </table>
      </div>
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowDeleteConfirm(null)}>
          <div className="glass rounded-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Delete Entry?</h3>
            <p className="text-sm text-[var(--muted)] mb-4">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--muted)] text-sm">Cancel</button>
              <button onClick={() => { onDelete(showDeleteConfirm); setShowDeleteConfirm(null) }} className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function TrialBalanceView({ trialBalance, accounts, onExport }: { trialBalance: TrialBalance; accounts: Account[]; onExport: () => void }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SummaryCard title="Total Debits" value={formatCurrency(trialBalance.debits)} icon={<ArrowUpRight className="w-5 h-5 text-cyan-400" />} color="text-cyan-400" />
        <SummaryCard title="Total Credits" value={formatCurrency(trialBalance.credits)} icon={<ArrowDownRight className="w-5 h-5 text-purple-400" />} color="text-purple-400" />
        <SummaryCard title="Status" value={trialBalance.balanced ? 'Balanced' : 'Unbalanced'} icon={<Scale className="w-5 h-5 text-emerald-400" />} color={trialBalance.balanced ? 'text-emerald-400' : 'text-red-400'} />
      </div>
      <div className="glass rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-[var(--text)]">Trial Balance</h3>
          <button onClick={onExport} className="flex items-center gap-2 px-3 py-1.5 border border-[var(--border)] text-[var(--muted)] rounded-lg text-xs font-medium hover:bg-[var(--surface)]"><Download className="w-3.5 h-3.5" />Export</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left px-3 py-2 text-[var(--muted)] font-medium text-xs uppercase">Account</th>
                <th className="text-right px-3 py-2 text-[var(--muted)] font-medium text-xs uppercase">Debit</th>
                <th className="text-right px-3 py-2 text-[var(--muted)] font-medium text-xs uppercase">Credit</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map(acc => (
                <tr key={acc.id} className="border-b border-[var(--border)]/50">
                  <td className="px-3 py-2 text-[var(--text)]">{acc.name}</td>
                  <td className="px-3 py-2 text-right font-mono text-cyan-400">{acc.balance >= 0 ? formatCurrency(acc.balance) : ''}</td>
                  <td className="px-3 py-2 text-right font-mono text-purple-400">{acc.balance < 0 ? formatCurrency(Math.abs(acc.balance)) : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function AnalyticsView({ accounts }: { accounts: Account[]; journalEntries?: JournalEntry[] }) {
  const revenue = accounts.filter(a => a.type === 'revenue').reduce((s, a) => s + a.balance, 0)
  const expenses = accounts.filter(a => a.type === 'expense').reduce((s, a) => s + a.balance, 0)
  const netIncome = revenue - expenses
  const profitMargin = revenue > 0 ? (netIncome / revenue) * 100 : 0

  const chartData = [
    { name: 'Revenue', value: revenue, color: '#22c55e' },
    { name: 'Expenses', value: expenses, color: '#f59e0b' },
    { name: 'Net Income', value: netIncome, color: netIncome >= 0 ? '#10b981' : '#ef4444' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SummaryCard title="Revenue" value={formatCurrency(revenue)} icon={<TrendingUp className="w-5 h-5 text-green-400" />} color="text-green-400" />
        <SummaryCard title="Expenses" value={formatCurrency(expenses)} icon={<ArrowDownRight className="w-5 h-5 text-amber-400" />} color="text-amber-400" />
        <SummaryCard title="Profit Margin" value={`${profitMargin.toFixed(1)}%`} icon={<Activity className="w-5 h-5 text-cyan-400" />} color={profitMargin >= 0 ? 'text-emerald-400' : 'text-red-400'} />
      </div>
      <div className="glass rounded-xl p-5">
        <h3 className="text-base font-semibold text-[var(--text)] mb-4">Revenue vs Expenses</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#0f1422', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }} />
              <Bar dataKey="value">
                {chartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default function Accounting() {
  const [data, setData] = useState<AccountingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'accounts' | 'journal' | 'trial' | 'analytics'>('dashboard')
  const [showForm, setShowForm] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | null>(null)
  const [editingEntry, setEditingEntry] = useState<JournalEntry | null>(null)
  const [accountForm, setAccountForm] = useState({ name: '', type: 'asset', balance: 0 })
  const [entryForm, setEntryForm] = useState({ date: '', description: '', debit: '', credit: '', amount: 0 })
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const result = await api.getAccounting()
      const normalized = Array.isArray(result) ? result[0] : result
      setData(normalized)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounting data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const accounts: Account[] = useMemo(() => {
    if (!data?.accounts || !Array.isArray(data.accounts)) return []
    return data.accounts
  }, [data])

  const journalEntries: JournalEntry[] = useMemo(() => {
    if (!data?.journal_entries || !Array.isArray(data.journal_entries)) return []
    return data.journal_entries
  }, [data])

  const trialBalance: TrialBalance = useMemo(() => {
    if (!data?.trial_balance) return { debits: 0, credits: 0, balanced: true }
    return data.trial_balance
  }, [data])

  const handleExportAccounts = () => {
    const csv = ['ID,Name,Type,Balance', ...accounts.map(a => `${a.id},${a.name},${a.type},${a.balance}`)].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'accounts.csv'; a.click(); URL.revokeObjectURL(url)
  }

  const handleExportJournal = () => {
    const csv = ['ID,Date,Description,Debit,Credit,Amount', ...journalEntries.map(e => `${e.id},${e.date},${e.description},${e.debit},${e.credit},${e.amount}`)].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'journal_entries.csv'; a.click(); URL.revokeObjectURL(url)
  }

  const handleExportTrialBalance = () => {
    const csv = ['Account,Debit,Credit', ...accounts.map(a => `${a.name},${a.balance >= 0 ? a.balance : ''},${a.balance < 0 ? Math.abs(a.balance) : ''}`)].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'trial_balance.csv'; a.click(); URL.revokeObjectURL(url)
  }

  const openCreateAccount = () => { setEditingAccount(null); setAccountForm({ name: '', type: 'asset', balance: 0 }); setShowForm(true) }
  const openEditAccount = (account: Account) => { setEditingAccount(account); setAccountForm({ name: account.name, type: account.type, balance: account.balance }); setShowForm(true) }

  const handleSaveAccount = async () => {
    try {
      if (editingAccount) {
        await api.updateAccountingEntry(editingAccount.id, accountForm as any)
      } else {
        await api.createAccountingEntry(accountForm as any)
      }
      setShowForm(false); fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to save account') }
  }

  const handleDeleteAccount = async (id: string) => {
    try {
      await api.deleteAccountingEntry(id)
      fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to delete account') }
  }

  const openCreateEntry = () => { setEditingEntry(null); setEntryForm({ date: new Date().toISOString().split('T')[0], description: '', debit: '', credit: '', amount: 0 }); setShowForm(true) }
  const openEditEntry = (entry: JournalEntry) => { setEditingEntry(entry); setEntryForm({ date: entry.date, description: entry.description, debit: entry.debit, credit: entry.credit, amount: entry.amount }); setShowForm(true) }

  const handleSaveEntry = async () => {
    try {
      if (editingEntry) {
        await api.updateAccountingEntry(editingEntry.id, entryForm as any)
      } else {
        await api.createAccountingEntry(entryForm as any)
      }
      setShowForm(false); fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to save entry') }
  }

  const handleDeleteEntry = async (id: string) => {
    try {
      await api.deleteAccountingEntry(id)
      fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to delete entry') }
  }

  const handleBulkDeleteEntries = async () => {
    try {
      await Promise.all(Array.from(selectedIds).map(id => api.deleteAccountingEntry(id)))
      setSelectedIds(new Set()); fetchData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to delete entries') }
  }

  if (loading) return <div className="animate-fade-in p-8"><div className="glass rounded-xl p-8 text-center text-[var(--muted)]">Loading accounting data...</div></div>
  if (error && !data) return <div className="animate-fade-in p-8"><div className="glass rounded-xl p-8 text-center text-red-400">{error}</div></div>

  const tabs = [
    { key: 'dashboard' as const, label: 'Dashboard', icon: <TrendingUp className="w-4 h-4" /> },
    { key: 'accounts' as const, label: 'Chart of Accounts', icon: <BookOpen className="w-4 h-4" /> },
    { key: 'journal' as const, label: 'Journal Entries', icon: <Scale className="w-4 h-4" /> },
    { key: 'trial' as const, label: 'Trial Balance', icon: <CheckSquare className="w-4 h-4" /> },
    { key: 'analytics' as const, label: 'Analytics', icon: <ArrowUpRight className="w-4 h-4" /> },
  ]

  return (
    <div className="animate-fade-in p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[var(--text)]">Accounting</h2>
        <p className="text-sm text-[var(--muted)] mt-1">Complete accounting management with dashboard, accounts, journal entries, and analytics</p>
      </div>
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${activeTab === tab.key ? 'bg-[var(--accent)] text-white' : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface)]'}`}>
            {tab.icon}{tab.label}
          </button>
        ))}
      </div>
      {activeTab === 'dashboard' && <Dashboard accounts={accounts} journalEntries={journalEntries} />}
      {activeTab === 'accounts' && <ChartOfAccounts accounts={accounts} onExport={handleExportAccounts} onCreate={openCreateAccount} onEdit={openEditAccount} onDelete={handleDeleteAccount} />}
      {activeTab === 'journal' && <JournalEntries entries={journalEntries} onExport={handleExportJournal} onCreate={openCreateEntry} onEdit={openEditEntry} onDelete={handleDeleteEntry} onBulkDelete={handleBulkDeleteEntries} />}
      {activeTab === 'trial' && <TrialBalanceView trialBalance={trialBalance} accounts={accounts} onExport={handleExportTrialBalance} />}
      {activeTab === 'analytics' && <AnalyticsView accounts={accounts} journalEntries={journalEntries} />}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowForm(false)}>
          <div className="glass rounded-2xl p-6 max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[var(--text)]">{editingAccount ? 'Edit Account' : editingEntry ? 'Edit Entry' : 'Create'}</h3>
              <button onClick={() => setShowForm(false)} className="p-1 rounded-lg hover:bg-[var(--surface)] text-[var(--muted)]"><X className="w-5 h-5" /></button>
            </div>
            {editingAccount || (!editingEntry && !editingAccount) ? (
              <div className="space-y-3">
                <div><label className="block text-sm text-[var(--muted)] mb-1">Name</label><input type="text" value={accountForm.name} onChange={e => setAccountForm({ ...accountForm, name: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
                <div><label className="block text-sm text-[var(--muted)] mb-1">Type</label><select value={accountForm.type} onChange={e => setAccountForm({ ...accountForm, type: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]"><option value="asset">Asset</option><option value="liability">Liability</option><option value="equity">Equity</option><option value="revenue">Revenue</option><option value="expense">Expense</option></select></div>
                <div><label className="block text-sm text-[var(--muted)] mb-1">Balance</label><input type="number" value={accountForm.balance} onChange={e => setAccountForm({ ...accountForm, balance: Number(e.target.value) })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
              </div>
            ) : (
              <div className="space-y-3">
                <div><label className="block text-sm text-[var(--muted)] mb-1">Date</label><input type="date" value={entryForm.date} onChange={e => setEntryForm({ ...entryForm, date: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
                <div><label className="block text-sm text-[var(--muted)] mb-1">Description</label><input type="text" value={entryForm.description} onChange={e => setEntryForm({ ...entryForm, description: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="block text-sm text-[var(--muted)] mb-1">Debit Account</label><input type="text" value={entryForm.debit} onChange={e => setEntryForm({ ...entryForm, debit: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
                  <div><label className="block text-sm text-[var(--muted)] mb-1">Credit Account</label><input type="text" value={entryForm.credit} onChange={e => setEntryForm({ ...entryForm, credit: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
                </div>
                <div><label className="block text-sm text-[var(--muted)] mb-1">Amount</label><input type="number" value={entryForm.amount} onChange={e => setEntryForm({ ...entryForm, amount: Number(e.target.value) })} className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-transparent text-[var(--text)]" /></div>
              </div>
            )}
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--muted)] text-sm">Cancel</button>
              <button onClick={editingAccount ? handleSaveAccount : editingEntry ? handleSaveEntry : handleSaveAccount} className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
