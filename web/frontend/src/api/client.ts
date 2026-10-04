const BASE_URL = '/api'

/**
 * Custom error class for API failures with status code and message.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Generic fetch wrapper with error handling and JSON parsing.
 * @param endpoint - API endpoint path (appended to BASE_URL)
 * @param options - Optional fetch options (method, body, headers)
 * @returns Parsed JSON response typed as T
 * @throws {ApiError} When response is not OK or body is invalid
 */
async function fetchData<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, options)
  if (!response.ok) {
    throw new ApiError(response.status, `API error ${response.status}: ${response.statusText}`)
  }
  const text = await response.text()
  if (!text) {
    throw new ApiError(response.status, 'Empty response body')
  }
  return JSON.parse(text) as T
}

/**
 * Generic request wrapper supporting all HTTP methods.
 */
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const text = await response.text()
    let message = `API error ${response.status}: ${response.statusText}`
    try {
      const json = JSON.parse(text)
      if (json.detail) message = json.detail
    } catch { /* ignore */ }
    throw new ApiError(response.status, message)
  }
  const text = await response.text()
  if (!text) throw new ApiError(response.status, 'Empty response body')
  return JSON.parse(text) as T
}

/**
 * API client for APEX-OS backend endpoints.
 * All methods return typed data and throw ApiError on failure.
 */
export const api = {
  /** Fetch dashboard metrics, revenue trend, and recent activity. */
  getDashboard: (): Promise<DashboardData> =>
    fetchData<DashboardData>('/dashboard'),

  /** Fetch accounting data including accounts, journal entries, and trial balance. */
  getAccounting: (): Promise<AccountingData> =>
    fetchData<AccountingData>('/accounting'),

  /** Create a new accounting entry. */
  createAccountingEntry: (data: Partial<AccountingData>): Promise<AccountingData> =>
    request<AccountingData>('/accounting', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing accounting entry by ID. */
  updateAccountingEntry: (id: string, data: Partial<AccountingData>): Promise<AccountingData> =>
    request<AccountingData>(`/accounting/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an accounting entry by ID. */
  deleteAccountingEntry: (id: string): Promise<void> =>
    request<void>(`/accounting/${id}`, { method: 'DELETE' }),

  /** Fetch CRM data including leads, opportunities, and forecast. */
  getCRM: (): Promise<CRMData> =>
    fetchData<CRMData>('/crm'),

  /** Fetch analytics data including KPIs, anomalies, and forecasts. */
  getAnalytics: (): Promise<AnalyticsData> =>
    fetchData<AnalyticsData>('/analytics'),

  /** Fetch agent reach data including agents, channels, and routes. */
  getAgentReach: (): Promise<AgentReachData> =>
    fetchData<AgentReachData>('/agent-reach'),

  /** Create a new agent. */
  createAgent: (data: Omit<Agent, 'id'>): Promise<Agent> =>
    request<Agent>('/agent-reach', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing agent by ID. */
  updateAgent: (id: string, data: Omit<Agent, 'id'>): Promise<Agent> =>
    request<Agent>(`/agent-reach/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an agent by ID. */
  deleteAgent: (id: string): Promise<void> =>
    request<void>(`/agent-reach/${id}`, { method: 'DELETE' }),

  /** Fetch big data platform status including datasets, queries, and storage. */
  getBigData: (): Promise<BigData> =>
    fetchData<BigData>('/bigdata'),

  /** Fetch paginated big data datasets with optional search and format filter. */
  getBigDataDatasets: (params: { page: number; limit: number; search?: string; format?: string }): Promise<{ items: BigDataDataset[]; total: number }> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) })
    if (params.search) sp.set('search', params.search)
    if (params.format) sp.set('format', params.format)
    return request<{ items: BigDataDataset[]; total: number }>(`/bigdata?${sp}`)
  },

  /** Create a new big data dataset. */
  createBigDataDataset: (data: { name: string; description: string; size: number; format: string }): Promise<BigDataDataset> =>
    request<BigDataDataset>('/bigdata', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing big data dataset. */
  updateBigDataDataset: (id: string, data: { name: string; description: string; size: number; format: string }): Promise<BigDataDataset> =>
    request<BigDataDataset>(`/bigdata/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a big data dataset. */
  deleteBigDataDataset: (id: string): Promise<void> =>
    request<void>(`/bigdata/${id}`, { method: 'DELETE' }),

  /** Fetch data science platform status including models, experiments, and features. */
  getDataScience: (): Promise<DataScienceData> =>
    fetchData<DataScienceData>('/datascience'),

  /** Fetch continuous BI status including dashboards, alerts, and data freshness. */
  getContinuousBI: (): Promise<ContinuousBIData> =>
    fetchData<ContinuousBIData>('/continuous-bi'),

  /** Fetch all available data in a single aggregated response. */
  getAll: (): Promise<Record<string, unknown>> =>
    fetchData<Record<string, unknown>>('/all'),

  /** Fetch paginated analytics entries with optional search and category filter. */
  getAnalyticsList: (params: AnalyticsListParams): Promise<AnalyticsListResponse> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.category) sp.set('category', params.category);
    return fetchData<AnalyticsListResponse>(`/analytics?${sp}`);
  },

  /** Create a new analytics entry. */
  createAnalytics: (data: Omit<AnalyticsEntry, 'id'>): Promise<AnalyticsEntry> =>
    fetchData<AnalyticsEntry>('/analytics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Update an existing analytics entry by ID. */
  updateAnalytics: (id: string, data: Omit<AnalyticsEntry, 'id'>): Promise<AnalyticsEntry> =>
    fetchData<AnalyticsEntry>(`/analytics/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Delete an analytics entry by ID. */
  deleteAnalytics: (id: string): Promise<void> =>
    fetchData<void>(`/analytics/${id}`, { method: 'DELETE' }),

  /** Fetch paginated users with optional search and filters. */
  getUsers: (params: UserListParams): Promise<UserListResponse> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.role) sp.set('role', params.role);
    if (params.status) sp.set('status', params.status);
    return fetchData<UserListResponse>(`/users?${sp}`);
  },

  /** Create a new user. */
  createUser: (data: UserFormData): Promise<User> =>
    fetchData<User>('/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Update an existing user by ID. */
  updateUser: (id: number, data: UserFormData): Promise<User> =>
    fetchData<User>(`/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Delete a user by ID. */
  deleteUser: (id: number): Promise<void> =>
    fetchData<void>(`/users/${id}`, { method: 'DELETE' }),

  // ── ContinuousBI Reports CRUD ──────────────────────────────────────────────

  /** Fetch paginated list of ContinuousBI reports. */
  getContinuousBIReports: (params?: { skip?: number; limit?: number; report_type?: string }): Promise<ContinuousBIReport[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.report_type) sp.set('report_type', params.report_type)
    const qs = sp.toString()
    return request<ContinuousBIReport[]>(`/continuous-bi${qs ? `?${qs}` : ''}`)
  },

  /** Create a new ContinuousBI report. */
  createContinuousBIReport: (data: ContinuousBIReportInput): Promise<ContinuousBIReport> =>
    request<ContinuousBIReport>('/continuous-bi', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing ContinuousBI report. */
  updateContinuousBIReport: (id: number, data: ContinuousBIReportInput): Promise<ContinuousBIReport> =>
    request<ContinuousBIReport>(`/continuous-bi/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a ContinuousBI report. */
  deleteContinuousBIReport: (id: number): Promise<void> =>
    request<void>(`/continuous-bi/${id}`, { method: 'DELETE' }),

  // ── Leads CRUD ──────────────────────────────────────────────────────────────

  /** Fetch all leads. */
  getLeads: (): Promise<Lead[]> =>
    fetchData<Lead[]>('/leads'),

  /** Create a new lead. */
  createLead: (data: LeadInput): Promise<Lead> =>
    request<Lead>('/leads', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing lead by ID. */
  updateLead: (id: string, data: LeadInput): Promise<Lead> =>
    request<Lead>(`/leads/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a lead by ID. */
  deleteLead: (id: string): Promise<void> =>
    request<void>(`/leads/${id}`, { method: 'DELETE' }),
} as const

// ── Type Definitions ──────────────────────────────────────────────────────────

export interface ContinuousBIReport {
  id: number
  name: string
  report_type: string
  status: string
  created_at: string
  updated_at: string
}

export interface ContinuousBIReportInput {
  name: string
  report_type: string
  status?: string
}

export interface DashboardData {
  id: string
  metrics: Array<{ name: string; value: number; change: number; trend: string }>
  revenue_trend: number[]
  user_growth: number[]
  recent_activity: Array<{ action: string; user: string; time: string }>
}

export interface AccountingData {
  id: string
  accounts: Array<{ id: string; name: string; type: string; balance: number }>
  journal_entries: Array<{ id: string; date: string; debit: string; credit: string; amount: number; description: string }>
  trial_balance: { debits: number; credits: number; balanced: boolean }
}

export interface CRMData {
  id: string
  leads: Array<{ id: string; name: string; status: string; score: number; value: number }>
  opportunities: Array<{ id: string; name: string; stage: string; value: number; probability: number }>
  forecast: { q1: number; q2: number; q3: number; q4: number }
}

export interface AnalyticsData {
  id: string
  kpis: Array<{ name: string; value: number; target: number; status: string }>
  anomalies: Array<{ metric: string; date: string; expected: number; actual: number; deviation: string }>
  forecasts: Array<{ metric: string; current: number; forecast_30d: number; forecast_90d: number }>
}

export interface Agent {
  id: string
  name: string
  status: string
  messages_processed: number
  latency_ms: number
}

export interface AgentReachData {
  id: string
  agents: Agent[]
  channels: Array<{ id: string; name: string; type: string; throughput: number }>
  routes: Array<{ source: string; target: string; messages: number; success_rate: number }>
}

export interface BigData {
  id: string
  datasets: Array<{ name: string; size: string; rows: number; format: string }>
  queries: Array<{ id: string; type: string; duration_ms: number; rows_scanned: number; status: string }>
  storage: { total_tb: number; used_tb: number; compression_ratio: number }
}

export interface BigDataDataset {
  id: string
  name: string
  description: string
  size: number
  format: string
  createdAt: string
}

export interface DataScienceData {
  id: string
  models: Array<{ id: string; name: string; type: string; accuracy: number; last_trained: string; status: string }>
  experiments: Array<{ id: string; name: string; status: string; progress: number }>
  features: Array<{ name: string; type: string; importance: number }>
}

export interface ContinuousBIData {
  id: string
  dashboards: Array<{ name: string; widgets: number; refresh_rate: string; viewers: number }>
  alerts: Array<{ name: string; condition: string; severity: string; enabled: boolean }>
  data_freshness: { last_update: string; lag_seconds: number; status: string }
}

export interface User {
  id: number
  name: string
  email: string
  role: string
  status: string
  createdAt: string
}

export interface UserFormData {
  name: string
  email: string
  role: string
  status: string
}

export interface UserListParams {
  page: number
  limit: number
  search?: string
  role?: string
  status?: string
}

export interface UserListResponse {
  users: User[]
  total: number
}

export interface AnalyticsEntry {
  id: string
  name: string
  category: string
  value: number
  date: string
  notes?: string
}

export interface AnalyticsListParams {
  page: number
  limit: number
  search?: string
  category?: string
}

export interface AnalyticsListResponse {
  items: AnalyticsEntry[]
  total: number
}

export interface Lead {
  id: string
  name: string
  email?: string
  company?: string
  status: string
  score: number
  value: number
  source?: string
  lastContact?: string
}

export interface LeadInput {
  name: string
  email?: string
  company?: string
  status: string
  score: number
  value: number
  source?: string
}
