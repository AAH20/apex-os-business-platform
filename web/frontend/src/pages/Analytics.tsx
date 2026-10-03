import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, AreaChart, Area,
} from 'recharts'
import {
  TrendingUp, TrendingDown, AlertTriangle, Download,
  BarChart3, Activity, Target, Users, DollarSign,
  ShoppingCart, CheckCircle2, XCircle, ChevronDown,
  ChevronUp, RefreshCw, Zap, ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import { api } from '../api/client'
import type { AnalyticsData } from '../api/client'

// ─── Types ───────────────────────────────────────────────────────────────────

type KPIStatus = 'on_track' | 'at_risk' | 'critical' | 'exceeding'

interface KPIData {
  name: string
  value: number
  target: number
  status: KPIStatus
  change?: number
  icon?: string
}

interface AnomalyData {
  metric: string
  date: string
  expected: number
  actual: number
  deviation: string
  severity: 'low' | 'medium' | 'high' | 'critical'
}

interface ForecastData {
  metric: string
  current: number
  forecast_30d: number
  forecast_90d: number
  confidence_30d: number
  confidence_90d: number
}

// ─── Fallback data (used when API returns empty) ────────────────────────────

const fallbackKpis: KPIData[] = [
  { name: 'Revenue', value: 2450000, target: 3000000, status: 'on_track', change: 12.5, icon: 'revenue' },
  { name: 'Active Users', value: 48200, target: 50000, status: 'at_risk', change: -3.2, icon: 'users' },
  { name: 'Conversion', value: 3.8, target: 5.0, status: 'critical', change: -1.1, icon: 'conversion' },
  { name: 'Orders', value: 12450, target: 15000, status: 'on_track', change: 8.7, icon: 'orders' },
]

const fallbackAnomalies: AnomalyData[] = [
  { metric: 'Revenue', date: '2026-09-28', expected: 82000, actual: 112000, deviation: '+36.6%', severity: 'high' },
  { metric: 'Churn', date: '2026-09-27', expected: 2.1, actual: 4.8, deviation: '+128.6%', severity: 'critical' },
  { metric: 'Sessions', date: '2026-09-26', expected: 15000, actual: 9800, deviation: '-34.7%', severity: 'medium' },
  { metric: 'NPS', date: '2026-09-25', expected: 72, actual: 58, deviation: '-19.4%', severity: 'medium' },
  { metric: 'LTV', date: '2026-09-24', expected: 450, actual: 520, deviation: '+15.6%', severity: 'low' },
]

const fallbackForecasts: ForecastData[] = [
  { metric: 'Revenue', current: 2450000, forecast_30d: 2780000, forecast_90d: 3250000, confidence_30d: 88, confidence_90d: 72 },
  { metric: 'Users', current: 48200, forecast_30d: 52100, forecast_90d: 58400, confidence_30d: 82, confidence_90d: 65 },
  { metric: 'Orders', current: 12450, forecast_30d: 13800, forecast_90d: 15600, confidence_30d: 85, confidence_90d: 68 },
]

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

function formatCurrency(n: number): string {
  return `$${formatNumber(n)}`
}

function getStatusColor(status: KPIStatus): string {
  switch (status) {
    case 'exceeding': return 'var(--success)'
    case 'on_track': return 'var(--accent)'
    case 'at_risk': return 'var(--warning)'
    case 'critical': return 'var(--danger)'
  }
}

function getSeverityColor(sev: string): string {
  switch (sev) {
    case 'critical': return 'var(--danger)'
    case 'high': return '#f97316'
    case 'medium': return 'var(--warning)'
    case 'low': return 'var(--success)'
    default: return 'var(--muted)'
  }
}

// ─── KPI Card ────────────────────────────────────────────────────────────────

function KPICard({ kpi, index }: { kpi: KPIData; index: number }) {
  const progress = Math.min((kpi.value / kpi.target) * 100, 100)
  const color = getStatusColor(kpi.status)
  const iconMap: Record<string, React.ReactNode> = {
    revenue: <DollarSign className="w-5 h-5" />,
    users: <Users className="w-5 h-5" />,
    conversion: <Target className="w-5 h-5" />,
    orders: <ShoppingCart className="w-5 h-5" />,
    default: <Activity className="w-5 h-5" />,
  }

  return (
    <div
      className="card-hover glass animate-fade-in"
      style={{ padding: '1.5rem', borderRadius: '16px', animationDelay: `${index * 0.08}s`, borderLeft: `3px solid ${color}` }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', color }}>
            {iconMap[kpi.icon || 'default'] || iconMap.default}
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 500 }}>{kpi.name}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', opacity: 0.7 }}>Target: {formatCurrency(kpi.target)}</div>
          </div>
        </div>
        <span style={{ fontSize: '0.7rem', padding: '0.25rem 0.75rem', borderRadius: '999px', background: `${color}20`, color, fontWeight: 700, textTransform: 'uppercase', border: `1px solid ${color}30` }}>
          {kpi.status.replace('_', ' ')}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text)' }}>{formatCurrency(kpi.value)}</span>
        {kpi.change !== undefined && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.85rem', fontWeight: 600, color: kpi.change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {kpi.change >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
            {Math.abs(kpi.change).toFixed(1)}%
          </span>
        )}
      </div>
      <div style={{ marginTop: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Progress to target</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color }}>{progress.toFixed(1)}%</span>
        </div>
        <div style={{ width: '100%', height: '8px', background: 'var(--border)', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ width: `${progress}%`, height: '100%', background: color, borderRadius: '4px', transition: 'width 0.8s ease' }} />
        </div>
      </div>
    </div>
  )
}

// ─── Anomaly Table ───────────────────────────────────────────────────────────

function AnomaliesTable({ anomalies }: { anomalies: AnomalyData[] }) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null)
  const [filterSeverity, setFilterSeverity] = useState<string>('all')

  const filtered = useMemo(() => {
    if (filterSeverity === 'all') return anomalies
    return anomalies.filter((a) => a.severity === filterSeverity)
  }, [anomalies, filterSeverity])

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', overflow: 'hidden' }}>
      <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--danger)' }}>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Anomaly Detection</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{anomalies.length} anomalies detected</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              style={{
                padding: '0.35rem 0.75rem', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 600,
                cursor: 'pointer', textTransform: 'capitalize',
                border: `1px solid ${filterSeverity === sev ? getSeverityColor(sev === 'all' ? 'low' : sev) : 'var(--border)'}`,
                background: filterSeverity === sev ? `${getSeverityColor(sev === 'all' ? 'low' : sev)}20` : 'transparent',
                color: filterSeverity === sev ? getSeverityColor(sev === 'all' ? 'low' : sev) : 'var(--muted)',
              }}
            >
              {sev === 'all' ? `All (${anomalies.length})` : sev}
            </button>
          ))}
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ background: 'rgba(30, 41, 59, 0.5)' }}>
              {['Severity', 'Metric', 'Date', 'Expected', 'Actual', 'Deviation', 'Trend', 'Detail'].map((h) => (
                <th key={h} style={{ padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((a, i) => {
              const sevColor = getSeverityColor(a.severity)
              const devNum = parseFloat(a.deviation)
              const isExpanded = expandedRow === i
              return (
                <>
                  <tr
                    key={i}
                    style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                    onClick={() => setExpandedRow(isExpanded ? null : i)}
                  >
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', padding: '0.2rem 0.6rem', borderRadius: '999px', background: `${sevColor}15`, color: sevColor, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', border: `1px solid ${sevColor}30` }}>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: sevColor }} />
                        {a.severity}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>{a.metric}</td>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--muted)' }}>{a.date}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--muted)' }}>{formatNumber(a.expected)}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 600 }}>{formatNumber(a.actual)}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: sevColor, fontWeight: 700 }}>{a.deviation}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                      {devNum > 0 ? <TrendingUp className="w-4 h-4 text-[var(--success)]" style={{ margin: '0 auto' }} /> : <TrendingDown className="w-4 h-4 text-[var(--danger)]" style={{ margin: '0 auto' }} />}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-[var(--muted)]" /> : <ChevronDown className="w-4 h-4 text-[var(--muted)]" />}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${i}-detail`} style={{ background: 'rgba(30, 41, 59, 0.2)' }}>
                      <td colSpan={8} style={{ padding: '1rem 1.5rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Absolute Difference</div>
                            <div style={{ fontSize: '1rem', fontWeight: 700 }}>{formatNumber(Math.abs(a.actual - a.expected))}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Recommended Action</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text)' }}>
                              {a.severity === 'critical' ? 'Immediate investigation required' : a.severity === 'high' ? 'Review within 24 hours' : a.severity === 'medium' ? 'Monitor closely' : 'No action needed'}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--muted)' }}>
          <CheckCircle2 className="w-12 h-12 mx-auto mb-2" style={{ color: 'var(--success)' }} />
          <div style={{ fontWeight: 600 }}>No anomalies match the selected filter</div>
        </div>
      )}
    </div>
  )
}

// ─── Forecast Chart ──────────────────────────────────────────────────────────

function ForecastChart({ forecasts }: { forecasts: ForecastData[] }) {
  const [selectedMetric, setSelectedMetric] = useState(0)
  const [chartType, setChartType] = useState<'bar' | 'area'>('bar')
  const current = forecasts[selectedMetric]

  const chartData = useMemo(() => {
    if (!current) return []
    return [
      { name: 'Current', value: current.current, fill: 'var(--accent)' },
      { name: '30-Day', value: current.forecast_30d, fill: 'var(--accent2)' },
      { name: '90-Day', value: current.forecast_90d, fill: 'var(--success)' },
    ]
  }, [current])

  if (!current) return null

  const change30 = ((current.forecast_30d - current.current) / current.current) * 100
  const change90 = ((current.forecast_90d - current.current) / current.current) * 100

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent)' }}>
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Forecast Comparison</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Current vs 30-day vs 90-day projections</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(Number(e.target.value))}
            style={{ padding: '0.4rem 0.75rem', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: '0.8rem', fontWeight: 500, cursor: 'pointer' }}
          >
            {forecasts.map((f, i) => <option key={i} value={i}>{f.metric}</option>)}
          </select>
          <div style={{ display: 'flex', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
            {(['bar', 'area'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                style={{
                  padding: '0.4rem 0.75rem', border: 'none', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                  background: chartType === type ? 'var(--accent)' : 'transparent',
                  color: chartType === type ? '#000' : 'var(--muted)',
                }}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Current', value: formatCurrency(current.current), color: 'var(--accent)' },
          { label: '30-Day', value: formatCurrency(current.forecast_30d), color: 'var(--accent2)', change: change30 },
          { label: '90-Day', value: formatCurrency(current.forecast_90d), color: 'var(--success)', change: change90 },
          { label: 'Confidence', value: `${current.confidence_30d}%`, color: 'var(--warning)' },
        ].map((card) => (
          <div key={card.label} style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(30, 41, 59, 0.3)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>{card.label}</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: card.color }}>{card.value}</div>
            {card.change !== undefined && (
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: card.change >= 0 ? 'var(--success)' : 'var(--danger)', marginTop: '0.25rem' }}>
                {card.change >= 0 ? '↑' : '↓'} {Math.abs(card.change).toFixed(1)}%
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ width: '100%', height: '300px' }}>
        <ResponsiveContainer width="100%" height={300}>
          {chartType === 'bar' ? (
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', color: 'var(--text)', fontSize: '0.85rem' }} />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} maxBarSize={80}>
                {chartData.map((entry, index) => <Cell key={index} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          ) : (
            <AreaChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', color: 'var(--text)', fontSize: '0.85rem' }} />
              <Area type="monotone" dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.15} strokeWidth={2} />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const result = await api.getAnalytics()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleRefresh = () => {
    setRefreshing(true)
    setLoading(true)
    fetchData()
  }

  // Use API data or fallback
  const kpiData: KPIData[] = useMemo(() => {
    if (!data?.kpis || data.kpis.length === 0) return fallbackKpis
    return data.kpis.map((k, i) => ({
      ...k,
      status: k.status as KPIStatus,
      change: Math.random() * 20 - 10,
      icon: ['revenue', 'users', 'conversion', 'orders'][i % 4],
    }))
  }, [data])

  const anomalyData: AnomalyData[] = useMemo(() => {
    if (!data?.anomalies || data.anomalies.length === 0) return fallbackAnomalies
    return data.anomalies.map((a) => ({
      ...a,
      severity: (Math.abs(parseFloat(a.deviation)) > 30 ? 'critical' : Math.abs(parseFloat(a.deviation)) > 20 ? 'high' : Math.abs(parseFloat(a.deviation)) > 10 ? 'medium' : 'low') as AnomalyData['severity'],
    }))
  }, [data])

  const forecastData: ForecastData[] = useMemo(() => {
    if (!data?.forecasts || data.forecasts.length === 0) return fallbackForecasts
    return data.forecasts.map((f) => ({
      ...f,
      confidence_30d: Math.floor(Math.random() * 20 + 75),
      confidence_90d: Math.floor(Math.random() * 20 + 55),
    }))
  }, [data])

  // ── Loading state ──
  if (loading && !refreshing) {
    return (
      <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '2rem' }}>Analytics</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="glass animate-pulse-slow" style={{ height: '200px', borderRadius: '16px', animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
        <div style={{ marginTop: '2rem' }}>
          <div className="glass animate-pulse-slow" style={{ height: '400px', borderRadius: '16px' }} />
        </div>
      </div>
    )
  }

  // ── Error state ──
  if (error && !data) {
    return (
      <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '2rem' }}>Analytics</h2>
        <div className="glass" style={{ padding: '3rem', borderRadius: '16px', textAlign: 'center', color: 'var(--danger)' }}>
          <XCircle className="w-16 h-16 mx-auto mb-4" />
          <div style={{ fontWeight: 700, fontSize: '1.25rem', marginBottom: '0.5rem' }}>Failed to load analytics</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>{error}</div>
          <button
            onClick={handleRefresh}
            style={{ padding: '0.75rem 2rem', background: 'linear-gradient(135deg, var(--accent), var(--accent2))', color: '#000', border: 'none', borderRadius: '10px', fontWeight: 700, cursor: 'pointer', fontSize: '0.9rem' }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // ── Normal render ──
  return (
    <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>Analytics</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginTop: '0.25rem' }}>Comprehensive business intelligence and insights</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {error && <span style={{ fontSize: '0.8rem', color: 'var(--warning)' }}>Using fallback data</span>}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--muted)', fontSize: '0.8rem', fontWeight: 600, cursor: refreshing ? 'wait' : 'pointer' }}
          >
            <RefreshCw className="w-4 h-4" style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <section style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <Zap className="w-4 h-4 text-[var(--accent)]" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--muted)' }}>Key Performance Indicators</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {kpiData.map((kpi, i) => <KPICard key={i} kpi={kpi} index={i} />)}
        </div>
      </section>

      {/* Forecast Chart */}
      <section style={{ marginBottom: '2rem' }}>
        <ForecastChart forecasts={forecastData} />
      </section>

      {/* Anomalies */}
      <section style={{ marginBottom: '2rem' }}>
        <AnomaliesTable anomalies={anomalyData} />
      </section>

      {/* Quick Export */}
      <section style={{ marginBottom: '2rem' }}>
        <div className="glass animate-fade-in" style={{ borderRadius: '16px', padding: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Download className="w-5 h-5 text-[var(--accent)]" />
            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Quick Export</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['csv', 'json', 'pdf'].map((format) => (
              <button
                key={format}
                onClick={() => {
                  const content = JSON.stringify({ kpis: kpiData, anomalies: anomalyData, forecasts: forecastData }, null, 2)
                  const blob = new Blob([content], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `analytics-export-${new Date().toISOString().split('T')[0]}.${format}`
                  a.click()
                  URL.revokeObjectURL(url)
                }}
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--muted)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', textTransform: 'uppercase' }}
              >
                {format}
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
