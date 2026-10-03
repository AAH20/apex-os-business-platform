import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  FunnelChart,
  Funnel,
  LabelList,
  Cell,
  AreaChart,
  Area,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Download,
  FileText,
  Filter,
  BarChart3,
  Activity,
  Target,
  Users,
  DollarSign,
  ShoppingCart,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Settings,
  Layers,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { api } from '../api/client'
import type { AnalyticsData } from '../api/client'

// ─── Types ───────────────────────────────────────────────────────────────────

type KPIStatus = 'on_track' | 'at_risk' | 'critical' | 'exceeding'
type Severity = 'low' | 'medium' | 'high' | 'critical'
type ExportFormat = 'csv' | 'json' | 'pdf'
type ReportSection = 'kpis' | 'anomalies' | 'forecasts' | 'cohorts' | 'funnel'

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
  severity: Severity
}

interface ForecastData {
  metric: string
  current: number
  forecast_30d: number
  forecast_90d: number
  confidence_30d: number
  confidence_90d: number
}

interface CohortData {
  cohort: string
  size: number
  retention: number[]
}

interface FunnelStage {
  stage: string
  value: number
  conversion: number
  dropoff: number
}

interface ReportConfig {
  name: string
  sections: ReportSection[]
  format: ExportFormat
  dateRange: string
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

function formatCurrency(n: number): string {
  return `$${formatNumber(n)}`
}

function formatPercent(n: number): string {
  return `${n.toFixed(1)}%`
}

function getStatusColor(status: KPIStatus): string {
  switch (status) {
    case 'exceeding':
      return 'var(--success)'
    case 'on_track':
      return 'var(--accent)'
    case 'at_risk':
      return 'var(--warning)'
    case 'critical':
      return 'var(--danger)'
    default:
      return 'var(--muted)'
  }
}

function getStatusLabel(status: KPIStatus): string {
  switch (status) {
    case 'exceeding':
      return 'Exceeding'
    case 'on_track':
      return 'On Track'
    case 'at_risk':
      return 'At Risk'
    case 'critical':
      return 'Critical'
    default:
      return 'Unknown'
  }
}

function getSeverityColor(severity: Severity): string {
  switch (severity) {
    case 'critical':
      return 'var(--danger)'
    case 'high':
      return '#f97316'
    case 'medium':
      return 'var(--warning)'
    case 'low':
      return 'var(--success)'
    default:
      return 'var(--muted)'
  }
}

function getSeverityLabel(severity: Severity): string {
  switch (severity) {
    case 'critical':
      return 'Critical'
    case 'high':
      return 'High'
    case 'medium':
      return 'Medium'
    case 'low':
      return 'Low'
    default:
      return 'Unknown'
  }
}

function getDeviationSeverity(deviation: string): Severity {
  const num = Math.abs(parseFloat(deviation))
  if (num > 30) return 'critical'
  if (num > 20) return 'high'
  if (num > 10) return 'medium'
  return 'low'
}

function getDeviationColor(deviation: string): string {
  const severity = getDeviationSeverity(deviation)
  return getSeverityColor(severity)
}

function getDeviationIcon(deviation: string): string {
  const num = parseFloat(deviation)
  if (isNaN(num)) return '→'
  if (num > 0) return '↑'
  return '↓'
}

function getHeatmapColor(value: number): string {
  if (value >= 80) return 'var(--success)'
  if (value >= 60) return '#22c55e'
  if (value >= 40) return 'var(--warning)'
  if (value >= 20) return '#f97316'
  return 'var(--danger)'
}

function getHeatmapOpacity(value: number): number {
  return 0.15 + (value / 100) * 0.65
}

// ─── KPI Card Component ──────────────────────────────────────────────────────

function KPICard({ kpi, index }: { kpi: KPIData; index: number }) {
  const progress = Math.min((kpi.value / kpi.target) * 100, 100)
  const color = getStatusColor(kpi.status)
  const isExceeding = kpi.status === 'exceeding'
  const isCritical = kpi.status === 'critical'

  const iconMap: Record<string, React.ReactNode> = {
    revenue: <DollarSign className="w-5 h-5" />,
    users: <Users className="w-5 h-5" />,
    conversion: <Target className="w-5 h-5" />,
    orders: <ShoppingCart className="w-5 h-5" />,
    default: <Activity className="w-5 h-5" />,
  }

  const icon = iconMap[kpi.icon || 'default'] || iconMap.default

  return (
    <div
      className="card-hover glass animate-fade-in"
      style={{
        padding: '1.5rem',
        borderRadius: '16px',
        animationDelay: `${index * 0.08}s`,
        borderLeft: `3px solid ${color}`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background glow */}
      <div
        style={{
          position: 'absolute',
          top: '-40px',
          right: '-40px',
          width: '120px',
          height: '120px',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${color}15 0%, transparent 70%)`,
          pointerEvents: 'none',
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: `${color}15`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color,
            }}
          >
            {icon}
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 500 }}>{kpi.name}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', opacity: 0.7 }}>Target: {formatCurrency(kpi.target)}</div>
          </div>
        </div>
        <span
          style={{
            fontSize: '0.7rem',
            padding: '0.25rem 0.75rem',
            borderRadius: '999px',
            background: `${color}20`,
            color,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            border: `1px solid ${color}30`,
          }}
        >
          {getStatusLabel(kpi.status)}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>
          {formatCurrency(kpi.value)}
        </span>
        {kpi.change !== undefined && (
          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.2rem',
              fontSize: '0.85rem',
              fontWeight: 600,
              color: kpi.change >= 0 ? 'var(--success)' : 'var(--danger)',
            }}
          >
            {kpi.change >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
            {Math.abs(kpi.change).toFixed(1)}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ marginTop: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Progress to target</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color }}>{progress.toFixed(1)}%</span>
        </div>
        <div
          style={{
            width: '100%',
            height: '8px',
            background: 'var(--border)',
            borderRadius: '4px',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <div
            style={{
              width: `${progress}%`,
              height: '100%',
              background: `linear-gradient(90deg, ${color}cc, ${color})`,
              borderRadius: '4px',
              transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              position: 'relative',
            }}
          >
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 0,
                bottom: 0,
                width: '20px',
                background: `linear-gradient(90deg, transparent, ${color}40)`,
              }}
            />
          </div>
          {/* Target marker */}
          <div
            style={{
              position: 'absolute',
              left: '100%',
              top: '-2px',
              width: '2px',
              height: '12px',
              background: 'var(--text)',
              opacity: 0.5,
            }}
          />
        </div>
      </div>

      {/* Status indicator */}
      {isCritical && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(239, 68, 68, 0.1)',
            borderRadius: '8px',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.8rem',
            color: 'var(--danger)',
          }}
        >
          <XCircle className="w-4 h-4" />
          Immediate attention required
        </div>
      )}
      {isExceeding && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(16, 185, 129, 0.1)',
            borderRadius: '8px',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.8rem',
            color: 'var(--success)',
          }}
        >
          <CheckCircle2 className="w-4 h-4" />
          Performing above target
        </div>
      )}
    </div>
  )
}

// ─── Anomaly Table Component ─────────────────────────────────────────────────

function AnomaliesTable({ anomalies }: { anomalies: AnomalyData[] }) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null)
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'all'>('all')

  const filtered = useMemo(() => {
    if (filterSeverity === 'all') return anomalies
    return anomalies.filter((a) => a.severity === filterSeverity)
  }, [anomalies, filterSeverity])

  const severityCounts = useMemo(() => {
    const counts: Record<Severity, number> = { low: 0, medium: 0, high: 0, critical: 0 }
    anomalies.forEach((a) => counts[a.severity]++)
    return counts
  }, [anomalies])

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', overflow: 'hidden' }}>
      <div
        style={{
          padding: '1.5rem',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--danger)',
            }}
          >
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Anomaly Detection</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
              {anomalies.length} anomalies detected across all metrics
            </p>
          </div>
        </div>

        {/* Severity filter pills */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {(['all', 'critical', 'high', 'medium', 'low'] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '999px',
                border: `1px solid ${filterSeverity === sev ? getSeverityColor(sev === 'all' ? 'low' : sev) : 'var(--border)'}`,
                background: filterSeverity === sev ? `${getSeverityColor(sev === 'all' ? 'low' : sev)}20` : 'transparent',
                color: filterSeverity === sev ? getSeverityColor(sev === 'all' ? 'low' : sev) : 'var(--muted)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
                transition: 'all 0.2s',
              }}
            >
              {sev === 'all' ? `All (${anomalies.length})` : `${getSeverityLabel(sev)} (${severityCounts[sev]})`}
            </button>
          ))}
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ background: 'rgba(30, 41, 59, 0.5)' }}>
              <th style={thStyle}>Severity</th>
              <th style={thStyle}>Metric</th>
              <th style={thStyle}>Date</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Expected</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Actual</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Deviation</th>
              <th style={{ ...thStyle, textAlign: 'center' }}>Trend</th>
              <th style={{ ...thStyle, textAlign: 'center' }}>Detail</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a, i) => {
              const devColor = getDeviationColor(a.deviation)
              const devIcon = getDeviationIcon(a.deviation)
              const sevColor = getSeverityColor(a.severity)
              const isExpanded = expandedRow === i
              const deviationNum = parseFloat(a.deviation)
              const barWidth = Math.min(Math.abs(deviationNum) * 2, 100)

              return (
                <>
                  <tr
                    key={i}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      transition: 'background 0.15s',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(30, 41, 59, 0.3)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    onClick={() => setExpandedRow(isExpanded ? null : i)}
                  >
                    <td style={tdStyle}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          padding: '0.2rem 0.6rem',
                          borderRadius: '999px',
                          background: `${sevColor}15`,
                          color: sevColor,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.03em',
                          border: `1px solid ${sevColor}30`,
                        }}
                      >
                        <span
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background: sevColor,
                          }}
                        />
                        {getSeverityLabel(a.severity)}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, fontWeight: 600 }}>{a.metric}</td>
                    <td style={{ ...tdStyle, color: 'var(--muted)' }}>{a.date}</td>
                    <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--muted)' }}>{formatNumber(a.expected)}</td>
                    <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>{formatNumber(a.actual)}</td>
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                        <div
                          style={{
                            width: '60px',
                            height: '4px',
                            background: 'var(--border)',
                            borderRadius: '2px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${barWidth}%`,
                              height: '100%',
                              background: devColor,
                              borderRadius: '2px',
                            }}
                          />
                        </div>
                        <span style={{ color: devColor, fontWeight: 700, minWidth: '50px' }}>
                          {devIcon} {a.deviation}
                        </span>
                      </div>
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      {deviationNum > 0 ? (
                        <TrendingUp className="w-4 h-4 text-[var(--success)]" style={{ margin: '0 auto' }} />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-[var(--danger)]" style={{ margin: '0 auto' }} />
                      )}
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-[var(--muted)]" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-[var(--muted)]" />
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${i}-detail`} style={{ background: 'rgba(30, 41, 59, 0.2)' }}>
                      <td colSpan={8} style={{ padding: '1rem 1.5rem' }}>
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                            gap: '1rem',
                          }}
                        >
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                              Absolute Difference
                            </div>
                            <div style={{ fontSize: '1rem', fontWeight: 700 }}>
                              {formatNumber(Math.abs(a.actual - a.expected))}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                              Deviation from Mean
                            </div>
                            <div style={{ fontSize: '1rem', fontWeight: 700, color: devColor }}>
                              {a.deviation}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                              Z-Score
                            </div>
                            <div style={{ fontSize: '1rem', fontWeight: 700 }}>
                              {(Math.abs(deviationNum) / 5).toFixed(2)}σ
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                              Recommended Action
                            </div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text)' }}>
                              {a.severity === 'critical'
                                ? 'Immediate investigation required'
                                : a.severity === 'high'
                                  ? 'Review within 24 hours'
                                  : a.severity === 'medium'
                                    ? 'Monitor closely'
                                    : 'No action needed'}
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

// ─── Forecast Chart Component ────────────────────────────────────────────────

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

  const areaData = useMemo(() => {
    if (!current) return []
    return [
      { period: 'Now', current: current.current, forecast_30d: current.current, forecast_90d: current.current },
      { period: '30d', current: current.current, forecast_30d: current.forecast_30d, forecast_90d: current.forecast_30d },
      { period: '60d', current: current.current, forecast_30d: current.forecast_30d, forecast_90d: (current.forecast_30d + current.forecast_90d) / 2 },
      { period: '90d', current: current.current, forecast_30d: current.forecast_30d, forecast_90d: current.forecast_90d },
    ]
  }, [current])

  if (!current) return null

  const change30 = ((current.forecast_30d - current.current) / current.current) * 100
  const change90 = ((current.forecast_90d - current.current) / current.current) * 100

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', padding: '1.5rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(6, 182, 212, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent)',
            }}
          >
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Forecast Comparison</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Current vs 30-day vs 90-day projections</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {/* Metric selector */}
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(Number(e.target.value))}
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--surface)',
              color: 'var(--text)',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {forecasts.map((f, i) => (
              <option key={i} value={i}>
                {f.metric}
              </option>
            ))}
          </select>

          {/* Chart type toggle */}
          <div style={{ display: 'flex', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
            <button
              onClick={() => setChartType('bar')}
              style={{
                padding: '0.4rem 0.75rem',
                background: chartType === 'bar' ? 'var(--accent)' : 'transparent',
                color: chartType === 'bar' ? '#000' : 'var(--muted)',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Bar
            </button>
            <button
              onClick={() => setChartType('area')}
              style={{
                padding: '0.4rem 0.75rem',
                background: chartType === 'area' ? 'var(--accent)' : 'transparent',
                color: chartType === 'area' ? '#000' : 'var(--muted)',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Area
            </button>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div
          style={{
            padding: '1rem',
            borderRadius: '12px',
            background: 'rgba(6, 182, 212, 0.08)',
            border: '1px solid rgba(6, 182, 212, 0.15)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Current</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent)' }}>{formatCurrency(current.current)}</div>
        </div>
        <div
          style={{
            padding: '1rem',
            borderRadius: '12px',
            background: 'rgba(168, 85, 247, 0.08)',
            border: '1px solid rgba(168, 85, 247, 0.15)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>30-Day Forecast</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent2)' }}>
            {formatCurrency(current.forecast_30d)}
          </div>
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: change30 >= 0 ? 'var(--success)' : 'var(--danger)',
              marginTop: '0.25rem',
            }}
          >
            {change30 >= 0 ? '↑' : '↓'} {Math.abs(change30).toFixed(1)}%
          </div>
        </div>
        <div
          style={{
            padding: '1rem',
            borderRadius: '12px',
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.15)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>90-Day Forecast</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--success)' }}>
            {formatCurrency(current.forecast_90d)}
          </div>
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: change90 >= 0 ? 'var(--success)' : 'var(--danger)',
              marginTop: '0.25rem',
            }}
          >
            {change90 >= 0 ? '↑' : '↓'} {Math.abs(change90).toFixed(1)}%
          </div>
        </div>
        <div
          style={{
            padding: '1rem',
            borderRadius: '12px',
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.15)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Confidence</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--warning)' }}>
            {current.confidence_30d}%
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '0.25rem' }}>30d confidence</div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ width: '100%', height: '300px' }}>
        <ResponsiveContainer width="100%" height={300}>
          {chartType === 'bar' ? (
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip
                contentStyle={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '12px',
                  color: 'var(--text)',
                  fontSize: '0.85rem',
                }}
                formatter={(value: number) => [formatCurrency(value), 'Value']}
              />
              <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} maxBarSize={80}>
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
                <LabelList dataKey="value" position="top" formatter={(v: number) => formatNumber(v)} style={{ fill: 'var(--text)', fontSize: '0.75rem', fontWeight: 600 }} />
              </Bar>
            </BarChart>
          ) : (
            <AreaChart data={areaData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="period" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickFormatter={(v) => formatNumber(v)} />
              <Tooltip
                contentStyle={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '12px',
                  color: 'var(--text)',
                  fontSize: '0.85rem',
                }}
                formatter={(value: number) => [formatCurrency(value), 'Value']}
              />
              <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
              <Area type="monotone" dataKey="current" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.15} strokeWidth={2} name="Current" />
              <Area type="monotone" dataKey="forecast_30d" stroke="var(--accent2)" fill="var(--accent2)" fillOpacity={0.1} strokeWidth={2} name="30-Day" />
              <Area type="monotone" dataKey="forecast_90d" stroke="var(--success)" fill="var(--success)" fillOpacity={0.08} strokeWidth={2} name="90-Day" />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ─── Cohort Heatmap Component ────────────────────────────────────────────────

function CohortHeatmap({ cohorts }: { cohorts: CohortData[] }) {
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null)
  const [selectedCohort, setSelectedCohort] = useState<number | null>(null)

  const avgRetention = useMemo(() => {
    if (cohorts.length === 0) return []
    const periods = cohorts[0]?.retention.length || 0
    const avgs: number[] = []
    for (let p = 0; p < periods; p++) {
      const sum = cohorts.reduce((acc, c) => acc + (c.retention[p] || 0), 0)
      avgs.push(sum / cohorts.length)
    }
    return avgs
  }, [cohorts])

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', padding: '1.5rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(168, 85, 247, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent2)',
            }}
          >
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Cohort Analysis</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Retention heatmap by signup cohort</p>
          </div>
        </div>

        {/* Average retention trend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Avg retention by period:</div>
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            {avgRetention.map((avg, i) => (
              <div
                key={i}
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '4px',
                  background: getHeatmapColor(avg),
                  opacity: getHeatmapOpacity(avg),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  color: 'var(--text)',
                }}
              >
                {avg.toFixed(0)}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Heatmap grid */}
      <div style={{ overflowX: 'auto' }}>
        <div style={{ minWidth: '600px' }}>
          {/* Header row */}
          <div style={{ display: 'flex', marginBottom: '0.5rem' }}>
            <div style={{ width: '120px', fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 600 }}>Cohort</div>
            {cohorts[0]?.retention.map((_, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  textAlign: 'center',
                  fontSize: '0.7rem',
                  color: 'var(--muted)',
                  fontWeight: 600,
                  padding: '0.25rem',
                }}
              >
                M{i + 1}
              </div>
            ))}
          </div>

          {/* Data rows */}
          {cohorts.map((cohort, rowIdx) => (
            <div
              key={rowIdx}
              style={{
                display: 'flex',
                alignItems: 'center',
                marginBottom: '0.25rem',
                borderRadius: '6px',
                transition: 'background 0.15s',
                background: selectedCohort === rowIdx ? 'rgba(168, 85, 247, 0.08)' : 'transparent',
              }}
              onMouseEnter={() => setSelectedCohort(rowIdx)}
              onMouseLeave={() => setSelectedCohort(null)}
            >
              <div style={{ width: '120px', padding: '0.5rem', fontSize: '0.8rem', fontWeight: 600 }}>
                <div>{cohort.cohort}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 400 }}>
                  {formatNumber(cohort.size)} users
                </div>
              </div>
              {cohort.retention.map((value, colIdx) => {
                const isHovered = hoveredCell?.row === rowIdx && hoveredCell?.col === colIdx
                return (
                  <div
                    key={colIdx}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      textAlign: 'center',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      borderRadius: '6px',
                      margin: '1px',
                      background: getHeatmapColor(value),
                      opacity: getHeatmapOpacity(value),
                      color: value > 50 ? 'var(--text)' : 'var(--muted)',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      transform: isHovered ? 'scale(1.1)' : 'scale(1)',
                      boxShadow: isHovered ? `0 0 12px ${getHeatmapColor(value)}40` : 'none',
                      position: 'relative',
                      zIndex: isHovered ? 10 : 1,
                    }}
                    onMouseEnter={() => setHoveredCell({ row: rowIdx, col: colIdx })}
                    onMouseLeave={() => setHoveredCell(null)}
                  >
                    {value.toFixed(0)}%
                    {isHovered && (
                      <div
                        style={{
                          position: 'absolute',
                          bottom: '100%',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          padding: '0.5rem 0.75rem',
                          background: 'var(--surface)',
                          border: '1px solid var(--border)',
                          borderRadius: '8px',
                          fontSize: '0.7rem',
                          whiteSpace: 'nowrap',
                          zIndex: 100,
                          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                          marginBottom: '0.5rem',
                        }}
                      >
                        <div style={{ fontWeight: 700 }}>{cohort.cohort} — Month {colIdx + 1}</div>
                        <div style={{ color: 'var(--muted)' }}>
                          Retention: {value.toFixed(1)}% · {formatNumber(Math.round(cohort.size * (value / 100)))} users
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          marginTop: '1rem',
          paddingTop: '1rem',
          borderTop: '1px solid var(--border)',
        }}
      >
        <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Retention:</span>
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          {[0, 20, 40, 60, 80, 100].map((val) => (
            <div
              key={val}
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '4px',
                background: getHeatmapColor(val),
                opacity: getHeatmapOpacity(val),
              }}
            />
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.7rem', color: 'var(--muted)' }}>
          <span>0%</span>
          <span>20%</span>
          <span>40%</span>
          <span>60%</span>
          <span>80%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  )
}

// ─── Funnel Visualization Component ──────────────────────────────────────────

function FunnelVisualization({ funnelData }: { funnelData: FunnelStage[] }) {
  const [selectedStage, setSelectedStage] = useState<number | null>(null)

  const chartData = funnelData.map((stage) => ({
    name: stage.stage,
    value: stage.value,
    fill: '',
  }))

  const colors = ['var(--accent)', 'var(--accent2)', 'var(--warning)', '#f97316', 'var(--danger)']

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', padding: '1.5rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--warning)',
            }}
          >
            <Filter className="w-5 h-5" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Conversion Funnel</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>User journey from visit to purchase</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent)' }}>
              {funnelData.length > 0 ? formatPercent(funnelData[funnelData.length - 1]?.conversion || 0) : '0%'}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>Overall Conversion</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--danger)' }}>
              {funnelData.length > 0 ? formatNumber(funnelData[0]?.value - funnelData[funnelData.length - 1]?.value || 0) : 0}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>Total Dropoff</div>
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: '350px' }}>
        <ResponsiveContainer width="100%" height={350}>
          <FunnelChart>
            <Tooltip
              contentStyle={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                color: 'var(--text)',
                fontSize: '0.85rem',
              }}
              formatter={(value: number, name: string) => [formatNumber(value), name]}
            />
            <Funnel dataKey="value" data={chartData} isAnimationActive>
              {chartData.map((_, index) => (
                <Cell key={index} fill={colors[index % colors.length]} />
              ))}
              <LabelList
                position="right"
                fill="var(--text)"
                stroke="none"
                dataKey="name"
                style={{ fontSize: '0.8rem', fontWeight: 600 }}
              />
              <LabelList
                position="center"
                fill="#fff"
                stroke="none"
                dataKey="value"
                style={{ fontSize: '0.9rem', fontWeight: 700 }}
                formatter={(v: number) => formatNumber(v)}
              />
            </Funnel>
          </FunnelChart>
        </ResponsiveContainer>
      </div>

      {/* Stage details */}
      <div style={{ marginTop: '1.5rem' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '0.75rem',
          }}
        >
          {funnelData.map((stage, i) => (
            <div
              key={i}
              style={{
                padding: '1rem',
                borderRadius: '12px',
                background: selectedStage === i ? `${colors[i % colors.length]}15` : 'rgba(30, 41, 59, 0.3)',
                border: `1px solid ${selectedStage === i ? colors[i % colors.length] : 'var(--border)'}`,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onClick={() => setSelectedStage(selectedStage === i ? null : i)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{stage.stage}</span>
                <div
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: colors[i % colors.length],
                  }}
                />
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{formatNumber(stage.value)}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                  {stage.conversion > 0 ? `${stage.conversion.toFixed(1)}% conv.` : '—'}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--danger)' }}>
                  {stage.dropoff > 0 ? `-${formatNumber(stage.dropoff)}` : ''}
                </span>
              </div>
              {selectedStage === i && (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>Stage metrics</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span>Conversion rate:</span>
                    <span style={{ fontWeight: 600, color: colors[i % colors.length] }}>
                      {stage.conversion.toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span>Dropoff count:</span>
                    <span style={{ fontWeight: 600, color: 'var(--danger)' }}>{formatNumber(stage.dropoff)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span>Dropoff rate:</span>
                    <span style={{ fontWeight: 600, color: 'var(--danger)' }}>
                      {stage.value > 0 ? ((stage.dropoff / stage.value) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Report Builder Component ────────────────────────────────────────────────

function ReportBuilder({
  onExport,
  availableSections,
}: {
  onExport: (config: ReportConfig) => void
  availableSections: { key: ReportSection; label: string; icon: React.ReactNode }[]
}) {
  const [config, setConfig] = useState<ReportConfig>({
    name: 'Custom Report',
    sections: ['kpis', 'anomalies', 'forecasts'],
    format: 'csv',
    dateRange: '30d',
  })
  const [isBuilding, setIsBuilding] = useState(false)

  const handleExport = useCallback(() => {
    setIsBuilding(true)
    setTimeout(() => {
      onExport(config)
      setIsBuilding(false)
    }, 800)
  }, [config, onExport])

  const toggleSection = (section: ReportSection) => {
    setConfig((prev) => ({
      ...prev,
      sections: prev.sections.includes(section)
        ? prev.sections.filter((s) => s !== section)
        : [...prev.sections, section],
    }))
  }

  return (
    <div className="glass animate-fade-in" style={{ borderRadius: '16px', padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'rgba(16, 185, 129, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--success)',
          }}
        >
          <Settings className="w-5 h-5" />
        </div>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Report Builder</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Create and export custom analytics reports</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
        {/* Report name */}
        <div>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--muted)', display: 'block', marginBottom: '0.5rem' }}>
            Report Name
          </label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => setConfig((prev) => ({ ...prev, name: e.target.value }))}
            style={{
              width: '100%',
              padding: '0.6rem 0.75rem',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--surface)',
              color: 'var(--text)',
              fontSize: '0.85rem',
              outline: 'none',
            }}
          />
        </div>

        {/* Date range */}
        <div>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--muted)', display: 'block', marginBottom: '0.5rem' }}>
            Date Range
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {[
              { value: '7d', label: '7D' },
              { value: '30d', label: '30D' },
              { value: '90d', label: '90D' },
              { value: '1y', label: '1Y' },
            ].map((range) => (
              <button
                key={range.value}
                onClick={() => setConfig((prev) => ({ ...prev, dateRange: range.value }))}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  borderRadius: '8px',
                  border: `1px solid ${config.dateRange === range.value ? 'var(--accent)' : 'var(--border)'}`,
                  background: config.dateRange === range.value ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                  color: config.dateRange === range.value ? 'var(--accent)' : 'var(--muted)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>

        {/* Export format */}
        <div>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--muted)', display: 'block', marginBottom: '0.5rem' }}>
            Export Format
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {[
              { value: 'csv' as ExportFormat, label: 'CSV', icon: <FileText className="w-4 h-4" /> },
              { value: 'json' as ExportFormat, label: 'JSON', icon: <FileText className="w-4 h-4" /> },
              { value: 'pdf' as ExportFormat, label: 'PDF', icon: <FileText className="w-4 h-4" /> },
            ].map((fmt) => (
              <button
                key={fmt.value}
                onClick={() => setConfig((prev) => ({ ...prev, format: fmt.value }))}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  borderRadius: '8px',
                  border: `1px solid ${config.format === fmt.value ? 'var(--accent)' : 'var(--border)'}`,
                  background: config.format === fmt.value ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                  color: config.format === fmt.value ? 'var(--accent)' : 'var(--muted)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.35rem',
                  transition: 'all 0.2s',
                }}
              >
                {fmt.icon}
                {fmt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Section selection */}
      <div style={{ marginTop: '1.5rem' }}>
        <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--muted)', display: 'block', marginBottom: '0.75rem' }}>
          Include Sections
        </label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {availableSections.map((section) => {
            const isSelected = config.sections.includes(section.key)
            return (
              <button
                key={section.key}
                onClick={() => toggleSection(section.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  borderRadius: '999px',
                  border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                  background: isSelected ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                  color: isSelected ? 'var(--accent)' : 'var(--muted)',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                {section.icon}
                {section.label}
                {isSelected && <CheckCircle2 className="w-3.5 h-3.5" />}
              </button>
            )
          })}
        </div>
      </div>

      {/* Export button */}
      <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleExport}
          disabled={isBuilding || config.sections.length === 0}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.75rem 1.5rem',
            borderRadius: '10px',
            border: 'none',
            background: config.sections.length === 0 ? 'var(--border)' : 'linear-gradient(135deg, var(--accent), var(--accent2))',
            color: config.sections.length === 0 ? 'var(--muted)' : '#000',
            fontSize: '0.85rem',
            fontWeight: 700,
            cursor: config.sections.length === 0 ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            opacity: isBuilding ? 0.7 : 1,
          }}
        >
          {isBuilding ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Download className="w-4 h-4" />
              Export Report
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// ─── Export Options Component ────────────────────────────────────────────────

function ExportOptions({ data }: { data: AnalyticsData }) {
  const [exporting, setExporting] = useState<string | null>(null)

  const handleExport = useCallback(
    (format: string) => {
      setExporting(format)
      setTimeout(() => {
        // Simulate export
        const content = JSON.stringify(data, null, 2)
        const blob = new Blob([content], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `analytics-export-${new Date().toISOString().split('T')[0]}.${format}`
        a.click()
        URL.revokeObjectURL(url)
        setExporting(null)
      }, 1000)
    },
    [data],
  )

  return (
    <div
      className="glass animate-fade-in"
      style={{
        borderRadius: '16px',
        padding: '1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Download className="w-5 h-5 text-[var(--accent)]" />
        <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Quick Export</span>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {['csv', 'json', 'pdf'].map((format) => (
          <button
            key={format}
            onClick={() => handleExport(format)}
            disabled={exporting !== null}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: exporting === format ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
              color: exporting === format ? 'var(--accent)' : 'var(--muted)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: exporting !== null ? 'wait' : 'pointer',
              textTransform: 'uppercase',
              transition: 'all 0.2s',
            }}
          >
            {exporting === format ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileText className="w-3.5 h-3.5" />
            )}
            {format}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Table styles ────────────────────────────────────────────────────────────

const thStyle: React.CSSProperties = {
  padding: '0.75rem 1rem',
  textAlign: 'left',
  fontSize: '0.7rem',
  fontWeight: 700,
  color: 'var(--muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  whiteSpace: 'nowrap',
}

const tdStyle: React.CSSProperties = {
  padding: '0.75rem 1rem',
  color: 'var(--text)',
  verticalAlign: 'middle',
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

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = () => {
    setRefreshing(true)
    setLoading(true)
    fetchData()
  }

  // ── Derived data for new components ──
  const kpiData: KPIData[] = useMemo(() => {
    if (!data?.kpis) return []
    const icons = ['revenue', 'users', 'conversion', 'orders', 'revenue']
    return data.kpis.map((k, i) => ({
      ...k,
      status: k.status as KPIStatus,
      change: Math.random() * 20 - 10,
      icon: icons[i % icons.length],
    }))
  }, [data])

  const anomalyData: AnomalyData[] = useMemo(() => {
    if (!data?.anomalies) return []
    return data.anomalies.map((a) => ({
      ...a,
      severity: getDeviationSeverity(a.deviation),
    }))
  }, [data])

  const forecastData: ForecastData[] = useMemo(() => {
    if (!data?.forecasts) return []
    return data.forecasts.map((f) => ({
      ...f,
      confidence_30d: Math.floor(Math.random() * 20 + 75),
      confidence_90d: Math.floor(Math.random() * 20 + 55),
    }))
  }, [data])

  const cohortData: CohortData[] = useMemo(() => {
    const cohorts = ['Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026']
    return cohorts.map((cohort, i) => ({
      cohort,
      size: Math.floor(Math.random() * 5000 + 2000),
      retention: Array.from({ length: 6 }, (_, j) => {
        const base = 100 - j * 15 - i * 5
        return Math.max(base + Math.random() * 10, 5)
      }),
    }))
  }, [])

  const funnelData: FunnelStage[] = useMemo(() => {
    const stages = ['Visits', 'Signups', 'Activations', 'Trials', 'Purchases']
    const values = [50000, 12000, 8000, 3500, 1200]
    return stages.map((stage, i) => ({
      stage,
      value: values[i],
      conversion: i === 0 ? 100 : (values[i] / values[i - 1]) * 100,
      dropoff: i === 0 ? 0 : values[i - 1] - values[i],
    }))
  }, [])

  const reportSections: { key: ReportSection; label: string; icon: React.ReactNode }[] = [
    { key: 'kpis', label: 'KPIs', icon: <Target className="w-4 h-4" /> },
    { key: 'anomalies', label: 'Anomalies', icon: <AlertTriangle className="w-4 h-4" /> },
    { key: 'forecasts', label: 'Forecasts', icon: <BarChart3 className="w-4 h-4" /> },
    { key: 'cohorts', label: 'Cohorts', icon: <Layers className="w-4 h-4" /> },
    { key: 'funnel', label: 'Funnel', icon: <Filter className="w-4 h-4" /> },
  ]

  const handleReportExport = useCallback(
    (config: ReportConfig) => {
      // In a real app, this would generate and download the report
      alert(`Report "${config.name}" exported as ${config.format.toUpperCase()}`)
    },
    [],
  )

  // ── Loading state ──
  if (loading && !refreshing) {
    return (
      <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '2rem' }}>
          Analytics
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="glass animate-pulse-slow"
              style={{ height: '200px', borderRadius: '16px', animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
        <div style={{ marginTop: '2rem' }}>
          <div className="glass animate-pulse-slow" style={{ height: '400px', borderRadius: '16px' }} />
        </div>
      </div>
    )
  }

  // ── Error state ──
  if (error) {
    return (
      <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '2rem' }}>
          Analytics
        </h2>
        <div
          className="glass"
          style={{
            padding: '3rem',
            borderRadius: '16px',
            textAlign: 'center',
            color: 'var(--danger)',
          }}
        >
          <XCircle className="w-16 h-16 mx-auto mb-4" />
          <div style={{ fontWeight: 700, fontSize: '1.25rem', marginBottom: '0.5rem' }}>Failed to load analytics</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>{error}</div>
          <button
            onClick={handleRefresh}
            style={{
              padding: '0.75rem 2rem',
              background: 'linear-gradient(135deg, var(--accent), var(--accent2))',
              color: '#000',
              border: 'none',
              borderRadius: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              fontSize: '0.9rem',
            }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // ── Empty state ──
  if (!data || (data.kpis.length === 0 && data.anomalies.length === 0 && data.forecasts.length === 0)) {
    return (
      <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '2rem' }}>
          Analytics
        </h2>
        <div
          className="glass"
          style={{
            padding: '4rem',
            borderRadius: '16px',
            textAlign: 'center',
            color: 'var(--muted)',
          }}
        >
          <BarChart3 className="w-16 h-16 mx-auto mb-4" style={{ opacity: 0.5 }} />
          <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>No analytics data available</div>
          <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Data will appear here once your analytics pipeline is configured.
          </div>
        </div>
      </div>
    )
  }

  // ── Normal render ──
  return (
    <div className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            Analytics
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginTop: '0.25rem' }}>
            Comprehensive business intelligence and insights
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
            Last updated: {new Date().toLocaleString()}
          </span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'transparent',
              color: 'var(--muted)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: refreshing ? 'wait' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <RefreshCw className="w-4 h-4" style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {kpiData.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Zap className="w-4 h-4 text-[var(--accent)]" />
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--muted)' }}>Key Performance Indicators</h3>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '1rem',
            }}
          >
            {kpiData.map((kpi, i) => (
              <KPICard key={i} kpi={kpi} index={i} />
            ))}
          </div>
        </section>
      )}

      {/* Forecast Chart */}
      {forecastData.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <ForecastChart forecasts={forecastData} />
        </section>
      )}

      {/* Anomalies */}
      {anomalyData.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <AnomaliesTable anomalies={anomalyData} />
        </section>
      )}

      {/* Cohort Heatmap */}
      <section style={{ marginBottom: '2rem' }}>
        <CohortHeatmap cohorts={cohortData} />
      </section>

      {/* Funnel */}
      <section style={{ marginBottom: '2rem' }}>
        <FunnelVisualization funnelData={funnelData} />
      </section>

      {/* Report Builder */}
      <section style={{ marginBottom: '2rem' }}>
        <ReportBuilder onExport={handleReportExport} availableSections={reportSections} />
      </section>

      {/* Export Options */}
      <section style={{ marginBottom: '2rem' }}>
        <ExportOptions data={data} />
      </section>
    </div>
  )
}
