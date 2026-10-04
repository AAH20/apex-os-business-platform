const BASE_URL = '/api'
const API_KEY = 'test-api-key-12345'

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
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: { 'X-API-Key': API_KEY, ...options?.headers },
  })
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
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
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

  /** Fetch paginated agent reach agents with optional search and status filter. */
  getAgentReachAgents: (params: { page: number; limit: number; search?: string; status?: string }): Promise<{ agents: Agent[]; total: number }> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.status) sp.set('status', params.status);
    return request<{ agents: Agent[]; total: number }>(`/agent-reach?${sp}`);
  },

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

  /** Fetch paginated data science models with optional search and status filter. */
  getDataScienceModels: (params: { page: number; limit: number; search?: string; status?: string }): Promise<{ models: DataScienceModel[]; total: number }> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.status) sp.set('status', params.status);
    return request<{ models: DataScienceModel[]; total: number }>(`/datascience?${sp}`);
  },

  /** Create a new data science model. */
  createDataScienceModel: (data: DataScienceModelInput): Promise<DataScienceModel> =>
    request<DataScienceModel>('/datascience', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing data science model. */
  updateDataScienceModel: (id: string, data: DataScienceModelInput): Promise<DataScienceModel> =>
    request<DataScienceModel>(`/datascience/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a data science model. */
  deleteDataScienceModel: (id: string): Promise<void> =>
    request<void>(`/datascience/${id}`, { method: 'DELETE' }),

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
  getContinuousBIReports: (params?: { skip?: number; limit?: number; report_type?: string; search?: string }): Promise<ContinuousBIReport[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.report_type) sp.set('report_type', params.report_type)
    if (params?.search) sp.set('search', params.search)
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

  // ── Roles CRUD ──────────────────────────────────────────────────────────────

  /** Fetch all roles. */
  getRoles: (): Promise<Role[]> =>
    fetchData<Role[]>('/roles'),

  /** Fetch a single role by ID. */
  getRoleById: (id: string): Promise<Role> =>
    fetchData<Role>(`/roles/${id}`),

  /** Create a new role. */
  createRole: (data: RoleInput): Promise<Role> =>
    request<Role>('/roles', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing role by ID. */
  updateRole: (id: string, data: RoleInput): Promise<Role> =>
    request<Role>(`/roles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a role by ID. */
  deleteRole: (id: string): Promise<void> =>
    request<void>(`/roles/${id}`, { method: 'DELETE' }),

  // ── Permissions CRUD ────────────────────────────────────────────────────────

  /** Fetch all permissions. */
  getPermissions: (): Promise<Permission[]> =>
    fetchData<Permission[]>('/permissions'),

  /** Fetch a single permission by ID. */
  getPermissionById: (id: string): Promise<Permission> =>
    fetchData<Permission>(`/permissions/${id}`),

  /** Create a new permission. */
  createPermission: (data: PermissionInput): Promise<Permission> =>
    request<Permission>('/permissions', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing permission by ID. */
  updatePermission: (id: string, data: PermissionInput): Promise<Permission> =>
    request<Permission>(`/permissions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a permission by ID. */
  deletePermission: (id: string): Promise<void> =>
    request<void>(`/permissions/${id}`, { method: 'DELETE' }),

  // ── Opportunities CRUD ──────────────────────────────────────────────────────

  /** Fetch all opportunities. */
  getOpportunities: (): Promise<Opportunity[]> =>
    fetchData<Opportunity[]>('/opportunities'),

  /** Fetch a single opportunity by ID. */
  getOpportunityById: (id: string): Promise<Opportunity> =>
    fetchData<Opportunity>(`/opportunities/${id}`),

  /** Create a new opportunity. */
  createOpportunity: (data: OpportunityInput): Promise<Opportunity> =>
    request<Opportunity>('/opportunities', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing opportunity by ID. */
  updateOpportunity: (id: string, data: OpportunityInput): Promise<Opportunity> =>
    request<Opportunity>(`/opportunities/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an opportunity by ID. */
  deleteOpportunity: (id: string): Promise<void> =>
    request<void>(`/opportunities/${id}`, { method: 'DELETE' }),

  // ── Campaigns CRUD ──────────────────────────────────────────────────────────

  /** Fetch all campaigns. */
  getCampaigns: (): Promise<Campaign[]> =>
    fetchData<Campaign[]>('/campaigns'),

  /** Fetch a single campaign by ID. */
  getCampaignById: (id: string): Promise<Campaign> =>
    fetchData<Campaign>(`/campaigns/${id}`),

  /** Create a new campaign. */
  createCampaign: (data: CampaignInput): Promise<Campaign> =>
    request<Campaign>('/campaigns', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing campaign by ID. */
  updateCampaign: (id: string, data: CampaignInput): Promise<Campaign> =>
    request<Campaign>(`/campaigns/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a campaign by ID. */
  deleteCampaign: (id: string): Promise<void> =>
    request<void>(`/campaigns/${id}`, { method: 'DELETE' }),

  // ── Alerts CRUD ─────────────────────────────────────────────────────────────

  /** Fetch all alerts. */
  getAlerts: (): Promise<Alert[]> =>
    fetchData<Alert[]>('/alerts'),

  /** Fetch a single alert by ID. */
  getAlertById: (id: string): Promise<Alert> =>
    fetchData<Alert>(`/alerts/${id}`),

  /** Create a new alert. */
  createAlert: (data: AlertInput): Promise<Alert> =>
    request<Alert>('/alerts', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing alert by ID. */
  updateAlert: (id: string, data: AlertInput): Promise<Alert> =>
    request<Alert>(`/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an alert by ID. */
  deleteAlert: (id: string): Promise<void> =>
    request<void>(`/alerts/${id}`, { method: 'DELETE' }),
} as const

// ── Type Definitions ──────────────────────────────────────────────────────────

export interface ContinuousBIReport {
  id: number;
  name: string;
  description?: string | null;
  report_type: string;
  owner?: string;
  is_active?: boolean;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ContinuousBIReportInput {
  name: string;
  description?: string;
  report_type: string;
  owner?: string;
  is_active?: boolean;
  status?: string;
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
  id: string;
  name: string;
  type?: string;
  status: string;
  description?: string;
  createdAt?: string;
  messages_processed?: number;
  latency_ms?: number;
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
  id: string;
  models: Array<{ id: string; name: string; type: string; accuracy: number; last_trained: string; status: string }>;
  experiments: Array<{ id: string; name: string; status: string; progress: number }>;
  features: Array<{ name: string; type: string; importance: number }>;
}

export interface DataScienceModel {
  id: string;
  name: string;
  type: string;
  version: string;
  status: string;
  accuracy: number;
  createdAt?: string;
}

export interface DataScienceModelInput {
  name: string;
  type: string;
  version: string;
  status: string;
  accuracy: number;
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

export interface Role {
  id: string
  name: string
  description?: string
  permissions?: string[]
  is_active?: boolean
  userCount?: number
  created_at?: string
  updated_at?: string
}

export interface RoleInput {
  name: string
  description?: string
  permissions?: string[]
  is_active?: boolean
  userCount?: number
}

export interface Permission {
  id: string
  name: string
  description?: string
  resource?: string
  action?: string
  module?: string
  created_at?: string
}

export interface PermissionInput {
  name: string
  description?: string
  resource?: string
  action?: string
  module?: string
}

export interface Opportunity {
  id: string
  name: string
  stage?: string
  value?: number
  probability?: number
  account?: string
  contact?: string
  close_date?: string
  status?: string
  expectedClose?: string
  owner?: string
  created_at?: string
  updated_at?: string
}

export interface OpportunityInput {
  name: string
  stage?: string
  value?: number
  probability?: number
  account?: string
  contact?: string
  close_date?: string
  status?: string
  expectedClose?: string
  owner?: string
}

export interface Campaign {
  id: string
  name: string
  description?: string
  status?: string
  type?: string
  start_date?: string
  end_date?: string
  budget?: number
  spent?: number
  startDate?: string
  endDate?: string
  created_at?: string
  updated_at?: string
}

export interface CampaignInput {
  name: string
  description?: string
  status?: string
  type?: string
  start_date?: string
  end_date?: string
  budget?: number
  spent?: number
  startDate?: string
  endDate?: string
}

export interface Alert {
  id: string
  name: string
  description?: string
  severity?: string
  condition?: string
  enabled?: boolean
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface AlertInput {
  name: string
  description?: string
  severity?: string
  condition?: string
  enabled?: boolean
  is_active?: boolean
}
