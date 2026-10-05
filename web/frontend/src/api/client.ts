const BASE_URL = '/api'
const API_KEY = 'test-api-key-12345'

/**
 * Join BASE_URL with an endpoint exactly once.
 *
 * Most endpoints in this file are written as full paths (`/api/iot/devices/`),
 * while a few are written bare (`/dashboards`). Naive concatenation produced
 * `/api/api/iot/devices/` -> 404 -> "Failed to fetch" with zeroed metrics.
 * Strip a leading `/api` (or a duplicated `//`) before prefixing so both forms
 * resolve to the same real backend route.
 */
function buildUrl(endpoint: string): string {
  if (/^https?:\/\//.test(endpoint)) return endpoint
  const path = endpoint.startsWith('/api/') ? endpoint.slice(4) : endpoint
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${BASE_URL}${normalized}`
}
const DEFAULT_TIMEOUT = 10000 // 10 seconds

async function fetchWithTimeout(url: string, options?: RequestInit, timeout = DEFAULT_TIMEOUT): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  const externalSignal = options?.signal
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort()
    else externalSignal.addEventListener('abort', () => controller.abort(), { once: true })
  }
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

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
 * Keys a backend may use to wrap a collection payload.
 * Checked in order, so the first array-valued key wins.
 */
const LIST_KEYS = ['items', 'data', 'results', 'records', 'rows', 'list', 'agents', 'models', 'content'] as const

/**
 * Normalize any list response shape into a flat array so callers can always
 * `.map()`/`.filter()` without a runtime TypeError.
 *
 * Handles: bare array, `{ items: [] }`, `{ data: [] }`, `{ results: [] }`,
 * other wrapper keys (records/rows/agents/models/content), single-key objects
 * holding an array, and null/undefined/non-array scalars (-> `[]`).
 */
export function normalizeToArray<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[]
  if (data === null || typeof data !== 'object') return []

  const obj = data as Record<string, unknown>
  for (const key of LIST_KEYS) {
    const value = obj[key]
    if (Array.isArray(value)) return value as T[]
  }
  // `{ "leads": [...] }`-style single-collection envelope.
  const arrayValues = Object.values(obj).filter((v): v is unknown[] => Array.isArray(v))
  if (arrayValues.length === 1) return arrayValues[0] as T[]
  // `{ data: { items: [...] } }` — unwrap one nested envelope.
  const objectValues = Object.values(obj).filter(
    (v): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v),
  )
  if (objectValues.length === 1) {
    for (const key of LIST_KEYS) {
      const value = objectValues[0][key]
      if (Array.isArray(value)) return value as T[]
    }
  }
  return []
}

/** Shape of a paged response, keyed by whichever field the backend uses. */
export type PagedResult<T, K extends string = 'items'> = { [P in K]: T[] } & { total: number }

/**
 * Normalize a paged response into `{ items, total }`, while preserving any other
 * array-valued key the backend returned (e.g. `{ agents: [...] }`) so existing
 * callers reading `.agents` keep working.
 */
export function normalizeToList<T>(data: unknown): { items: T[]; total: number } & Record<string, unknown> {
  const items = normalizeToArray<T>(data)
  const isObj = data !== null && typeof data === 'object' && !Array.isArray(data)
  const obj = isObj ? (data as Record<string, unknown>) : {}
  const rawTotal = obj.total
  const total = typeof rawTotal === 'number' ? rawTotal : items.length

  const extra: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (key !== 'items' && Array.isArray(value)) extra[key] = value
  }
  return { items, total, ...extra } as { items: T[]; total: number } & Record<string, unknown>
}

/**
 * Normalize a response whose collection key is named by the caller, guaranteeing
 * both `items` and that key are populated. Lets endpoints like
 * `getAgentReachAgents()` keep their declared `{ agents, total }` contract
 * while the payload may actually be `{ items: [...] }` or a bare array.
 */
export function normalizeToKeyedList<T, K extends string>(
  data: unknown,
  key: K,
): { items: T[]; total: number } & Record<K, T[]> {
  const list = normalizeToList<T>(data)
  const keyed = list[key]
  return { ...list, [key]: (Array.isArray(keyed) ? keyed : list.items) } as { items: T[]; total: number } & Record<K, T[]>
}

/**
 * Generic fetch wrapper with error handling and JSON parsing.
 * @param endpoint - API endpoint path (appended to BASE_URL)
 * @param options - Optional fetch options (method, body, headers)
 * @returns Parsed JSON response typed as T
 * @throws {ApiError} When response is not OK or body is invalid
 */
async function fetchData<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetchWithTimeout(buildUrl(endpoint), {
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
  const response = await fetchWithTimeout(buildUrl(endpoint), {
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
 * request, but the result is always a plain array.
 * Applied to every collection endpoint so callers can `.map()`/`.filter()` safely.
 */
async function requestList<T>(endpoint: string, options?: RequestInit): Promise<T[]> {
  return normalizeToArray<T>(await request<unknown>(endpoint, options))
}

/**
 * request, but the result is always `{ items, total }`.
 * Preserves any extra array-valued key the backend used (e.g. `agents`).
 */
async function requestPaged<T>(endpoint: string, options?: RequestInit): Promise<PagedResult<T> & { items: T[]; total: number }> {
  return normalizeToList<T>(await request<unknown>(endpoint, options))
}

/**
 * request, but the result is always `{ items, total }` plus the named collection
 * key the endpoint's public signature promises (e.g. `agents`).
 */
async function requestKeyedList<T, K extends string>(
  endpoint: string,
  key: K,
  options?: RequestInit,
): Promise<{ items: T[]; total: number } & Record<K, T[]>> {
  return normalizeToKeyedList<T, K>(await request<unknown>(endpoint, options), key)
}

/**
 * fetchData, but the result is always `{ items, total }` plus the named collection
 * key the endpoint's public signature promises (e.g. `users`).
 */
async function fetchKeyedList<T, K extends string>(
  endpoint: string,
  key: K,
  options?: RequestInit,
): Promise<{ items: T[]; total: number } & Record<K, T[]>> {
  return normalizeToKeyedList<T, K>(await fetchData<unknown>(endpoint, options), key)
}

/**
 * fetchData, but the result is always a plain array.
 * Applied to every collection endpoint so callers can `.map()`/`.filter()` safely.
 */
async function fetchList<T>(endpoint: string, options?: RequestInit): Promise<T[]> {
  return normalizeToArray<T>(await fetchData<unknown>(endpoint, options))
}

/**
 * fetchData, but the result is always `{ items, total }`.
 */
async function fetchPaged<T>(endpoint: string, options?: RequestInit): Promise<PagedResult<T> & { items: T[]; total: number }> {
  return normalizeToList<T>(await fetchData<unknown>(endpoint, options))
}

/**
 * API client for APEX-OS backend endpoints.
 * All methods return typed data and throw ApiError on failure.
 */
export const api = {
  /** Fetch dashboard metrics, revenue trend, and recent activity. */
  getDashboard: (): Promise<DashboardData> =>
    fetchData<DashboardData>('/dashboards'),

  /** Fetch dashboard widgets. */
  getDashboardWidgets: (): Promise<DashboardWidget[]> =>
    fetchList<DashboardWidget>('/dashboards'),

  /** Fetch accounting data including accounts, journal entries, and trial balance. */
  getAccounting: (): Promise<AccountingData> =>
    fetchData<AccountingData>('/accounts/'),

  /** Create a new accounting entry. */
  createAccountingEntry: (data: Partial<AccountingData>): Promise<AccountingData> =>
    request<AccountingData>('/accounts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing accounting entry by ID. */
  updateAccountingEntry: (id: string, data: Partial<AccountingData>): Promise<AccountingData> =>
    request<AccountingData>(`/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an accounting entry by ID. */
  deleteAccountingEntry: (id: string): Promise<void> =>
    request<void>(`/accounts/${id}`, { method: 'DELETE' }),

  /** Fetch CRM data including leads, opportunities, and forecast. */
  getCRM: (): Promise<CRMData> =>
    fetchData<CRMData>('/leads/'),

  /** Fetch analytics data including KPIs, anomalies, and forecasts. */
  getAnalytics: (): Promise<AnalyticsData> =>
    fetchData<AnalyticsData>('/dashboards'),

  /** Fetch agent reach data including agents, channels, and routes. */
  getAgentReach: (): Promise<AgentReachData> =>
    fetchData<AgentReachData>('/agents/'),

  /** Fetch paginated agent reach agents with optional search and status filter. */
  getAgentReachAgents: (params: { page: number; limit: number; search?: string; status?: string }): Promise<{ agents: Agent[]; total: number }> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.status) sp.set('status', params.status);
    return requestPaged<Agent>(`/agents?${sp}`) as Promise<{ agents: Agent[]; total: number }>;
  },

  /** Create a new agent. */
  createAgent: (data: Omit<Agent, 'id'>): Promise<Agent> =>
    request<Agent>('/agents/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing agent by ID. */
  updateAgent: (id: string, data: Omit<Agent, 'id'>): Promise<Agent> =>
    request<Agent>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an agent by ID. */
  deleteAgent: (id: string): Promise<void> =>
    request<void>(`/agents/${id}`, { method: 'DELETE' }),

  /** Fetch big data platform status including datasets, queries, and storage. */
  getBigData: (): Promise<BigData> =>
    fetchData<BigData>('/datasets'),

  /** Fetch paginated big data datasets with optional search and format filter. */
  getBigDataDatasets: (params: { page: number; limit: number; search?: string; format?: string }): Promise<{ items: BigDataDataset[]; total: number }> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) })
    if (params.search) sp.set('search', params.search)
    if (params.format) sp.set('format', params.format)
    return requestPaged<BigDataDataset>(`/datasets?${sp}`)
  },

  /** Create a new big data dataset. */
  createBigDataDataset: (data: { name: string; description: string; size: number; format: string }): Promise<BigDataDataset> =>
    request<BigDataDataset>('/datasets', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing big data dataset. */
  updateBigDataDataset: (id: string, data: { name: string; description: string; size: number; format: string }): Promise<BigDataDataset> =>
    request<BigDataDataset>(`/datasets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a big data dataset. */
  deleteBigDataDataset: (id: string): Promise<void> =>
    request<void>(`/datasets/${id}`, { method: 'DELETE' }),

  // ── Data Warehouse ──────────────────────────────────────────────────────

  /** List data sources with pagination. */
  listDataSources: (params: { skip?: number; limit?: number }): Promise<DataSource[]> => {
    const sp = new URLSearchParams({ skip: String(params.skip ?? 0), limit: String(params.limit ?? 10) });
    return requestList<DataSource>(`/api/data-warehouse/data-sources?${sp}`);
  },

  /** Get a single data source by ID. */
  getDataSource: (id: number): Promise<DataSource> =>
    request<DataSource>(`/api/data-warehouse/data-sources/${id}`),

  /** Create a new data source. */
  createDataSource: (data: DataSourceInput): Promise<DataSource> =>
    request<DataSource>('/api/data-warehouse/data-sources', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing data source. */
  updateDataSource: (id: number, data: DataSourceInput): Promise<DataSource> =>
    request<DataSource>(`/api/data-warehouse/data-sources/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a data source. */
  deleteDataSource: (id: number): Promise<void> =>
    request<void>(`/api/data-warehouse/data-sources/${id}`, { method: 'DELETE' }),

  /** List ETL jobs with pagination. */
  listETLJobs: (params: { skip?: number; limit?: number }): Promise<ETLJob[]> => {
    const sp = new URLSearchParams({ skip: String(params.skip ?? 0), limit: String(params.limit ?? 10) });
    return requestList<ETLJob>(`/api/data-warehouse/etl-jobs?${sp}`);
  },

  /** Get a single ETL job by ID. */
  getETLJob: (id: number): Promise<ETLJob> =>
    request<ETLJob>(`/api/data-warehouse/etl-jobs/${id}`),

  /** Create a new ETL job. */
  createETLJob: (data: ETLJobInput): Promise<ETLJob> =>
    request<ETLJob>('/api/data-warehouse/etl-jobs', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing ETL job. */
  updateETLJob: (id: number, data: ETLJobInput): Promise<ETLJob> =>
    request<ETLJob>(`/api/data-warehouse/etl-jobs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an ETL job. */
  deleteETLJob: (id: number): Promise<void> =>
    request<void>(`/api/data-warehouse/etl-jobs/${id}`, { method: 'DELETE' }),

  /** List data marts with pagination. */
  listDataMarts: (params: { skip?: number; limit?: number }): Promise<DataMart[]> => {
    const sp = new URLSearchParams({ skip: String(params.skip ?? 0), limit: String(params.limit ?? 10) });
    return requestList<DataMart>(`/api/data-warehouse/data-marts?${sp}`);
  },

  /** Get a single data mart by ID. */
  getDataMart: (id: number): Promise<DataMart> =>
    request<DataMart>(`/api/data-warehouse/data-marts/${id}`),

  /** Create a new data mart. */
  createDataMart: (data: DataMartInput): Promise<DataMart> =>
    request<DataMart>('/api/data-warehouse/data-marts', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing data mart. */
  updateDataMart: (id: number, data: DataMartInput): Promise<DataMart> =>
    request<DataMart>(`/api/data-warehouse/data-marts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a data mart. */
  deleteDataMart: (id: number): Promise<void> =>
    request<void>(`/api/data-warehouse/data-marts/${id}`, { method: 'DELETE' }),

  /** List data models with pagination. */
  listDataModels: (params: { skip?: number; limit?: number }): Promise<DataModel[]> => {
    const sp = new URLSearchParams({ skip: String(params.skip ?? 0), limit: String(params.limit ?? 10) });
    return requestList<DataModel>(`/api/data-warehouse/data-models?${sp}`);
  },

  /** Get a single data model by ID. */
  getDataModel: (id: number): Promise<DataModel> =>
    request<DataModel>(`/api/data-warehouse/data-models/${id}`),

  /** Create a new data model. */
  createDataModel: (data: DataModelInput): Promise<DataModel> =>
    request<DataModel>('/api/data-warehouse/data-models', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing data model. */
  updateDataModel: (id: number, data: DataModelInput): Promise<DataModel> =>
    request<DataModel>(`/api/data-warehouse/data-models/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a data model. */
  deleteDataModel: (id: number): Promise<void> =>
    request<void>(`/api/data-warehouse/data-models/${id}`, { method: 'DELETE' }),

  /** Fetch data science platform status including models, experiments, and features. */
  getDataScience: (): Promise<DataScienceData> =>
    fetchData<DataScienceData>('/models'),

  /** Fetch paginated data science models with optional search and status filter. */
  getDataScienceModels: (params: { page: number; limit: number; search?: string; status?: string }): Promise<{ models: DataScienceModel[]; total: number }> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.status) sp.set('status', params.status);
    return requestPaged<DataScienceModel>(`/models?${sp}`) as Promise<{ models: DataScienceModel[]; total: number }>;
  },

  /** Create a new data science model. */
  createDataScienceModel: (data: DataScienceModelInput): Promise<DataScienceModel> =>
    request<DataScienceModel>('/models', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing data science model. */
  updateDataScienceModel: (id: string, data: DataScienceModelInput): Promise<DataScienceModel> =>
    request<DataScienceModel>(`/models/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a data science model. */
  deleteDataScienceModel: (id: string): Promise<void> =>
    request<void>(`/models/${id}`, { method: 'DELETE' }),

  /** Fetch continuous BI status including dashboards, alerts, and data freshness. */
  getContinuousBI: (options?: RequestInit): Promise<ContinuousBIData> =>
    fetchData<ContinuousBIData>('/reports', options),

  /** Fetch all available data in a single aggregated response. */
  getAll: (): Promise<Record<string, unknown>> =>
    fetchData<Record<string, unknown>>('/dashboards'),

  /** Fetch paginated analytics entries with optional search and category filter. */
  getAnalyticsList: (params: AnalyticsListParams): Promise<AnalyticsListResponse> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.category) sp.set('category', params.category);
    return fetchPaged<AnalyticsEntry>(`/dashboards?${sp}`) as Promise<AnalyticsListResponse>;
  },

  /** Create a new analytics entry. */
  createAnalytics: (data: Omit<AnalyticsEntry, 'id'>): Promise<AnalyticsEntry> =>
    fetchData<AnalyticsEntry>('/dashboards', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Update an existing analytics entry by ID. */
  updateAnalytics: (id: string, data: Omit<AnalyticsEntry, 'id'>): Promise<AnalyticsEntry> =>
    fetchData<AnalyticsEntry>(`/dashboards/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Delete an analytics entry by ID. */
  deleteAnalytics: (id: string): Promise<void> =>
    fetchData<void>(`/dashboards/${id}`, { method: 'DELETE' }),

  /** Fetch paginated users with optional search and filters. */
  getUsers: (params: UserListParams): Promise<UserListResponse> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) });
    if (params.search) sp.set('search', params.search);
    if (params.role) sp.set('role', params.role);
    if (params.status) sp.set('status', params.status);
    return fetchPaged<User>(`/api/users?${sp}`) as Promise<UserListResponse>;
  },

  /** Create a new user. */
  createUser: (data: UserFormData): Promise<User> =>
    fetchData<User>('/api/users/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Update an existing user by ID. */
  updateUser: (id: number, data: UserFormData): Promise<User> =>
    fetchData<User>(`/api/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  /** Delete a user by ID. */
  deleteUser: (id: number): Promise<void> =>
    fetchData<void>(`/api/users/${id}`, { method: 'DELETE' }),

  // ── ContinuousBI Reports CRUD ──────────────────────────────────────────────

  /** Fetch paginated list of ContinuousBI reports. */
  getContinuousBIReports: (params?: { skip?: number; limit?: number; report_type?: string; search?: string }): Promise<ContinuousBIReport[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.report_type) sp.set('report_type', params.report_type)
    if (params?.search) sp.set('search', params.search)
    const qs = sp.toString()
    return requestList<ContinuousBIReport>(`/api/reports${qs ? `?${qs}` : ''}`)
  },

  /** Create a new ContinuousBI report. */
  createContinuousBIReport: (data: ContinuousBIReportInput): Promise<ContinuousBIReport> =>
    request<ContinuousBIReport>('/api/reports', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing ContinuousBI report. */
  updateContinuousBIReport: (id: number, data: ContinuousBIReportInput): Promise<ContinuousBIReport> =>
    request<ContinuousBIReport>(`/api/reports/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a ContinuousBI report. */
  deleteContinuousBIReport: (id: number): Promise<void> =>
    request<void>(`/api/reports/${id}`, { method: 'DELETE' }),

  // ── Leads CRUD ──────────────────────────────────────────────────────────────

  /** Fetch all leads. */
  getLeads: (): Promise<Lead[]> =>
    fetchList<Lead>('/api/leads/'),

  /** Create a new lead. */
  createLead: (data: LeadInput): Promise<Lead> =>
    request<Lead>('/api/leads/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing lead by ID. */
  updateLead: (id: string, data: LeadInput): Promise<Lead> =>
    request<Lead>(`/api/leads/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a lead by ID. */
  deleteLead: (id: string): Promise<void> =>
    request<void>(`/api/leads/${id}`, { method: 'DELETE' }),

  // ── Roles CRUD ──────────────────────────────────────────────────────────────

  /** Fetch all roles. */
  getRoles: (): Promise<Role[]> =>
    fetchList<Role>('/api/roles/'),

  /** Fetch a single role by ID. */
  getRoleById: (id: string): Promise<Role> =>
    fetchData<Role>(`/api/roles/${id}`),

  /** Create a new role. */
  createRole: (data: RoleInput): Promise<Role> =>
    request<Role>('/api/roles/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing role by ID. */
  updateRole: (id: string, data: RoleInput): Promise<Role> =>
    request<Role>(`/api/roles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a role by ID. */
  deleteRole: (id: string): Promise<void> =>
    request<void>(`/api/roles/${id}`, { method: 'DELETE' }),

  // ── Permissions CRUD ────────────────────────────────────────────────────────

  /** Fetch all permissions. */
  getPermissions: (): Promise<Permission[]> =>
    fetchList<Permission>('/api/permissions/'),

  /** Fetch a single permission by ID. */
  getPermissionById: (id: string): Promise<Permission> =>
    fetchData<Permission>(`/api/permissions/${id}`),

  /** Create a new permission. */
  createPermission: (data: PermissionInput): Promise<Permission> =>
    request<Permission>('/api/permissions/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing permission by ID. */
  updatePermission: (id: string, data: PermissionInput): Promise<Permission> =>
    request<Permission>(`/api/permissions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a permission by ID. */
  deletePermission: (id: string): Promise<void> =>
    request<void>(`/api/permissions/${id}`, { method: 'DELETE' }),

  // ── Opportunities CRUD ──────────────────────────────────────────────────────

  /** Fetch all opportunities. */
  getOpportunities: (): Promise<Opportunity[]> =>
    fetchList<Opportunity>('/api/opportunities/'),

  /** Fetch a single opportunity by ID. */
  getOpportunityById: (id: string): Promise<Opportunity> =>
    fetchData<Opportunity>(`/api/opportunities/${id}`),

  /** Create a new opportunity. */
  createOpportunity: (data: OpportunityInput): Promise<Opportunity> =>
    request<Opportunity>('/api/opportunities/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing opportunity by ID. */
  updateOpportunity: (id: string, data: OpportunityInput): Promise<Opportunity> =>
    request<Opportunity>(`/api/opportunities/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an opportunity by ID. */
  deleteOpportunity: (id: string): Promise<void> =>
    request<void>(`/api/opportunities/${id}`, { method: 'DELETE' }),

  // ── Campaigns CRUD ──────────────────────────────────────────────────────────

  /** Fetch all campaigns. */
  getCampaigns: (): Promise<Campaign[]> =>
    fetchList<Campaign>('/api/campaigns/'),

  /** Fetch a single campaign by ID. */
  getCampaignById: (id: string): Promise<Campaign> =>
    fetchData<Campaign>(`/api/campaigns/${id}`),

  /** Create a new campaign. */
  createCampaign: (data: CampaignInput): Promise<Campaign> =>
    request<Campaign>('/api/campaigns/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing campaign by ID. */
  updateCampaign: (id: string, data: CampaignInput): Promise<Campaign> =>
    request<Campaign>(`/api/campaigns/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a campaign by ID. */
  deleteCampaign: (id: string): Promise<void> =>
    request<void>(`/api/campaigns/${id}`, { method: 'DELETE' }),

  // ── Alerts CRUD ─────────────────────────────────────────────────────────────

  /** Fetch all alerts. */
  getAlerts: (): Promise<Alert[]> =>
    fetchList<Alert>('/api/alerts/'),

  /** Fetch a single alert by ID. */
  getAlertById: (id: string): Promise<Alert> =>
    fetchData<Alert>(`/api/alerts/${id}`),

  /** Create a new alert. */
  createAlert: (data: AlertInput): Promise<Alert> =>
    request<Alert>('/api/alerts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing alert by ID. */
  updateAlert: (id: string, data: AlertInput): Promise<Alert> =>
    request<Alert>(`/api/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an alert by ID. */
  deleteAlert: (id: string): Promise<void> =>
    request<void>(`/api/alerts/${id}`, { method: 'DELETE' }),

  // ── Notification Center CRUD ──────────────────────────────────────────────

  /** Fetch paginated notifications with optional read/type filters. */
  getNotifications: (params?: { page?: number; limit?: number; read?: boolean; type?: string }): Promise<{ items: Notification[]; total: number }> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.read != null) sp.set('read', String(params.read));
    if (params?.type) sp.set('type', params.type);
    const qs = sp.toString();
    return requestPaged<Notification>(`/api/notifications${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single notification by ID. */
  getNotification: (id: number): Promise<Notification> =>
    request<Notification>(`/api/notifications/${id}`),

  /** Create a new notification. */
  createNotification: (data: NotificationInput): Promise<Notification> =>
    request<Notification>('/api/notifications', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing notification by ID. */
  updateNotification: (id: number, data: Partial<NotificationInput>): Promise<Notification> =>
    request<Notification>(`/api/notifications/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a notification by ID. */
  deleteNotification: (id: number): Promise<void> =>
    request<void>(`/api/notifications/${id}`, { method: 'DELETE' }),

  /** Fetch paginated notification templates. */
  getNotificationTemplates: (params?: { page?: number; limit?: number; type?: string }): Promise<{ items: NotificationTemplate[]; total: number }> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.type) sp.set('type', params.type);
    const qs = sp.toString();
    return requestPaged<NotificationTemplate>(`/api/notifications/templates${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single notification template by ID. */
  getNotificationTemplate: (id: number): Promise<NotificationTemplate> =>
    request<NotificationTemplate>(`/api/notifications/templates/${id}`),

  /** Create a new notification template. */
  createNotificationTemplate: (data: NotificationTemplateInput): Promise<NotificationTemplate> =>
    request<NotificationTemplate>('/api/notifications/templates', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing notification template by ID. */
  updateNotificationTemplate: (id: number, data: Partial<NotificationTemplateInput>): Promise<NotificationTemplate> =>
    request<NotificationTemplate>(`/api/notifications/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a notification template by ID. */
  deleteNotificationTemplate: (id: number): Promise<void> =>
    request<void>(`/api/notifications/templates/${id}`, { method: 'DELETE' }),

  /** Fetch paginated notification rules. */
  getNotificationRules: (params?: { page?: number; limit?: number; is_active?: boolean }): Promise<{ items: NotificationRule[]; total: number }> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.is_active != null) sp.set('is_active', String(params.is_active));
    const qs = sp.toString();
    return requestPaged<NotificationRule>(`/api/notifications/rules${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single notification rule by ID. */
  getNotificationRule: (id: number): Promise<NotificationRule> =>
    request<NotificationRule>(`/api/notifications/rules/${id}`),

  /** Create a new notification rule. */
  createNotificationRule: (data: NotificationRuleInput): Promise<NotificationRule> =>
    request<NotificationRule>('/api/notifications/rules', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing notification rule by ID. */
  updateNotificationRule: (id: number, data: Partial<NotificationRuleInput>): Promise<NotificationRule> =>
    request<NotificationRule>(`/api/notifications/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a notification rule by ID. */
  deleteNotificationRule: (id: number): Promise<void> =>
    request<void>(`/api/notifications/rules/${id}`, { method: 'DELETE' }),

  /** Fetch paginated notification preferences. */
  getNotificationPreferences: (params?: { page?: number; limit?: number; user_id?: string }): Promise<{ items: NotificationPreference[]; total: number }> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.user_id) sp.set('user_id', params.user_id);
    const qs = sp.toString();
    return requestPaged<NotificationPreference>(`/api/notifications/preferences${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single notification preference by ID. */
  getNotificationPreference: (id: number): Promise<NotificationPreference> =>
    request<NotificationPreference>(`/api/notifications/preferences/${id}`),

  /** Create a new notification preference. */
  createNotificationPreference: (data: NotificationPreferenceInput): Promise<NotificationPreference> =>
    request<NotificationPreference>('/api/notifications/preferences', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing notification preference by ID. */
  updateNotificationPreference: (id: number, data: Partial<NotificationPreferenceInput>): Promise<NotificationPreference> =>
    request<NotificationPreference>(`/api/notifications/preferences/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a notification preference by ID. */
  deleteNotificationPreference: (id: number): Promise<void> =>
    request<void>(`/api/notifications/preferences/${id}`, { method: 'DELETE' }),

  // ── Compliance CRUD ────────────────────────────────────────────────────────

  /** Fetch all compliance frameworks. */
  getComplianceFrameworks: (): Promise<ComplianceFramework[]> =>
    fetchList<ComplianceFramework>('/api/compliance/frameworks/'),

  /** Fetch a single compliance framework by ID. */
  getComplianceFrameworkById: (id: string): Promise<ComplianceFramework> =>
    fetchData<ComplianceFramework>(`/api/compliance/frameworks/${id}`),

  /** Create a new compliance framework. */
  createComplianceFramework: (data: ComplianceFrameworkInput): Promise<ComplianceFramework> =>
    request<ComplianceFramework>('/api/compliance/frameworks/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance framework. */
  updateComplianceFramework: (id: string, data: ComplianceFrameworkInput): Promise<ComplianceFramework> =>
    request<ComplianceFramework>(`/api/compliance/frameworks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance framework. */
  deleteComplianceFramework: (id: string): Promise<void> =>
    request<void>(`/api/compliance/frameworks/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance controls. */
  getComplianceControls: (): Promise<Control[]> =>
    fetchList<Control>('/api/compliance/controls/'),

  /** Fetch a single compliance control by ID. */
  getComplianceControlById: (id: string): Promise<Control> =>
    fetchData<Control>(`/api/compliance/controls/${id}`),

  /** Create a new compliance control. */
  createComplianceControl: (data: ControlInput): Promise<Control> =>
    request<Control>('/api/compliance/controls/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance control. */
  updateComplianceControl: (id: string, data: ControlInput): Promise<Control> =>
    request<Control>(`/api/compliance/controls/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance control. */
  deleteComplianceControl: (id: string): Promise<void> =>
    request<void>(`/api/compliance/controls/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance audits. */
  getComplianceAudits: (): Promise<Audit[]> =>
    fetchList<Audit>('/api/compliance/audits/'),

  /** Fetch a single compliance audit by ID. */
  getComplianceAuditById: (id: string): Promise<Audit> =>
    fetchData<Audit>(`/api/compliance/audits/${id}`),

  /** Create a new compliance audit. */
  createComplianceAudit: (data: AuditInput): Promise<Audit> =>
    request<Audit>('/api/compliance/audits/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance audit. */
  updateComplianceAudit: (id: string, data: AuditInput): Promise<Audit> =>
    request<Audit>(`/api/compliance/audits/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance audit. */
  deleteComplianceAudit: (id: string): Promise<void> =>
    request<void>(`/api/compliance/audits/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance findings. */
  getComplianceFindings: (): Promise<Finding[]> =>
    fetchList<Finding>('/api/compliance/findings/'),

  /** Fetch a single compliance finding by ID. */
  getComplianceFindingById: (id: string): Promise<Finding> =>
    fetchData<Finding>(`/api/compliance/findings/${id}`),

  /** Create a new compliance finding. */
  createComplianceFinding: (data: FindingInput): Promise<Finding> =>
    request<Finding>('/api/compliance/findings/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance finding. */
  updateComplianceFinding: (id: string, data: FindingInput): Promise<Finding> =>
    request<Finding>(`/api/compliance/findings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance finding. */
  deleteComplianceFinding: (id: string): Promise<void> =>
    request<void>(`/api/compliance/findings/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance remediation plans. */
  getComplianceRemediationPlans: (): Promise<RemediationPlan[]> =>
    fetchList<RemediationPlan>('/api/compliance/remediation-plans/'),

  /** Fetch a single compliance remediation plan by ID. */
  getComplianceRemediationPlanById: (id: string): Promise<RemediationPlan> =>
    fetchData<RemediationPlan>(`/api/compliance/remediation-plans/${id}`),

  /** Create a new compliance remediation plan. */
  createComplianceRemediationPlan: (data: RemediationPlanInput): Promise<RemediationPlan> =>
    request<RemediationPlan>('/api/compliance/remediation-plans/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance remediation plan. */
  updateComplianceRemediationPlan: (id: string, data: RemediationPlanInput): Promise<RemediationPlan> =>
    request<RemediationPlan>(`/api/compliance/remediation-plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance remediation plan. */
  deleteComplianceRemediationPlan: (id: string): Promise<void> =>
    request<void>(`/api/compliance/remediation-plans/${id}`, { method: 'DELETE' }),

  // ── Budgeting CRUD ──────────────────────────────────────────────────────────

  /** Fetch all budgets. */
  getBudgets: (): Promise<Budget[]> =>
    fetchList<Budget>('/api/budgeting/budgets/'),

  /** Fetch a single budget by ID. */
  getBudgetById: (id: number): Promise<Budget> =>
    fetchData<Budget>(`/api/budgeting/budgets/${id}`),

  /** Create a new budget. */
  createBudget: (data: Partial<Budget>): Promise<Budget> =>
    request<Budget>('/api/budgeting/budgets/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing budget. */
  updateBudget: (id: number, data: Partial<Budget>): Promise<Budget> =>
    request<Budget>(`/api/budgeting/budgets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a budget. */
  deleteBudget: (id: number): Promise<void> =>
    request<void>(`/api/budgeting/budgets/${id}`, { method: 'DELETE' }),

  /** Fetch all budget lines. */
  getBudgetLines: (): Promise<BudgetLine[]> =>
    fetchList<BudgetLine>('/api/budgeting/budget-lines/'),

  /** Fetch a single budget line by ID. */
  getBudgetLineById: (id: number): Promise<BudgetLine> =>
    fetchData<BudgetLine>(`/api/budgeting/budget-lines/${id}`),

  /** Create a new budget line. */
  createBudgetLine: (data: Partial<BudgetLine>): Promise<BudgetLine> =>
    request<BudgetLine>('/api/budgeting/budget-lines/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing budget line. */
  updateBudgetLine: (id: number, data: Partial<BudgetLine>): Promise<BudgetLine> =>
    request<BudgetLine>(`/api/budgeting/budget-lines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a budget line. */
  deleteBudgetLine: (id: number): Promise<void> =>
    request<void>(`/api/budgeting/budget-lines/${id}`, { method: 'DELETE' }),

  /** Fetch all cost centers. */
  getCostCenters: (): Promise<CostCenter[]> =>
    fetchList<CostCenter>('/api/budgeting/cost-centers/'),

  /** Fetch a single cost center by ID. */
  getCostCenterById: (id: number): Promise<CostCenter> =>
    fetchData<CostCenter>(`/api/budgeting/cost-centers/${id}`),

  /** Create a new cost center. */
  createCostCenter: (data: Partial<CostCenter>): Promise<CostCenter> =>
    request<CostCenter>('/api/budgeting/cost-centers/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing cost center. */
  updateCostCenter: (id: number, data: Partial<CostCenter>): Promise<CostCenter> =>
    request<CostCenter>(`/api/budgeting/cost-centers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a cost center. */
  deleteCostCenter: (id: number): Promise<void> =>
    request<void>(`/api/budgeting/cost-centers/${id}`, { method: 'DELETE' }),

  /** Fetch all variance analysis records. */
  getVarianceAnalysis: (): Promise<VarianceAnalysis[]> =>
    fetchList<VarianceAnalysis>('/api/budgeting/variance-analysis/'),

  /** Fetch a single variance analysis by ID. */
  getVarianceAnalysisById: (id: number): Promise<VarianceAnalysis> =>
    fetchData<VarianceAnalysis>(`/api/budgeting/variance-analysis/${id}`),

  /** Create a new variance analysis record. */
  createVarianceAnalysis: (data: Partial<VarianceAnalysis>): Promise<VarianceAnalysis> =>
    request<VarianceAnalysis>('/api/budgeting/variance-analysis/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing variance analysis record. */
  updateVarianceAnalysis: (id: number, data: Partial<VarianceAnalysis>): Promise<VarianceAnalysis> =>
    request<VarianceAnalysis>(`/api/budgeting/variance-analysis/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a variance analysis record. */
  deleteVarianceAnalysis: (id: number): Promise<void> =>
    request<void>(`/api/budgeting/variance-analysis/${id}`, { method: 'DELETE' }),

  // ── Inventory: Products CRUD ──────────────────────────────────────────────

  /** Fetch paginated products with optional category/supplier filter. */
  getProducts: (params?: { skip?: number; limit?: number; category_id?: number; supplier_id?: number }): Promise<Product[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.category_id != null) sp.set('category_id', String(params.category_id))
    if (params?.supplier_id != null) sp.set('supplier_id', String(params.supplier_id))
    const qs = sp.toString()
    return requestList<Product>(`/api/inventory/products${qs ? `?${qs}` : ''}`)
  },

  /** Fetch a single product by ID. */
  getProduct: (id: number): Promise<Product> =>
    request<Product>(`/api/inventory/products/${id}`),

  /** Create a new product. */
  createProduct: (data: ProductInput): Promise<Product> =>
    request<Product>('/api/inventory/products', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing product. */
  updateProduct: (id: number, data: Partial<ProductInput>): Promise<Product> =>
    request<Product>(`/api/inventory/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a product. */
  deleteProduct: (id: number): Promise<void> =>
    request<void>(`/api/inventory/products/${id}`, { method: 'DELETE' }),

  // ── Inventory: Categories CRUD ────────────────────────────────────────────

  /** Fetch all categories. */
  getCategories: (): Promise<Category[]> =>
    requestList<Category>('/api/inventory/categories'),

  /** Fetch a single category by ID. */
  getCategory: (id: number): Promise<Category> =>
    request<Category>(`/api/inventory/categories/${id}`),

  /** Create a new category. */
  createCategory: (data: CategoryInput): Promise<Category> =>
    request<Category>('/api/inventory/categories', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing category. */
  updateCategory: (id: number, data: Partial<CategoryInput>): Promise<Category> =>
    request<Category>(`/api/inventory/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a category. */
  deleteCategory: (id: number): Promise<void> =>
    request<void>(`/api/inventory/categories/${id}`, { method: 'DELETE' }),

  // ── Inventory: Suppliers CRUD ─────────────────────────────────────────────

  /** Fetch all suppliers. */
  getSuppliers: (): Promise<Supplier[]> =>
    requestList<Supplier>('/api/inventory/suppliers'),

  /** Fetch a single supplier by ID. */
  getSupplier: (id: number): Promise<Supplier> =>
    request<Supplier>(`/api/inventory/suppliers/${id}`),

  /** Create a new supplier. */
  createSupplier: (data: SupplierInput): Promise<Supplier> =>
    request<Supplier>('/api/inventory/suppliers', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing supplier. */
  updateSupplier: (id: number, data: Partial<SupplierInput>): Promise<Supplier> =>
    request<Supplier>(`/api/inventory/suppliers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a supplier. */
  deleteSupplier: (id: number): Promise<void> =>
    request<void>(`/api/inventory/suppliers/${id}`, { method: 'DELETE' }),

  // ── Inventory: Stock Orders CRUD ──────────────────────────────────────────

  /** Fetch paginated stock orders with optional status/product filter. */
  getStockOrders: (params?: { skip?: number; limit?: number; status?: string; product_id?: number }): Promise<StockOrder[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.status) sp.set('status', params.status)
    if (params?.product_id != null) sp.set('product_id', String(params.product_id))
    const qs = sp.toString()
    return requestList<StockOrder>(`/api/inventory/stock-orders${qs ? `?${qs}` : ''}`)
  },

  /** Fetch a single stock order by ID. */
  getStockOrder: (id: number): Promise<StockOrder> =>
    request<StockOrder>(`/api/inventory/stock-orders/${id}`),

  /** Create a new stock order. */
  createStockOrder: (data: StockOrderInput): Promise<StockOrder> =>
    request<StockOrder>('/api/inventory/stock-orders', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing stock order. */
  updateStockOrder: (id: number, data: Partial<StockOrderInput>): Promise<StockOrder> =>
    request<StockOrder>(`/api/inventory/stock-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a stock order. */
  deleteStockOrder: (id: number): Promise<void> =>
    request<void>(`/api/inventory/stock-orders/${id}`, { method: 'DELETE' }),

  // ── Inventory: Warehouse Locations CRUD ───────────────────────────────────

  /** Fetch all warehouse locations. */
  getWarehouseLocations: (): Promise<WarehouseLocation[]> =>
    requestList<WarehouseLocation>('/api/inventory/warehouse-locations'),

  /** Fetch a single warehouse location by ID. */
  getWarehouseLocation: (id: number): Promise<WarehouseLocation> =>
    request<WarehouseLocation>(`/api/inventory/warehouse-locations/${id}`),

  /** Create a new warehouse location. */
  createWarehouseLocation: (data: WarehouseLocationInput): Promise<WarehouseLocation> =>
    request<WarehouseLocation>('/api/inventory/warehouse-locations', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing warehouse location. */
  updateWarehouseLocation: (id: number, data: Partial<WarehouseLocationInput>): Promise<WarehouseLocation> =>
    request<WarehouseLocation>(`/api/inventory/warehouse-locations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a warehouse location. */
  deleteWarehouseLocation: (id: number): Promise<void> =>
    request<void>(`/api/inventory/warehouse-locations/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Suppliers CRUD ──────────────────────────────────────────

  /** Fetch all supply chain suppliers. */
  getSupplyChainSuppliers: (): Promise<Supplier[]> =>
    requestList<Supplier>('/api/supply-chain/suppliers'),

  /** Fetch a single supply chain supplier by ID. */
  getSupplyChainSupplier: (id: number): Promise<Supplier> =>
    request<Supplier>(`/api/supply-chain/suppliers/${id}`),

  /** Create a new supply chain supplier. */
  createSupplyChainSupplier: (data: SupplierInput): Promise<Supplier> =>
    request<Supplier>('/api/supply-chain/suppliers', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing supply chain supplier. */
  updateSupplyChainSupplier: (id: number, data: Partial<SupplierInput>): Promise<Supplier> =>
    request<Supplier>(`/api/supply-chain/suppliers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a supply chain supplier. */
  deleteSupplyChainSupplier: (id: number): Promise<void> =>
    request<void>(`/api/supply-chain/suppliers/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Purchase Orders CRUD ────────────────────────────────────

  /** Fetch all purchase orders. */
  getPurchaseOrders: (): Promise<PurchaseOrder[]> =>
    requestList<PurchaseOrder>('/api/supply-chain/purchase-orders'),

  /** Fetch a single purchase order by ID. */
  getPurchaseOrder: (id: number): Promise<PurchaseOrder> =>
    request<PurchaseOrder>(`/api/supply-chain/purchase-orders/${id}`),

  /** Create a new purchase order. */
  createPurchaseOrder: (data: PurchaseOrderInput): Promise<PurchaseOrder> =>
    request<PurchaseOrder>('/api/supply-chain/purchase-orders', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing purchase order. */
  updatePurchaseOrder: (id: number, data: Partial<PurchaseOrderInput>): Promise<PurchaseOrder> =>
    request<PurchaseOrder>(`/api/supply-chain/purchase-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a purchase order. */
  deletePurchaseOrder: (id: number): Promise<void> =>
    request<void>(`/api/supply-chain/purchase-orders/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Shipments CRUD ───────────────────────────────────────────

  /** Fetch all shipments. */
  getShipments: (): Promise<Shipment[]> =>
    requestList<Shipment>('/api/supply-chain/shipments'),

  /** Fetch a single shipment by ID. */
  getShipment: (id: number): Promise<Shipment> =>
    request<Shipment>(`/api/supply-chain/shipments/${id}`),

  /** Create a new shipment. */
  createShipment: (data: ShipmentInput): Promise<Shipment> =>
    request<Shipment>('/api/supply-chain/shipments', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing shipment. */
  updateShipment: (id: number, data: Partial<ShipmentInput>): Promise<Shipment> =>
    request<Shipment>(`/api/supply-chain/shipments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a shipment. */
  deleteShipment: (id: number): Promise<void> =>
    request<void>(`/api/supply-chain/shipments/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Logistics Routes CRUD ───────────────────────────────────

  /** Fetch all logistics routes. */
  getLogisticsRoutes: (): Promise<LogisticsRoute[]> =>
    requestList<LogisticsRoute>('/api/supply-chain/logistics-routes'),

  /** Fetch a single logistics route by ID. */
  getLogisticsRoute: (id: number): Promise<LogisticsRoute> =>
    request<LogisticsRoute>(`/api/supply-chain/logistics-routes/${id}`),

  /** Create a new logistics route. */
  createLogisticsRoute: (data: LogisticsRouteInput): Promise<LogisticsRoute> =>
    request<LogisticsRoute>('/api/supply-chain/logistics-routes', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing logistics route. */
  updateLogisticsRoute: (id: number, data: Partial<LogisticsRouteInput>): Promise<LogisticsRoute> =>
    request<LogisticsRoute>(`/api/supply-chain/logistics-routes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a logistics route. */
  deleteLogisticsRoute: (id: number): Promise<void> =>
    request<void>(`/api/supply-chain/logistics-routes/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Production Lines CRUD ─────────────────────────────────

  /** Fetch all production lines. */
  getProductionLines: (): Promise<ProductionLine[]> =>
    requestList<ProductionLine>('/api/manufacturing/production-lines/'),

  /** Fetch a single production line by ID. */
  getProductionLine: (id: number): Promise<ProductionLine> =>
    request<ProductionLine>(`/api/manufacturing/production-lines/${id}`),

  /** Create a new production line. */
  createProductionLine: (data: ProductionLineInput): Promise<ProductionLine> =>
    request<ProductionLine>('/api/manufacturing/production-lines/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing production line. */
  updateProductionLine: (id: number, data: Partial<ProductionLineInput>): Promise<ProductionLine> =>
    request<ProductionLine>(`/api/manufacturing/production-lines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a production line. */
  deleteProductionLine: (id: number): Promise<void> =>
    request<void>(`/api/manufacturing/production-lines/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Work Orders CRUD ───────────────────────────────────────

  /** Fetch all work orders. */
  getWorkOrders: (): Promise<WorkOrder[]> =>
    requestList<WorkOrder>('/api/manufacturing/work-orders/'),

  /** Fetch a single work order by ID. */
  getWorkOrder: (id: number): Promise<WorkOrder> =>
    request<WorkOrder>(`/api/manufacturing/work-orders/${id}`),

  /** Create a new work order. */
  createWorkOrder: (data: WorkOrderInput): Promise<WorkOrder> =>
    request<WorkOrder>('/api/manufacturing/work-orders/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing work order. */
  updateWorkOrder: (id: number, data: Partial<WorkOrderInput>): Promise<WorkOrder> =>
    request<WorkOrder>(`/api/manufacturing/work-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a work order. */
  deleteWorkOrder: (id: number): Promise<void> =>
    request<void>(`/api/manufacturing/work-orders/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Quality Checks CRUD ────────────────────────────────────

  /** Fetch all quality checks. */
  getQualityChecks: (): Promise<QualityCheck[]> =>
    requestList<QualityCheck>('/api/manufacturing/quality-checks/'),

  /** Fetch a single quality check by ID. */
  getQualityCheck: (id: number): Promise<QualityCheck> =>
    request<QualityCheck>(`/api/manufacturing/quality-checks/${id}`),

  /** Create a new quality check. */
  createQualityCheck: (data: QualityCheckInput): Promise<QualityCheck> =>
    request<QualityCheck>('/api/manufacturing/quality-checks/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing quality check. */
  updateQualityCheck: (id: number, data: Partial<QualityCheckInput>): Promise<QualityCheck> =>
    request<QualityCheck>(`/api/manufacturing/quality-checks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a quality check. */
  deleteQualityCheck: (id: number): Promise<void> =>
    request<void>(`/api/manufacturing/quality-checks/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Bills of Materials CRUD ────────────────────────────────

  /** Fetch all bills of materials. */
  getBillsOfMaterials: (): Promise<BillOfMaterials[]> =>
    requestList<BillOfMaterials>('/api/manufacturing/bills-of-materials/'),

  /** Fetch a single bill of materials by ID. */
  getBillOfMaterials: (id: number): Promise<BillOfMaterials> =>
    request<BillOfMaterials>(`/api/manufacturing/bills-of-materials/${id}`),

  /** Create a new bill of materials. */
  createBillOfMaterials: (data: BillOfMaterialsInput): Promise<BillOfMaterials> =>
    request<BillOfMaterials>('/api/manufacturing/bills-of-materials/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing bill of materials. */
  updateBillOfMaterials: (id: number, data: Partial<BillOfMaterialsInput>): Promise<BillOfMaterials> =>
    request<BillOfMaterials>(`/api/manufacturing/bills-of-materials/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a bill of materials. */
  deleteBillOfMaterials: (id: number): Promise<void> =>
    request<void>(`/api/manufacturing/bills-of-materials/${id}`, { method: 'DELETE' }),

  // ── Reporting CRUD ─────────────────────────────────────────────────────────

  /** Fetch paginated reports. */
  getReports: (params?: { page?: number; limit?: number; search?: string }): Promise<Report[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.search) sp.set('search', params.search);
    const qs = sp.toString();
    return requestList<Report>(`/api/reporting/reports${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single report by ID. */
  getReportById: (id: number): Promise<Report> =>
    request<Report>(`/api/reporting/reports/${id}`),

  /** Create a new report. */
  createReport: (data: ReportInput): Promise<Report> =>
    request<Report>('/api/reporting/reports', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing report by ID. */
  updateReport: (id: number, data: ReportInput): Promise<Report> =>
    request<Report>(`/api/reporting/reports/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a report by ID. */
  deleteReport: (id: number): Promise<void> =>
    request<void>(`/api/reporting/reports/${id}`, { method: 'DELETE' }),

  /** Fetch paginated report templates. */
  getReportTemplates: (params?: { page?: number; limit?: number }): Promise<ReportTemplate[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return requestList<ReportTemplate>(`/api/reporting/templates${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single report template by ID. */
  getReportTemplateById: (id: number): Promise<ReportTemplate> =>
    request<ReportTemplate>(`/api/reporting/templates/${id}`),

  /** Create a new report template. */
  createReportTemplate: (data: ReportTemplateInput): Promise<ReportTemplate> =>
    request<ReportTemplate>('/api/reporting/templates', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing report template by ID. */
  updateReportTemplate: (id: number, data: ReportTemplateInput): Promise<ReportTemplate> =>
    request<ReportTemplate>(`/api/reporting/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a report template by ID. */
  deleteReportTemplate: (id: number): Promise<void> =>
    request<void>(`/api/reporting/templates/${id}`, { method: 'DELETE' }),

  /** Fetch paginated scheduled reports. */
  getScheduledReports: (params?: { page?: number; limit?: number }): Promise<ScheduledReport[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return requestList<ScheduledReport>(`/api/reporting/scheduled${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single scheduled report by ID. */
  getScheduledReportById: (id: number): Promise<ScheduledReport> =>
    request<ScheduledReport>(`/api/reporting/scheduled/${id}`),

  /** Create a new scheduled report. */
  createScheduledReport: (data: ScheduledReportInput): Promise<ScheduledReport> =>
    request<ScheduledReport>('/api/reporting/scheduled', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing scheduled report by ID. */
  updateScheduledReport: (id: number, data: ScheduledReportInput): Promise<ScheduledReport> =>
    request<ScheduledReport>(`/api/reporting/scheduled/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a scheduled report by ID. */
  deleteScheduledReport: (id: number): Promise<void> =>
    request<void>(`/api/reporting/scheduled/${id}`, { method: 'DELETE' }),

  /** Fetch paginated report subscriptions. */
  getReportSubscriptions: (params?: { page?: number; limit?: number }): Promise<ReportSubscription[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return requestList<ReportSubscription>(`/api/reporting/subscriptions${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single report subscription by ID. */
  getReportSubscriptionById: (id: number): Promise<ReportSubscription> =>
    request<ReportSubscription>(`/api/reporting/subscriptions/${id}`),

  /** Create a new report subscription. */
  createReportSubscription: (data: ReportSubscriptionInput): Promise<ReportSubscription> =>
    request<ReportSubscription>('/api/reporting/subscriptions', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing report subscription by ID. */
  updateReportSubscription: (id: number, data: ReportSubscriptionInput): Promise<ReportSubscription> =>
    request<ReportSubscription>(`/api/reporting/subscriptions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a report subscription by ID. */
  deleteReportSubscription: (id: number): Promise<void> =>
    request<void>(`/api/reporting/subscriptions/${id}`, { method: 'DELETE' }),

  // ── Asset Management CRUD ───────────────────────────────────────────────────

  /** Fetch all assets. */
  getAssets: (): Promise<Asset[]> =>
    fetchList<Asset>('/api/assets/'),

  /** Fetch a single asset by ID. */
  getAssetById: (id: number): Promise<Asset> =>
    fetchData<Asset>(`/api/assets/${id}`),

  /** Create a new asset. */
  createAsset: (data: AssetInput): Promise<Asset> =>
    request<Asset>('/api/assets/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing asset by ID. */
  updateAsset: (id: number, data: AssetInput): Promise<Asset> =>
    request<Asset>(`/api/assets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an asset by ID. */
  deleteAsset: (id: number): Promise<void> =>
    request<void>(`/api/assets/${id}`, { method: 'DELETE' }),

  /** Fetch all asset categories. */
  getAssetCategories: (): Promise<AssetCategory[]> =>
    fetchList<AssetCategory>('/api/assets/categories/'),

  /** Fetch a single asset category by ID. */
  getAssetCategoryById: (id: number): Promise<AssetCategory> =>
    fetchData<AssetCategory>(`/api/assets/categories/${id}`),

  /** Create a new asset category. */
  createAssetCategory: (data: AssetCategoryInput): Promise<AssetCategory> =>
    request<AssetCategory>('/api/assets/categories/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing asset category by ID. */
  updateAssetCategory: (id: number, data: AssetCategoryInput): Promise<AssetCategory> =>
    request<AssetCategory>(`/api/assets/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an asset category by ID. */
  deleteAssetCategory: (id: number): Promise<void> =>
    request<void>(`/api/assets/categories/${id}`, { method: 'DELETE' }),

  /** Fetch all maintenance schedules. */
  getMaintenanceSchedules: (): Promise<MaintenanceSchedule[]> =>
    fetchList<MaintenanceSchedule>('/api/assets/maintenance/'),

  /** Fetch a single maintenance schedule by ID. */
  getMaintenanceScheduleById: (id: number): Promise<MaintenanceSchedule> =>
    fetchData<MaintenanceSchedule>(`/api/assets/maintenance/${id}`),

  /** Create a new maintenance schedule. */
  createMaintenanceSchedule: (data: MaintenanceScheduleInput): Promise<MaintenanceSchedule> =>
    request<MaintenanceSchedule>('/api/assets/maintenance/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing maintenance schedule by ID. */
  updateMaintenanceSchedule: (id: number, data: MaintenanceScheduleInput): Promise<MaintenanceSchedule> =>
    request<MaintenanceSchedule>(`/api/assets/maintenance/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a maintenance schedule by ID. */
  deleteMaintenanceSchedule: (id: number): Promise<void> =>
    request<void>(`/api/assets/maintenance/${id}`, { method: 'DELETE' }),

  /** Fetch all depreciation records. */
  getDepreciationRecords: (): Promise<DepreciationRecord[]> =>
    fetchList<DepreciationRecord>('/api/assets/depreciation/'),

  /** Fetch a single depreciation record by ID. */
  getDepreciationRecordById: (id: number): Promise<DepreciationRecord> =>
    fetchData<DepreciationRecord>(`/api/assets/depreciation/${id}`),

  /** Create a new depreciation record. */
  createDepreciationRecord: (data: DepreciationRecordInput): Promise<DepreciationRecord> =>
    request<DepreciationRecord>('/api/assets/depreciation/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing depreciation record by ID. */
  updateDepreciationRecord: (id: number, data: DepreciationRecordInput): Promise<DepreciationRecord> =>
    request<DepreciationRecord>(`/api/assets/depreciation/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a depreciation record by ID. */
  deleteDepreciationRecord: (id: number): Promise<void> =>
    request<void>(`/api/assets/depreciation/${id}`, { method: 'DELETE' }),

  // ── IoT CRUD ───────────────────────────────────────────────────────────────

  /** Fetch all IoT devices. */
  getIoTDevices: (): Promise<IoTDevice[]> =>
    fetchList<IoTDevice>('/api/iot/devices/'),

  /** Fetch a single IoT device by ID. */
  getIoTDeviceById: (id: number): Promise<IoTDevice> =>
    fetchData<IoTDevice>(`/api/iot/devices/${id}`),

  /** Create a new IoT device. */
  createIoTDevice: (data: IoTDeviceInput): Promise<IoTDevice> =>
    request<IoTDevice>('/api/iot/devices/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT device. */
  updateIoTDevice: (id: number, data: IoTDeviceInput): Promise<IoTDevice> =>
    request<IoTDevice>(`/api/iot/devices/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT device. */
  deleteIoTDevice: (id: number): Promise<void> =>
    request<void>(`/api/iot/devices/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT sensors. */
  getIoTSensors: (): Promise<IoTSensor[]> =>
    fetchList<IoTSensor>('/api/iot/sensors/'),

  /** Fetch a single IoT sensor by ID. */
  getIoTSensorById: (id: number): Promise<IoTSensor> =>
    fetchData<IoTSensor>(`/api/iot/sensors/${id}`),

  /** Create a new IoT sensor. */
  createIoTSensor: (data: IoTSensorInput): Promise<IoTSensor> =>
    request<IoTSensor>('/api/iot/sensors/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT sensor. */
  updateIoTSensor: (id: number, data: IoTSensorInput): Promise<IoTSensor> =>
    request<IoTSensor>(`/api/iot/sensors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT sensor. */
  deleteIoTSensor: (id: number): Promise<void> =>
    request<void>(`/api/iot/sensors/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT telemetry data. */
  getIoTTelemetry: (): Promise<IoTTelemetry[]> =>
    fetchList<IoTTelemetry>('/api/iot/telemetry/'),

  /** Fetch a single IoT telemetry entry by ID. */
  getIoTTelemetryById: (id: number): Promise<IoTTelemetry> =>
    fetchData<IoTTelemetry>(`/api/iot/telemetry/${id}`),

  /** Create a new IoT telemetry entry. */
  createIoTTelemetry: (data: IoTTelemetryInput): Promise<IoTTelemetry> =>
    request<IoTTelemetry>('/api/iot/telemetry/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT telemetry entry. */
  updateIoTTelemetry: (id: number, data: IoTTelemetryInput): Promise<IoTTelemetry> =>
    request<IoTTelemetry>(`/api/iot/telemetry/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT telemetry entry. */
  deleteIoTTelemetry: (id: number): Promise<void> =>
    request<void>(`/api/iot/telemetry/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT alerts. */
  getIoTAlerts: (): Promise<IoTAlert[]> =>
    fetchList<IoTAlert>('/api/iot/alerts/'),

  /** Fetch a single IoT alert by ID. */
  getIoTAlertById: (id: number): Promise<IoTAlert> =>
    fetchData<IoTAlert>(`/api/iot/alerts/${id}`),

  /** Create a new IoT alert. */
  createIoTAlert: (data: IoTAlertInput): Promise<IoTAlert> =>
    request<IoTAlert>('/api/iot/alerts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT alert. */
  updateIoTAlert: (id: number, data: IoTAlertInput): Promise<IoTAlert> =>
    request<IoTAlert>(`/api/iot/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT alert. */
  deleteIoTAlert: (id: number): Promise<void> =>
    request<void>(`/api/iot/alerts/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT device groups. */
  getIoTGroups: (): Promise<IoTDeviceGroup[]> =>
    fetchList<IoTDeviceGroup>('/api/iot/groups/'),

  /** Fetch a single IoT device group by ID. */
  getIoTGroupById: (id: number): Promise<IoTDeviceGroup> =>
    fetchData<IoTDeviceGroup>(`/api/iot/groups/${id}`),

  /** Create a new IoT device group. */
  createIoTGroup: (data: IoTGroupInput): Promise<IoTDeviceGroup> =>
    request<IoTDeviceGroup>('/api/iot/groups/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT device group. */
  updateIoTGroup: (id: number, data: IoTGroupInput): Promise<IoTDeviceGroup> =>
    request<IoTDeviceGroup>(`/api/iot/groups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT device group. */
  deleteIoTGroup: (id: number): Promise<void> =>
    request<void>(`/api/iot/groups/${id}`, { method: 'DELETE' }),

  // ── HR: Employees CRUD ─────────────────────────────────────────────────────

  /** Fetch all employees. */
  getEmployees: (): Promise<Employee[]> =>
    requestList<Employee>('/api/hr/employees'),

  /** Fetch a single employee by ID. */
  getEmployee: (id: number): Promise<Employee> =>
    request<Employee>(`/api/hr/employees/${id}`),

  /** Create a new employee. */
  createEmployee: (data: EmployeeInput): Promise<Employee> =>
    request<Employee>('/api/hr/employees', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing employee. */
  updateEmployee: (id: number, data: Partial<EmployeeInput>): Promise<Employee> =>
    request<Employee>(`/api/hr/employees/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an employee. */
  deleteEmployee: (id: number): Promise<void> =>
    request<void>(`/api/hr/employees/${id}`, { method: 'DELETE' }),

  // ── HR: Departments CRUD ───────────────────────────────────────────────────

  /** Fetch all departments. */
  getDepartments: (): Promise<Department[]> =>
    requestList<Department>('/api/hr/departments'),

  /** Fetch a single department by ID. */
  getDepartment: (id: number): Promise<Department> =>
    request<Department>(`/api/hr/departments/${id}`),

  /** Create a new department. */
  createDepartment: (data: DepartmentInput): Promise<Department> =>
    request<Department>('/api/hr/departments', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing department. */
  updateDepartment: (id: number, data: Partial<DepartmentInput>): Promise<Department> =>
    request<Department>(`/api/hr/departments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a department. */
  deleteDepartment: (id: number): Promise<void> =>
    request<void>(`/api/hr/departments/${id}`, { method: 'DELETE' }),

  // ── IoT: Devices & Sensors (short aliases) ─────────────────────────────────

  /** Fetch all devices (alias for getIoTDevices). */
  getDevices: (): Promise<IoTDevice[]> =>
    requestList<IoTDevice>('/api/iot/devices/'),

  /** Fetch all sensors (alias for getIoTSensors). */
  getSensors: (): Promise<IoTSensor[]> =>
    requestList<IoTSensor>('/api/iot/sensors/'),

  // ── Compliance: Controls (short alias) ─────────────────────────────────────

  /** Fetch all controls (alias for getComplianceControls). */
  getControls: (): Promise<Control[]> =>
    requestList<Control>('/api/compliance/controls/'),

  // ── Cost Management CRUD ───────────────────────────────────────────────────

  /** Fetch all cost allocations. */
  getCostAllocations: (): Promise<CostAllocation[]> =>
    fetchList<CostAllocation>('/api/cost-management/cost-allocations/'),

  /** Fetch a single cost allocation by ID. */
  getCostAllocationById: (id: number): Promise<CostAllocation> =>
    fetchData<CostAllocation>(`/api/cost-management/cost-allocations/${id}`),

  /** Create a new cost allocation. */
  createCostAllocation: (data: Partial<CostAllocation>): Promise<CostAllocation> =>
    request<CostAllocation>('/api/cost-management/cost-allocations/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing cost allocation. */
  updateCostAllocation: (id: number, data: Partial<CostAllocation>): Promise<CostAllocation> =>
    request<CostAllocation>(`/api/cost-management/cost-allocations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a cost allocation. */
  deleteCostAllocation: (id: number): Promise<void> =>
    request<void>(`/api/cost-management/cost-allocations/${id}`, { method: 'DELETE' }),

  /** Fetch all cost forecasts. */
  getCostForecasts: (): Promise<CostForecast[]> =>
    fetchList<CostForecast>('/api/cost-management/cost-forecasts/'),

  /** Fetch a single cost forecast by ID. */
  getCostForecastById: (id: number): Promise<CostForecast> =>
    fetchData<CostForecast>(`/api/cost-management/cost-forecasts/${id}`),

  /** Create a new cost forecast. */
  createCostForecast: (data: Partial<CostForecast>): Promise<CostForecast> =>
    request<CostForecast>('/api/cost-management/cost-forecasts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing cost forecast. */
  updateCostForecast: (id: number, data: Partial<CostForecast>): Promise<CostForecast> =>
    request<CostForecast>(`/api/cost-management/cost-forecasts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a cost forecast. */
  deleteCostForecast: (id: number): Promise<void> =>
    request<void>(`/api/cost-management/cost-forecasts/${id}`, { method: 'DELETE' }),

  /** Fetch all cost variances. */
  getCostVariances: (): Promise<CostVariance[]> =>
    fetchList<CostVariance>('/api/cost-management/cost-variances/'),

  /** Fetch a single cost variance by ID. */
  getCostVarianceById: (id: number): Promise<CostVariance> =>
    fetchData<CostVariance>(`/api/cost-management/cost-variances/${id}`),

  /** Create a new cost variance. */
  createCostVariance: (data: Partial<CostVariance>): Promise<CostVariance> =>
    request<CostVariance>('/api/cost-management/cost-variances/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing cost variance. */
  updateCostVariance: (id: number, data: Partial<CostVariance>): Promise<CostVariance> =>
    request<CostVariance>(`/api/cost-management/cost-variances/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a cost variance. */
  deleteCostVariance: (id: number): Promise<void> =>
    request<void>(`/api/cost-management/cost-variances/${id}`, { method: 'DELETE' }),

  // ── Project Management CRUD ────────────────────────────────────────────────

  /** Fetch all projects. */
  getProjects: (): Promise<Project[]> =>
    requestList<Project>('/api/projects'),

  /** Fetch a single project by ID. */
  getProject: (id: number): Promise<Project> =>
    request<Project>(`/api/projects/${id}`),

  /** Create a new project. */
  createProject: (data: ProjectInput): Promise<Project> =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing project. */
  updateProject: (id: number, data: Partial<ProjectInput>): Promise<Project> =>
    request<Project>(`/api/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a project. */
  deleteProject: (id: number): Promise<void> =>
    request<void>(`/api/projects/${id}`, { method: 'DELETE' }),

  /** Fetch all milestones. */
  getMilestones: (): Promise<Milestone[]> =>
    requestList<Milestone>('/api/project-mgmt/milestones'),

  /** Fetch a single milestone by ID. */
  getMilestone: (id: number): Promise<Milestone> =>
    request<Milestone>(`/api/project-mgmt/milestones/${id}`),

  /** Create a new milestone. */
  createMilestone: (data: MilestoneInput): Promise<Milestone> =>
    request<Milestone>('/api/project-mgmt/milestones', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing milestone. */
  updateMilestone: (id: number, data: Partial<MilestoneInput>): Promise<Milestone> =>
    request<Milestone>(`/api/project-mgmt/milestones/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a milestone. */
  deleteMilestone: (id: number): Promise<void> =>
    request<void>(`/api/project-mgmt/milestones/${id}`, { method: 'DELETE' }),

  // ── Knowledge Base CRUD ────────────────────────────────────────────────────

  /** Fetch all KB categories. */
  getKBCategories: (): Promise<KBCategory[]> =>
    requestList<KBCategory>('/api/knowledge-base/categories'),

  /** Fetch a single KB category by ID. */
  getKBCategory: (id: number): Promise<KBCategory> =>
    request<KBCategory>(`/api/knowledge-base/categories/${id}`),

  /** Create a new KB category. */
  createKBCategory: (data: KBCategoryInput): Promise<KBCategory> =>
    request<KBCategory>('/api/knowledge-base/categories', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing KB category. */
  updateKBCategory: (id: number, data: Partial<KBCategoryInput>): Promise<KBCategory> =>
    request<KBCategory>(`/api/knowledge-base/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a KB category. */
  deleteKBCategory: (id: number): Promise<void> =>
    request<void>(`/api/knowledge-base/categories/${id}`, { method: 'DELETE' }),

  /** Fetch all KB tags. */
  getKBTags: (): Promise<KBTag[]> =>
    requestList<KBTag>('/api/knowledge-base/tags'),

  /** Fetch a single KB tag by ID. */
  getKBTag: (id: number): Promise<KBTag> =>
    request<KBTag>(`/api/knowledge-base/tags/${id}`),

  /** Create a new KB tag. */
  createKBTag: (data: KBTagInput): Promise<KBTag> =>
    request<KBTag>('/api/knowledge-base/tags', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing KB tag. */
  updateKBTag: (id: number, data: Partial<KBTagInput>): Promise<KBTag> =>
    request<KBTag>(`/api/knowledge-base/tags/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a KB tag. */
  deleteKBTag: (id: number): Promise<void> =>
    request<void>(`/api/knowledge-base/tags/${id}`, { method: 'DELETE' }),

  /** Fetch KB articles with optional filters. */
  getKBArticles: (params?: { skip?: number; limit?: number; category_id?: number; search?: string }): Promise<KBArticle[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.category_id != null) sp.set('category_id', String(params.category_id))
    if (params?.search) sp.set('search', params.search)
    const qs = sp.toString()
    return requestList<KBArticle>(`/api/knowledge-base/articles${qs ? `?${qs}` : ''}`)
  },

  /** Fetch a single KB article by ID. */
  getKBArticle: (id: number): Promise<KBArticle> =>
    request<KBArticle>(`/api/knowledge-base/articles/${id}`),

  /** Create a new KB article. */
  createKBArticle: (data: KBArticleInput): Promise<KBArticle> =>
    request<KBArticle>('/api/knowledge-base/articles', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing KB article. */
  updateKBArticle: (id: number, data: Partial<KBArticleInput>): Promise<KBArticle> =>
    request<KBArticle>(`/api/knowledge-base/articles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a KB article. */
  deleteKBArticle: (id: number): Promise<void> =>
    request<void>(`/api/knowledge-base/articles/${id}`, { method: 'DELETE' }),

  /** Fetch KB comments, optionally filtered by article. */
  getKBComments: (articleId?: number): Promise<KBComment[]> => {
    const qs = articleId != null ? `?article_id=${articleId}` : ''
    return requestList<KBComment>(`/api/knowledge-base/comments${qs}`)
  },

  /** Fetch a single KB comment by ID. */
  getKBComment: (id: number): Promise<KBComment> =>
    request<KBComment>(`/api/knowledge-base/comments/${id}`),

  /** Create a new KB comment. */
  createKBComment: (data: KBCommentInput): Promise<KBComment> =>
    request<KBComment>('/api/knowledge-base/comments', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing KB comment. */
  updateKBComment: (id: number, data: Partial<KBCommentInput>): Promise<KBComment> =>
    request<KBComment>(`/api/knowledge-base/comments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a KB comment. */
  deleteKBComment: (id: number): Promise<void> =>
    request<void>(`/api/knowledge-base/comments/${id}`, { method: 'DELETE' }),

  // ── Integrations CRUD ──────────────────────────────────────────────────────

  /** Fetch all integrations. */
  getIntegrations: (): Promise<Integration[]> =>
    requestList<Integration>('/api/integrations/'),

  /** Fetch a single integration by ID. */
  getIntegration: (id: number): Promise<Integration> =>
    request<Integration>(`/api/integrations/${id}`),

  /** Create a new integration. */
  createIntegration: (data: IntegrationInput): Promise<Integration> =>
    request<Integration>('/api/integrations/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing integration. */
  updateIntegration: (id: number, data: Partial<IntegrationInput>): Promise<Integration> =>
    request<Integration>(`/api/integrations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an integration. */
  deleteIntegration: (id: number): Promise<void> =>
    request<void>(`/api/integrations/${id}`, { method: 'DELETE' }),

  /** Fetch all API keys. */
  getApiKeys: (): Promise<ApiKey[]> =>
    requestList<ApiKey>('/api/integrations/api-keys/'),

  /** Fetch a single API key by ID. */
  getApiKey: (id: number): Promise<ApiKey> =>
    request<ApiKey>(`/api/integrations/api-keys/${id}`),

  /** Create a new API key. */
  createApiKey: (data: ApiKeyInput): Promise<ApiKey> =>
    request<ApiKey>('/api/integrations/api-keys/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing API key. */
  updateApiKey: (id: number, data: Partial<ApiKeyInput>): Promise<ApiKey> =>
    request<ApiKey>(`/api/integrations/api-keys/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an API key. */
  deleteApiKey: (id: number): Promise<void> =>
    request<void>(`/api/integrations/api-keys/${id}`, { method: 'DELETE' }),

  /** Fetch all webhooks. */
  getWebhooks: (): Promise<Webhook[]> =>
    requestList<Webhook>('/api/integrations/webhooks/'),

  /** Fetch a single webhook by ID. */
  getWebhook: (id: number): Promise<Webhook> =>
    request<Webhook>(`/api/integrations/webhooks/${id}`),

  /** Create a new webhook. */
  createWebhook: (data: WebhookInput): Promise<Webhook> =>
    request<Webhook>('/api/integrations/webhooks/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing webhook. */
  updateWebhook: (id: number, data: Partial<WebhookInput>): Promise<Webhook> =>
    request<Webhook>(`/api/integrations/webhooks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a webhook. */
  deleteWebhook: (id: number): Promise<void> =>
    request<void>(`/api/integrations/webhooks/${id}`, { method: 'DELETE' }),

  /** Fetch all sync jobs. */
  getSyncJobs: (): Promise<SyncJob[]> =>
    requestList<SyncJob>('/api/integrations/sync-jobs/'),

  /** Fetch a single sync job by ID. */
  getSyncJob: (id: number): Promise<SyncJob> =>
    request<SyncJob>(`/api/integrations/sync-jobs/${id}`),

  /** Create a new sync job. */
  createSyncJob: (data: SyncJobInput): Promise<SyncJob> =>
    request<SyncJob>('/api/integrations/sync-jobs/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing sync job. */
  updateSyncJob: (id: number, data: Partial<SyncJobInput>): Promise<SyncJob> =>
    request<SyncJob>(`/api/integrations/sync-jobs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a sync job. */
  deleteSyncJob: (id: number): Promise<void> =>
    request<void>(`/api/integrations/sync-jobs/${id}`, { method: 'DELETE' }),

  // ── Export Templates ──────────────────────────────────────────────────────

  /** List export templates with pagination. */
  getExportTemplates: (params: { page: number; limit: number }): Promise<ExportTemplate[]> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) })
    return requestList<ExportTemplate>(`/api/export-templates/templates?${sp}`)
  },

  /** Get a single export template by ID. */
  getExportTemplate: (id: number): Promise<ExportTemplate> =>
    request<ExportTemplate>(`/api/export-templates/templates/${id}`),

  /** Create a new export template. */
  createExportTemplate: (data: ExportTemplateInput): Promise<ExportTemplate> =>
    request<ExportTemplate>('/api/export-templates/templates', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing export template. */
  updateExportTemplate: (id: number, data: Partial<ExportTemplateInput>): Promise<ExportTemplate> =>
    request<ExportTemplate>(`/api/export-templates/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an export template. */
  deleteExportTemplate: (id: number): Promise<void> =>
    request<void>(`/api/export-templates/templates/${id}`, { method: 'DELETE' }),

  /** List export jobs with pagination. */
  getExportJobs: (params: { page: number; limit: number }): Promise<ExportJob[]> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) })
    return requestList<ExportJob>(`/api/export-templates/jobs?${sp}`)
  },

  /** Get a single export job by ID. */
  getExportJob: (id: number): Promise<ExportJob> =>
    request<ExportJob>(`/api/export-templates/jobs/${id}`),

  /** Create a new export job. */
  createExportJob: (data: ExportJobInput): Promise<ExportJob> =>
    request<ExportJob>('/api/export-templates/jobs', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing export job. */
  updateExportJob: (id: number, data: Partial<ExportJobInput>): Promise<ExportJob> =>
    request<ExportJob>(`/api/export-templates/jobs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an export job. */
  deleteExportJob: (id: number): Promise<void> =>
    request<void>(`/api/export-templates/jobs/${id}`, { method: 'DELETE' }),

  /** List export schedules with pagination. */
  getExportSchedules: (params: { page: number; limit: number }): Promise<ExportSchedule[]> => {
    const sp = new URLSearchParams({ page: String(params.page), limit: String(params.limit) })
    return requestList<ExportSchedule>(`/api/export-templates/schedules?${sp}`)
  },

  /** Get a single export schedule by ID. */
  getExportSchedule: (id: number): Promise<ExportSchedule> =>
    request<ExportSchedule>(`/api/export-templates/schedules/${id}`),

  /** Create a new export schedule. */
  createExportSchedule: (data: ExportScheduleInput): Promise<ExportSchedule> =>
    request<ExportSchedule>('/api/export-templates/schedules', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing export schedule. */
  updateExportSchedule: (id: number, data: Partial<ExportScheduleInput>): Promise<ExportSchedule> =>
    request<ExportSchedule>(`/api/export-templates/schedules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an export schedule. */
  deleteExportSchedule: (id: number): Promise<void> =>
    request<void>(`/api/export-templates/schedules/${id}`, { method: 'DELETE' }),

  // ── Disaster Recovery CRUD ─────────────────────────────────────────────────

  /** Fetch all DR plans. */
  getDRPlans: (): Promise<DRPlan[]> =>
    fetchList<DRPlan>('/api/disaster-recovery/dr-plans/'),

  /** Fetch a single DR plan by ID. */
  getDRPlanById: (id: string): Promise<DRPlan> =>
    fetchData<DRPlan>(`/api/disaster-recovery/dr-plans/${id}`),

  /** Create a new DR plan. */
  createDRPlan: (data: DRPlanInput): Promise<DRPlan> =>
    request<DRPlan>('/api/disaster-recovery/dr-plans/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing DR plan. */
  updateDRPlan: (id: string, data: DRPlanInput): Promise<DRPlan> =>
    request<DRPlan>(`/api/disaster-recovery/dr-plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a DR plan. */
  deleteDRPlan: (id: string): Promise<void> =>
    request<void>(`/api/disaster-recovery/dr-plans/${id}`, { method: 'DELETE' }),

  /** Fetch all backup schedules. */
  getBackupSchedules: (): Promise<BackupSchedule[]> =>
    fetchList<BackupSchedule>('/api/disaster-recovery/backup-schedules/'),

  /** Fetch a single backup schedule by ID. */
  getBackupScheduleById: (id: string): Promise<BackupSchedule> =>
    fetchData<BackupSchedule>(`/api/disaster-recovery/backup-schedules/${id}`),

  /** Create a new backup schedule. */
  createBackupSchedule: (data: BackupScheduleInput): Promise<BackupSchedule> =>
    request<BackupSchedule>('/api/disaster-recovery/backup-schedules/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing backup schedule. */
  updateBackupSchedule: (id: string, data: BackupScheduleInput): Promise<BackupSchedule> =>
    request<BackupSchedule>(`/api/disaster-recovery/backup-schedules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a backup schedule. */
  deleteBackupSchedule: (id: string): Promise<void> =>
    request<void>(`/api/disaster-recovery/backup-schedules/${id}`, { method: 'DELETE' }),

  /** Fetch all recovery procedures. */
  getRecoveryProcedures: (): Promise<RecoveryProcedure[]> =>
    fetchList<RecoveryProcedure>('/api/disaster-recovery/recovery-procedures/'),

  /** Fetch a single recovery procedure by ID. */
  getRecoveryProcedureById: (id: string): Promise<RecoveryProcedure> =>
    fetchData<RecoveryProcedure>(`/api/disaster-recovery/recovery-procedures/${id}`),

  /** Create a new recovery procedure. */
  createRecoveryProcedure: (data: RecoveryProcedureInput): Promise<RecoveryProcedure> =>
    request<RecoveryProcedure>('/api/disaster-recovery/recovery-procedures/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing recovery procedure. */
  updateRecoveryProcedure: (id: string, data: RecoveryProcedureInput): Promise<RecoveryProcedure> =>
    request<RecoveryProcedure>(`/api/disaster-recovery/recovery-procedures/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a recovery procedure. */
  deleteRecoveryProcedure: (id: string): Promise<void> =>
    request<void>(`/api/disaster-recovery/recovery-procedures/${id}`, { method: 'DELETE' }),

  /** Fetch all DR tests. */
  getDRTests: (): Promise<DRTest[]> =>
    fetchList<DRTest>('/api/disaster-recovery/dr-tests/'),

  /** Fetch a single DR test by ID. */
  getDRTestById: (id: string): Promise<DRTest> =>
    fetchData<DRTest>(`/api/disaster-recovery/dr-tests/${id}`),

  /** Create a new DR test. */
  createDRTest: (data: DRTestInput): Promise<DRTest> =>
    request<DRTest>('/api/disaster-recovery/dr-tests/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing DR test. */
  updateDRTest: (id: string, data: DRTestInput): Promise<DRTest> =>
    request<DRTest>(`/api/disaster-recovery/dr-tests/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a DR test. */
  deleteDRTest: (id: string): Promise<void> =>
    request<void>(`/api/disaster-recovery/dr-tests/${id}`, { method: 'DELETE' }),

  // ── Capacity Planning CRUD ─────────────────────────────────────────────────

  /** Fetch all capacity plans. */
  getCapacityPlans: (): Promise<CapacityPlan[]> =>
    requestList<CapacityPlan>('/api/capacity-planning/capacity-plans/'),

  /** Fetch a single capacity plan by ID. */
  getCapacityPlan: (id: number): Promise<CapacityPlan> =>
    request<CapacityPlan>(`/api/capacity-planning/capacity-plans/${id}`),

  /** Create a new capacity plan. */
  createCapacityPlan: (data: Partial<CapacityPlan>): Promise<CapacityPlan> =>
    request<CapacityPlan>('/api/capacity-planning/capacity-plans/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing capacity plan. */
  updateCapacityPlan: (id: number, data: Partial<CapacityPlan>): Promise<CapacityPlan> =>
    request<CapacityPlan>(`/api/capacity-planning/capacity-plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a capacity plan. */
  deleteCapacityPlan: (id: number): Promise<void> =>
    request<void>(`/api/capacity-planning/capacity-plans/${id}`, { method: 'DELETE' }),

  /** Fetch all resource allocations. */
  getResourceAllocations: (): Promise<ResourceAllocation[]> =>
    requestList<ResourceAllocation>('/api/capacity-planning/resource-allocations/'),

  /** Fetch a single resource allocation by ID. */
  getResourceAllocation: (id: number): Promise<ResourceAllocation> =>
    request<ResourceAllocation>(`/api/capacity-planning/resource-allocations/${id}`),

  /** Create a new resource allocation. */
  createResourceAllocation: (data: Partial<ResourceAllocation>): Promise<ResourceAllocation> =>
    request<ResourceAllocation>('/api/capacity-planning/resource-allocations/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing resource allocation. */
  updateResourceAllocation: (id: number, data: Partial<ResourceAllocation>): Promise<ResourceAllocation> =>
    request<ResourceAllocation>(`/api/capacity-planning/resource-allocations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a resource allocation. */
  deleteResourceAllocation: (id: number): Promise<void> =>
    request<void>(`/api/capacity-planning/resource-allocations/${id}`, { method: 'DELETE' }),

  /** Fetch all forecasts. */
  getForecasts: (): Promise<Forecast[]> =>
    requestList<Forecast>('/api/capacity-planning/forecasts/'),

  /** Fetch a single forecast by ID. */
  getForecast: (id: number): Promise<Forecast> =>
    request<Forecast>(`/api/capacity-planning/forecasts/${id}`),

  /** Create a new forecast. */
  createForecast: (data: Partial<Forecast>): Promise<Forecast> =>
    request<Forecast>('/api/capacity-planning/forecasts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing forecast. */
  updateForecast: (id: number, data: Partial<Forecast>): Promise<Forecast> =>
    request<Forecast>(`/api/capacity-planning/forecasts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a forecast. */
  deleteForecast: (id: number): Promise<void> =>
    request<void>(`/api/capacity-planning/forecasts/${id}`, { method: 'DELETE' }),

  /** Fetch all scenarios. */
  getScenarios: (): Promise<Scenario[]> =>
    requestList<Scenario>('/api/capacity-planning/scenarios/'),

  /** Fetch a single scenario by ID. */
  getScenario: (id: number): Promise<Scenario> =>
    request<Scenario>(`/api/capacity-planning/scenarios/${id}`),

  /** Create a new scenario. */
  createScenario: (data: Partial<Scenario>): Promise<Scenario> =>
    request<Scenario>('/api/capacity-planning/scenarios/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing scenario. */
  updateScenario: (id: number, data: Partial<Scenario>): Promise<Scenario> =>
    request<Scenario>(`/api/capacity-planning/scenarios/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a scenario. */
  deleteScenario: (id: number): Promise<void> =>
    request<void>(`/api/capacity-planning/scenarios/${id}`, { method: 'DELETE' }),

  // ── Monitoring CRUD ─────────────────────────────────────────────────────────

  /** Fetch all monitors. */
  getMonitors: (options?: RequestInit): Promise<Monitor[]> =>
    requestList<Monitor>('/api/monitoring/monitors', options),

  /** Fetch a single monitor by ID. */
  getMonitor: (id: number): Promise<Monitor> =>
    request<Monitor>(`/api/monitoring/monitors/${id}`),

  /** Create a new monitor. */
  createMonitor: (data: MonitorInput): Promise<Monitor> =>
    request<Monitor>('/api/monitoring/monitors', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing monitor. */
  updateMonitor: (id: number, data: Partial<MonitorInput>): Promise<Monitor> =>
    request<Monitor>(`/api/monitoring/monitors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a monitor. */
  deleteMonitor: (id: number): Promise<void> =>
    request<void>(`/api/monitoring/monitors/${id}`, { method: 'DELETE' }),

  /** Fetch all alert rules. */
  getAlertRules: (options?: RequestInit): Promise<AlertRule[]> =>
    requestList<AlertRule>('/api/monitoring/alert-rules', options),

  /** Fetch a single alert rule by ID. */
  getAlertRule: (id: number): Promise<AlertRule> =>
    request<AlertRule>(`/api/monitoring/alert-rules/${id}`),

  /** Create a new alert rule. */
  createAlertRule: (data: AlertRuleInput): Promise<AlertRule> =>
    request<AlertRule>('/api/monitoring/alert-rules', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing alert rule. */
  updateAlertRule: (id: number, data: Partial<AlertRuleInput>): Promise<AlertRule> =>
    request<AlertRule>(`/api/monitoring/alert-rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an alert rule. */
  deleteAlertRule: (id: number): Promise<void> =>
    request<void>(`/api/monitoring/alert-rules/${id}`, { method: 'DELETE' }),

  /** Fetch all dashboards. */
  getDashboards: (options?: RequestInit): Promise<Dashboard[]> =>
    requestList<Dashboard>('/api/monitoring/dashboards', options),

  /** Create a new dashboard. */
  createDashboard: (data: DashboardInput): Promise<Dashboard> =>
    request<Dashboard>('/api/monitoring/dashboards', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing dashboard. */
  updateDashboard: (id: number, data: Partial<DashboardInput>): Promise<Dashboard> =>
    request<Dashboard>(`/api/monitoring/dashboards/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a dashboard. */
  deleteDashboard: (id: number): Promise<void> =>
    request<void>(`/api/monitoring/dashboards/${id}`, { method: 'DELETE' }),

  /** Fetch all metrics. */
  getMetrics: (options?: RequestInit): Promise<Metric[]> =>
    requestList<Metric>('/api/monitoring/metrics', options),

  /** Fetch a single metric by ID. */
  getMetric: (id: number): Promise<Metric> =>
    request<Metric>(`/api/monitoring/metrics/${id}`),

  /** Create a new metric. */
  createMetric: (data: MetricInput): Promise<Metric> =>
    request<Metric>('/api/monitoring/metrics', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing metric. */
  updateMetric: (id: number, data: Partial<MetricInput>): Promise<Metric> =>
    request<Metric>(`/api/monitoring/metrics/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a metric. */
  deleteMetric: (id: number): Promise<void> =>
    request<void>(`/api/monitoring/metrics/${id}`, { method: 'DELETE' }),
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

export interface DashboardWidget {
  id: string
  title: string
  type: 'metric' | 'chart' | 'table' | 'text'
  value: string
  change: number
  trend: 'up' | 'down'
  color: string
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
  agent_type: string;
  status: string;
  description: string;
  createdAt: string;
  messages_processed: number;
  latency_ms: number;
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

export interface ComplianceFramework {
  id: number
  name: string
  version: string
  description: string
  status: string
  created_at: string
}

export interface ComplianceFrameworkInput {
  name: string
  version?: string
  description?: string
  status?: string
}

export interface Control {
  id: number
  framework_id: number
  name: string
  description: string
  status: string
  owner: string
  created_at: string
}

export interface ControlInput {
  framework_id: number
  name: string
  description?: string
  status?: string
  owner?: string
}

export interface Audit {
  id: number
  framework_id: number
  name: string
  auditor: string
  start_date: string
  end_date: string
  status: string
  result: string | null
  created_at: string
}

export interface AuditInput {
  framework_id: number
  name: string
  auditor?: string
  start_date?: string
  end_date?: string
  status?: string
  result?: string | null
}

export interface Finding {
  id: number
  audit_id: number
  title: string
  description: string
  severity: string
  status: string
  assigned_to: string
  due_date: string
  created_at: string
}

export interface FindingInput {
  audit_id: number
  title: string
  description?: string
  severity?: string
  status?: string
  assigned_to?: string
  due_date?: string
}

export interface RemediationPlan {
  id: number
  finding_id: number
  title: string
  description: string
  status: string
  owner: string
  target_date: string
  created_at: string
}

export interface RemediationPlanInput {
  finding_id: number
  title: string
  description?: string
  status?: string
  owner?: string
  target_date?: string
}

export interface IoTDevice {
  id: number
  name: string
  type: string
  status: string
  location: string
  group_id?: number
  last_seen: string
}

export interface IoTDeviceInput {
  name: string
  type: string
  status: string
  location: string
  group_id?: number
}

export interface IoTSensor {
  id: number
  device_id: number
  name: string
  unit: string
  min_val: number
  max_val: number
  calibration_date?: string
}

export interface IoTSensorInput {
  device_id: number
  name: string
  unit: string
  min_val: number
  max_val: number
  calibration_date?: string
}

export interface IoTTelemetry {
  id: number
  sensor_id: number
  value: number
  timestamp: string
  quality: string
}

export interface IoTTelemetryInput {
  sensor_id: number
  value: number
  quality: string
}

export interface IoTAlert {
  id: number
  device_id: number
  rule: string
  severity: string
  message: string
  is_active: boolean
  created_at: string
}

export interface IoTAlertInput {
  device_id: number
  rule: string
  severity: string
  message: string
  is_active: boolean
}

export interface IoTDeviceGroup {
  id: number
  name: string
  description: string
  color: string
}

export interface IoTGroupInput {
  name: string
  description: string
  color: string
}

export interface Budget {
  id: number
  name: string
  fiscal_year: number
  status: string
  total_budgeted: number
  total_actual: number
  currency: string
  start_date?: string
  end_date?: string
  created_at: string
}

export interface BudgetLine {
  id: number
  budget_id: number
  cost_center_id: number
  category: string
  description?: string
  budgeted_amount: number
  actual_amount: number
  period?: string
  created_at: string
}

export interface CostCenter {
  id: number
  name: string
  code: string
  manager?: string
  department?: string
  created_at: string
}

export interface VarianceAnalysis {
  id: number
  budget_id: number
  budget_line_id: number
  period: string
  budgeted_amount: number
  actual_amount: number
  variance_amount: number
  variance_percent: number
  status: string
  notes?: string
  created_at: string
}

// ── Cost Management Types ─────────────────────────────────────────────────────

export interface CostCenter {
  id: number;
  name: string;
  code: string;
  manager?: string;
  department?: string;
  created_at: string;
}

export interface CostAllocation {
  id: number;
  cost_center_id: number;
  allocation_name: string;
  amount: number;
  period?: string;
  description?: string;
  created_at: string;
}

export interface CostForecast {
  id: number;
  cost_center_id: number;
  forecast_name: string;
  period: string;
  forecast_amount: number;
  actual_amount: number;
  created_at: string;
}

export interface CostVariance {
  id: number;
  cost_center_id: number;
  period: string;
  budgeted_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_percent: number;
  status: string;
  notes?: string;
  created_at: string;
}

// ── Inventory Types ───────────────────────────────────────────────────────────

export interface Product {
  id: number
  name: string
  sku: string
  description?: string | null
  category_id?: number | null
  supplier_id?: number | null
  quantity: number
  price: number
  cost?: number | null
  warehouse_location_id?: number | null
  reorder_level: number
  created_at?: string
  updated_at?: string
}

export interface ProductInput {
  name: string
  sku: string
  description?: string
  category_id?: number
  supplier_id?: number
  quantity: number
  price: number
  cost?: number
  warehouse_location_id?: number
  reorder_level: number
}

export interface Category {
  id: number
  name: string
  description?: string | null
  created_at?: string
  updated_at?: string
}

export interface CategoryInput {
  name: string
  description?: string
}

export interface Supplier {
  id: number
  name: string
  contact_email?: string | null
  contact_phone?: string | null
  address?: string | null
  created_at?: string
  updated_at?: string
}

export interface SupplierInput {
  name: string
  contact_email?: string
  contact_phone?: string
  address?: string
}

export interface StockOrder {
  id: number
  product_id: number
  supplier_id?: number | null
  quantity: number
  unit_cost: number
  status: string
  notes?: string | null
  created_at?: string
  updated_at?: string
}

export interface StockOrderInput {
  product_id: number
  supplier_id?: number
  quantity: number
  unit_cost: number
  status: string
  notes?: string
}

export interface WarehouseLocation {
  id: number
  name: string
  code: string
  description?: string | null
  created_at?: string
  updated_at?: string
}

export interface WarehouseLocationInput {
  name: string
  code: string
  description?: string
}

// ── Supply Chain Types ────────────────────────────────────────────────────────

export interface PurchaseOrder {
  id: number
  supplier_id: number
  product_name: string
  quantity: number
  unit_price: number
  total_price: number
  status: string
  expected_delivery?: string | null
  created_at?: string
  updated_at?: string
}

export interface PurchaseOrderInput {
  supplier_id: number
  product_name: string
  quantity: number
  unit_price: number
  status: string
  expected_delivery?: string
}

export interface Shipment {
  id: number
  purchase_order_id: number
  origin: string
  destination: string
  carrier?: string | null
  tracking_number?: string | null
  status: string
  shipped_date?: string | null
  estimated_arrival?: string | null
  created_at?: string
  updated_at?: string
}

export interface ShipmentInput {
  purchase_order_id: number
  origin: string
  destination: string
  carrier?: string
  tracking_number?: string
  status: string
  shipped_date?: string
  estimated_arrival?: string
}

export interface LogisticsRoute {
  id: number
  name: string
  origin: string
  destination: string
  distance_km?: number | null
  estimated_duration_hours?: number | null
  transport_mode?: string | null
  cost?: number | null
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface LogisticsRouteInput {
  name: string
  origin: string
  destination: string
  distance_km?: number
  estimated_duration_hours?: number
  transport_mode?: string
  cost?: number
  is_active?: boolean
}

// ── Reporting Types ───────────────────────────────────────────────────────────

export interface Report {
  id: number
  name: string
  description?: string
  report_type: string
  config?: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ReportInput {
  name: string
  description?: string
  report_type: string
  config?: Record<string, unknown>
  is_active: boolean
}

export interface ReportTemplate {
  id: number
  name: string
  description?: string
  category: string
  query?: string
  parameters?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ReportTemplateInput {
  name: string
  description?: string
  category: string
  query?: string
  parameters?: Record<string, unknown>
}

export interface ScheduledReport {
  id: number
  report_id: number
  name: string
  cron_expression: string
  recipients: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ScheduledReportInput {
  report_id: number
  name: string
  cron_expression: string
  recipients: string[]
  is_active: boolean
}

export interface ReportSubscription {
  id: number
  user_id: number
  report_id: number
  delivery_method: string
  frequency: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ReportSubscriptionInput {
  user_id: number
  report_id: number
  delivery_method: string
  frequency: string
  is_active: boolean
}

// ── Manufacturing Types ──────────────────────────────────────────────────────

export interface ProductionLine {
  id: number
  name: string
  code: string
  status: string
  capacity_per_hour: number
  location?: string
  supervisor?: string
  created_at?: string
  updated_at?: string
}

export interface ProductionLineInput {
  name: string
  code: string
  status: string
  capacity_per_hour: number
  location?: string
  supervisor?: string
}

export interface WorkOrder {
  id: number
  product_name: string
  quantity: number
  production_line_id: number
  priority: string
  status: string
  due_date?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export interface WorkOrderInput {
  product_name: string
  quantity: number
  production_line_id: number
  priority: string
  status: string
  due_date?: string
  notes?: string
}

export interface QualityCheck {
  id: number
  work_order_id: number
  inspector: string
  result: string
  defect_count: number
  notes?: string
  checked_at?: string
}

export interface QualityCheckInput {
  work_order_id: number
  inspector: string
  result: string
  defect_count: number
  notes?: string
}

export interface BOMItem {
  material_name: string
  quantity: number
  unit: string
}

export interface BillOfMaterials {
  id: number
  product_name: string
  version: string
  items: BOMItem[]
  notes?: string
  created_at?: string
  updated_at?: string
}

export interface BillOfMaterialsInput {
  product_name: string
  version: string
  items: BOMItem[]
  notes?: string
}

// ── Asset Management Types ────────────────────────────────────────────────────

export interface Asset {
  id: number
  name: string
  asset_tag: string
  category_id: number
  purchase_date: string
  purchase_cost: number
  salvage_value: number
  status: string
  location?: string
  description?: string
  created_at?: string
  updated_at?: string
}

export interface AssetInput {
  name: string
  asset_tag: string
  category_id: number
  purchase_date: string
  purchase_cost: number
  salvage_value: number
  status: string
  location?: string
  description?: string
}

export interface AssetCategory {
  id: number
  name: string
  description?: string
  depreciation_method: string
  useful_life_years: number
  created_at?: string
  updated_at?: string
}

export interface AssetCategoryInput {
  name: string
  description?: string
  depreciation_method: string
  useful_life_years: number
}

export interface MaintenanceSchedule {
  id: number
  asset_id: number
  title: string
  description?: string
  frequency: string
  next_due_date: string
  assigned_to?: string
  estimated_cost: number
  status: string
  created_at?: string
  updated_at?: string
}

export interface MaintenanceScheduleInput {
  asset_id: number
  title: string
  description?: string
  frequency: string
  next_due_date: string
  assigned_to?: string
  estimated_cost: number
  status: string
}

export interface DepreciationRecord {
  id: number
  asset_id: number
  period_start: string
  period_end: string
  depreciation_amount: number
  accumulated_depreciation: number
  book_value: number
  created_at?: string
}

export interface DepreciationRecordInput {
  asset_id: number
  period_start: string
  period_end: string
  depreciation_amount: number
  accumulated_depreciation: number
  book_value: number
}

// ── HR Types ──────────────────────────────────────────────────────────────────

export interface Employee {
  id: number
  first_name: string
  last_name: string
  email: string
  phone?: string
  department_id?: number
  position?: string
  hire_date?: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface EmployeeInput {
  first_name: string
  last_name: string
  email: string
  phone?: string
  department_id?: number
  position?: string
  hire_date?: string
  status: string
}

export interface Department {
  id: number
  name: string
  description?: string
  manager_id?: number
  created_at?: string
  updated_at?: string
}

export interface DepartmentInput {
  name: string
  description?: string
  manager_id?: number
}

// ── Project Management Types ──────────────────────────────────────────────────

export interface Project {
  id: number
  name: string
  description?: string
  status: string
  start_date?: string
  end_date?: string
  manager_id?: number
  created_at?: string
  updated_at?: string
}

export interface ProjectInput {
  name: string
  description?: string
  status: string
  start_date?: string
  end_date?: string
  manager_id?: number
}

export interface Milestone {
  id: number
  project_id: number
  name: string
  description?: string
  due_date?: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface MilestoneInput {
  project_id: number
  name: string
  description?: string
  due_date?: string
  status: string
}

// ── Data Warehouse Types ──────────────────────────────────────────────────────

export interface DataSource {
  id: number
  name: string
  description?: string
  source_type: string
  connection_string?: string
  status: string
  tags: string[]
  created_at?: string
  updated_at?: string
}

export interface DataSourceInput {
  name: string
  description?: string
  source_type?: string
  connection_string?: string
  status?: string
  tags?: string[]
}

export interface ETLJob {
  id: number
  name: string
  description?: string
  source_id?: number
  target_type: string
  schedule?: string
  status: string
  last_run?: string
  next_run?: string
  row_count: number
  duration_ms: number
  created_at?: string
  updated_at?: string
}

export interface ETLJobInput {
  name: string
  description?: string
  source_id?: number
  target_type?: string
  schedule?: string
  status?: string
  last_run?: string
  next_run?: string
  row_count?: number
  duration_ms?: number
}

export interface DataMart {
  id: number
  name: string
  description?: string
  schema_name?: string
  mart_type: string
  status: string
  table_count: number
  size_bytes: number
  tags: string[]
  created_at?: string
  updated_at?: string
}

export interface DataMartInput {
  name: string
  description?: string
  schema_name?: string
  mart_type?: string
  status?: string
  table_count?: number
  size_bytes?: number
  tags?: string[]
}

export interface DataModel {
  id: number
  name: string
  description?: string
  model_type: string
  mart_id?: number
  columns: string[]
  primary_key?: string
  indexes: string[]
  status: string
  row_count: number
  size_bytes: number
  created_at?: string
  updated_at?: string
}

export interface DataModelInput {
  name: string
  description?: string
  model_type?: string
  mart_id?: number
  columns?: string[]
  primary_key?: string
  indexes?: string[]
  status?: string
  row_count?: number
  size_bytes?: number
}

// ── Export Templates Types ──────────────────────────────────────────────────

export interface ExportTemplate {
  id: number
  name: string
  description?: string
  category: string
  format: string
  query?: string
  parameters?: Record<string, unknown>
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface ExportTemplateInput {
  name: string
  description?: string
  category?: string
  format?: string
  query?: string
  parameters?: Record<string, unknown>
  is_active?: boolean
}

export interface ExportJob {
  id: number
  template_id: number
  name: string
  status: string
  parameters?: Record<string, unknown>
  row_count?: number
  file_size?: string
  created_at?: string
  updated_at?: string
}

export interface ExportJobInput {
  template_id: number
  name: string
  status?: string
  parameters?: Record<string, unknown>
  row_count?: number
  file_size?: string
}

export interface ExportSchedule {
  id: number
  template_id: number
  name: string
  cron_expression: string
  recipients: string[]
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface ExportScheduleInput {
  template_id: number
  name: string
  cron_expression: string
  recipients?: string[]
  is_active?: boolean
}

// ── Integration Types ─────────────────────────────────────────────────────────

export interface Integration {
  id: number
  name: string
  type: string
  description?: string
  config?: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface IntegrationInput {
  name: string
  type: string
  description?: string
  config?: Record<string, unknown>
  is_active?: boolean
}

export interface ApiKey {
  id: number
  name: string
  integration_id: number
  scopes?: string[]
  key_prefix: string
  is_active: boolean
  created_at: string
  last_used_at?: string | null
  expires_at?: string | null
}

export interface ApiKeyInput {
  name: string
  integration_id: number
  scopes?: string[]
  expires_at?: string
}

export interface Webhook {
  id: number
  integration_id: number
  url: string
  events: string[]
  secret?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WebhookInput {
  integration_id: number
  url: string
  events: string[]
  secret?: string
  is_active?: boolean
}

export interface SyncJob {
  id: number
  integration_id: number
  job_type: string
  config?: Record<string, unknown>
  status: string
  started_at: string
  completed_at?: string | null
  result?: Record<string, unknown> | null
  error_message?: string | null
}

export interface SyncJobInput {
  integration_id: number
  job_type: string
  config?: Record<string, unknown>
}

// ── Knowledge Base Types ──────────────────────────────────────────────────────

export interface KBCategory {
  id: number
  name: string
  description?: string | null
}

export interface KBCategoryInput {
  name: string
  description?: string
}

export interface KBTag {
  id: number
  name: string
  color?: string
}

export interface KBTagInput {
  name: string
  color?: string
}

export interface KBArticle {
  id: number
  title: string
  content: string
  category_id?: number | null
  tag_ids: number[]
  author?: string | null
  is_published: boolean
  views: number
  created_at?: string
  updated_at?: string
}

export interface KBArticleInput {
  title: string
  content: string
  category_id?: number | null
  tag_ids: number[]
  author?: string
  is_published: boolean
}

export interface KBComment {
  id: number
  article_id: number
  author: string
  content: string
  created_at?: string
}

export interface KBCommentInput {
  article_id: number
  author: string
  content: string
}

// ── Notification Center Types ─────────────────────────────────────────────────

export interface Notification {
  id: number
  title: string
  message: string
  type: 'info' | 'warning' | 'error' | 'success'
  read: boolean
  user_id?: string
  created_at: string
  updated_at: string
}

export interface NotificationInput {
  title: string
  message: string
  type: 'info' | 'warning' | 'error' | 'success'
  read?: boolean
  user_id?: string
}

export interface NotificationTemplate {
  id: number
  name: string
  subject: string
  body: string
  type: 'info' | 'warning' | 'error' | 'success'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NotificationTemplateInput {
  name: string
  subject: string
  body: string
  type: 'info' | 'warning' | 'error' | 'success'
  is_active?: boolean
}

export interface NotificationRule {
  id: number
  name: string
  condition: string
  action: string
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NotificationRuleInput {
  name: string
  condition: string
  action: string
  priority?: number
  is_active?: boolean
}

export interface NotificationPreference {
  id: number
  user_id: string
  email_enabled: boolean
  push_enabled: boolean
  sms_enabled: boolean
  digest_frequency: 'immediate' | 'hourly' | 'daily' | 'weekly'
  quiet_hours_start?: string
  quiet_hours_end?: string
  created_at: string
  updated_at: string
}

export interface NotificationPreferenceInput {
  user_id: string
  email_enabled?: boolean
  push_enabled?: boolean
  sms_enabled?: boolean
  digest_frequency?: 'immediate' | 'hourly' | 'daily' | 'weekly'
  quiet_hours_start?: string
  quiet_hours_end?: string
}

// ── Disaster Recovery Types ───────────────────────────────────────────────────

export interface DRPlan {
  id: number
  name: string
  description: string
  rto_hours: number
  rpo_hours: number
  status: string
  last_tested: string | null
  created_at: string
}

export interface DRPlanInput {
  name: string
  description?: string
  rto_hours?: number
  rpo_hours?: number
  status?: string
  last_tested?: string | null
}

export interface BackupSchedule {
  id: number
  name: string
  schedule: string
  retention_days: number
  target: string
  enabled: boolean
  last_run: string | null
  created_at: string
}

export interface BackupScheduleInput {
  name: string
  schedule?: string
  retention_days?: number
  target?: string
  enabled?: boolean
  last_run?: string | null
}

export interface RecoveryProcedure {
  id: number
  dr_plan_id: number
  step: number
  title: string
  description: string
  owner: string
  estimated_minutes: number
  created_at: string
}

export interface RecoveryProcedureInput {
  dr_plan_id: number
  step: number
  title: string
  description?: string
  owner?: string
  estimated_minutes?: number
}

export interface DRTest {
  id: number
  dr_plan_id: number
  test_date: string
  result: string
  rto_achieved_hours: number | null
  notes: string
  created_at: string
}

export interface DRTestInput {
  dr_plan_id: number
  test_date: string
  result?: string
  rto_achieved_hours?: number | null
  notes?: string
}

// ── Capacity Planning Types ───────────────────────────────────────────────────

export interface CapacityPlan {
  id: number
  name: string
  status: string
  start_date?: string
  end_date?: string
  total_budget: number
  currency: string
  notes?: string
  created_at: string
}

export interface ResourceAllocation {
  id: number
  plan_id: number
  resource_type: string
  resource_name: string
  allocated_units: number
  utilized_units: number
  unit?: string
  cost_per_unit: number
  created_at: string
}

export interface Forecast {
  id: number
  plan_id: number
  metric: string
  period: string
  forecast_value: number
  confidence_lower?: number
  confidence_upper?: number
  model?: string
  created_at: string
}

export interface Scenario {
  id: number
  plan_id: number
  name: string
  description?: string
  assumptions?: string
  probability: number
  impact: string
  created_at: string
}


// ── Monitoring Types ──────────────────────────────────────────────────────────

export interface Monitor {
  id: number;
  name: string;
  type: string;
  target: string;
  interval: number;
  status: string;
  last_check: string;
  is_active: boolean;
}

export interface MonitorInput {
  name: string;
  type?: string;
  target?: string;
  interval?: number;
  is_active?: boolean;
}

export interface AlertRule {
  id: number;
  name: string;
  condition: string;
  severity: string;
  monitor_id?: number;
  is_active: boolean;
  created_at: string;
}

export interface AlertRuleInput {
  name: string;
  condition?: string;
  severity?: string;
  monitor_id?: number;
  is_active?: boolean;
}

export interface Dashboard {
  id: number;
  name: string;
  description: string;
  widgets: number;
  refresh_rate: number;
  is_active: boolean;
  created_at: string;
}

export interface DashboardInput {
  name: string;
  description?: string;
  widgets?: number;
  refresh_rate?: number;
  is_active?: boolean;
}

export interface Metric {
  id: number;
  name: string;
  unit: string;
  value: number;
  timestamp: string;
  monitor_id?: number;
}

export interface MetricInput {
  name: string;
  unit?: string;
  value?: number;
  monitor_id?: number;
}
