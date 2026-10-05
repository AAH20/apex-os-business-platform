import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const fmtCurrency = (v: number) => v == null ? '$0.00' : v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `$${(v / 1_000).toFixed(1)}K` : `$${v.toFixed(2)}`
const fmtNumber = (v: number) => v == null ? '0' : v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `${(v / 1_000).toFixed(1)}K` : `${v.toLocaleString()}`

interface ChartDataPoint { name: string; value: number }

export function RevenueChart({ data }: { data: ChartDataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs><linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4} /><stop offset="100%" stopColor="#06b6d4" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
        <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => fmtCurrency(v)} />
        <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} labelStyle={{ color: 'var(--muted)' }} formatter={(v: number) => [fmtCurrency(v), 'Revenue']} />
        <Area type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2.5} fill="url(#revGrad)" dot={{ fill: '#06b6d4', strokeWidth: 0, r: 4 }} activeDot={{ r: 6, fill: '#06b6d4', stroke: '#07090e', strokeWidth: 2 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function UserGrowthChart({ data }: { data: ChartDataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
        <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} tickFormatter={(v: number) => fmtNumber(v)} />
        <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)' }} labelStyle={{ color: 'var(--muted)' }} formatter={(v: number) => [fmtNumber(v), 'Users']} />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={32}>
          {data.map((_, i) => <Cell key={i} fill={i === data.length - 1 ? '#a855f7' : '#a855f7' + Math.round(40 + (i / data.length) * 60).toString(16).padStart(2, '0')} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
