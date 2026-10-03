const BASE_URL = '/api'

async function fetchData<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`)
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

export const api = {
  getDashboard: () => fetchData<DashboardData>('/dashboard'),
  getAccounting: () => fetchData<AccountingData>('/accounting'),
  getCRM: () => fetchData<CRMData>('/crm'),
  getAnalytics: () => fetchData<AnalyticsData>('/analytics'),
  getAgentReach: () => fetchData<AgentReachData>('/agent-reach'),
  getBigData: () => fetchData<BigData>('/bigdata'),
  getDataScience: () => fetchData<DataScienceData>('/datascience'),
  getContinuousBI: () => fetchData<ContinuousBIData>('/continuous-bi'),
  getAll: () => fetchData<AllData>('/all'),
  healthCheck: () => fetchData<{ status: string; timestamp: string }>('/health'),
}

// Type definitions
export interface Metric {
  name: string
  value: number
  change: number
  trend: 'up' | 'down'
}

export interface DashboardData {
  metrics: Metric[]
  revenue_trend: number[]
  user_growth: number[]
  recent_activity: Array<{ action: string; user: string; time: string }>
}

export interface AccountingData {
  accounts: Array<{ id: string; name: string; type: string; balance: number }>
  journal_entries: Array<{ id: string; date: string; debit: string; credit: string; amount: number; description: string }>
  trial_balance: { debits: number; credits: number; balanced: boolean }
}

export interface CRMData {
  leads: Array<{ id: string; name: string; status: string; score: number; value: number }>
  opportunities: Array<{ id: string; name: string; stage: string; value: number; probability: number }>
  forecast: { q1: number; q2: number; q3: number; q4: number }
}

export interface AnalyticsData {
  kpis: Array<{ name: string; value: number; target: number; status: string }>
  anomalies: Array<{ metric: string; date: string; expected: number; actual: number; deviation: string }>
  forecasts: Array<{ metric: string; current: number; forecast_30d: number; forecast_90d: number }>
}

export interface AgentReachData {
  agents: Array<{ id: string; name: string; status: string; messages_processed: number; latency_ms: number }>
  channels: Array<{ id: string; name: string; type: string; throughput: number }>
  routes: Array<{ source: string; target: string; messages: number; success_rate: number }>
}

export interface BigData {
  datasets: Array<{ name: string; size: string; rows: number; format: string }>
  queries: Array<{ id: string; type: string; duration_ms: number; rows_scanned: number; status: string }>
  storage: { total_tb: number; used_tb: number; compression_ratio: number }
}

export interface DataScienceData {
  models: Array<{ name: string; type: string; accuracy: number; last_trained: string; status: string }>
  experiments: Array<{ id: string; name: string; status: string; progress: number }>
  features: Array<{ name: string; type: string; importance: number }>
}

export interface ContinuousBIData {
  dashboards: Array<{ name: string; widgets: number; refresh_rate: string; viewers: number }>
  alerts: Array<{ name: string; condition: string; severity: string; enabled: boolean }>
  data_freshness: { last_update: string; lag_seconds: number; status: string }
}

export interface AllData {
  dashboard: DashboardData
  accounting: AccountingData
  crm: CRMData
  analytics: AnalyticsData
  agent_reach: AgentReachData
  bigdata: BigData
  datascience: DataScienceData
  continuous_bi: ContinuousBIData
}
