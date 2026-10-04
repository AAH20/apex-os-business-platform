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
    fetchData<Role[]>('/roles/'),

  /** Fetch a single role by ID. */
  getRoleById: (id: string): Promise<Role> =>
    fetchData<Role>(`/roles/${id}`),

  /** Create a new role. */
  createRole: (data: RoleInput): Promise<Role> =>
    request<Role>('/roles/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing role by ID. */
  updateRole: (id: string, data: RoleInput): Promise<Role> =>
    request<Role>(`/roles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a role by ID. */
  deleteRole: (id: string): Promise<void> =>
    request<void>(`/roles/${id}`, { method: 'DELETE' }),

  // ── Permissions CRUD ────────────────────────────────────────────────────────

  /** Fetch all permissions. */
  getPermissions: (): Promise<Permission[]> =>
    fetchData<Permission[]>('/permissions/'),

  /** Fetch a single permission by ID. */
  getPermissionById: (id: string): Promise<Permission> =>
    fetchData<Permission>(`/permissions/${id}`),

  /** Create a new permission. */
  createPermission: (data: PermissionInput): Promise<Permission> =>
    request<Permission>('/permissions/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing permission by ID. */
  updatePermission: (id: string, data: PermissionInput): Promise<Permission> =>
    request<Permission>(`/permissions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a permission by ID. */
  deletePermission: (id: string): Promise<void> =>
    request<void>(`/permissions/${id}`, { method: 'DELETE' }),

  // ── Opportunities CRUD ──────────────────────────────────────────────────────

  /** Fetch all opportunities. */
  getOpportunities: (): Promise<Opportunity[]> =>
    fetchData<Opportunity[]>('/opportunities/'),

  /** Fetch a single opportunity by ID. */
  getOpportunityById: (id: string): Promise<Opportunity> =>
    fetchData<Opportunity>(`/opportunities/${id}`),

  /** Create a new opportunity. */
  createOpportunity: (data: OpportunityInput): Promise<Opportunity> =>
    request<Opportunity>('/opportunities/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing opportunity by ID. */
  updateOpportunity: (id: string, data: OpportunityInput): Promise<Opportunity> =>
    request<Opportunity>(`/opportunities/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an opportunity by ID. */
  deleteOpportunity: (id: string): Promise<void> =>
    request<void>(`/opportunities/${id}`, { method: 'DELETE' }),

  // ── Campaigns CRUD ──────────────────────────────────────────────────────────

  /** Fetch all campaigns. */
  getCampaigns: (): Promise<Campaign[]> =>
    fetchData<Campaign[]>('/campaigns/'),

  /** Fetch a single campaign by ID. */
  getCampaignById: (id: string): Promise<Campaign> =>
    fetchData<Campaign>(`/campaigns/${id}`),

  /** Create a new campaign. */
  createCampaign: (data: CampaignInput): Promise<Campaign> =>
    request<Campaign>('/campaigns/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing campaign by ID. */
  updateCampaign: (id: string, data: CampaignInput): Promise<Campaign> =>
    request<Campaign>(`/campaigns/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a campaign by ID. */
  deleteCampaign: (id: string): Promise<void> =>
    request<void>(`/campaigns/${id}`, { method: 'DELETE' }),

  // ── Alerts CRUD ─────────────────────────────────────────────────────────────

  /** Fetch all alerts. */
  getAlerts: (): Promise<Alert[]> =>
    fetchData<Alert[]>('/alerts/'),

  /** Fetch a single alert by ID. */
  getAlertById: (id: string): Promise<Alert> =>
    fetchData<Alert>(`/alerts/${id}`),

  /** Create a new alert. */
  createAlert: (data: AlertInput): Promise<Alert> =>
    request<Alert>('/alerts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing alert by ID. */
  updateAlert: (id: string, data: AlertInput): Promise<Alert> =>
    request<Alert>(`/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an alert by ID. */
  deleteAlert: (id: string): Promise<void> =>
    request<void>(`/alerts/${id}`, { method: 'DELETE' }),

  // ── Compliance CRUD ────────────────────────────────────────────────────────

  /** Fetch all compliance frameworks. */
  getComplianceFrameworks: (): Promise<ComplianceFramework[]> =>
    fetchData<ComplianceFramework[]>('/compliance/frameworks/'),

  /** Fetch a single compliance framework by ID. */
  getComplianceFrameworkById: (id: string): Promise<ComplianceFramework> =>
    fetchData<ComplianceFramework>(`/compliance/frameworks/${id}`),

  /** Create a new compliance framework. */
  createComplianceFramework: (data: ComplianceFrameworkInput): Promise<ComplianceFramework> =>
    request<ComplianceFramework>('/compliance/frameworks/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance framework. */
  updateComplianceFramework: (id: string, data: ComplianceFrameworkInput): Promise<ComplianceFramework> =>
    request<ComplianceFramework>(`/compliance/frameworks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance framework. */
  deleteComplianceFramework: (id: string): Promise<void> =>
    request<void>(`/compliance/frameworks/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance controls. */
  getComplianceControls: (): Promise<Control[]> =>
    fetchData<Control[]>('/compliance/controls/'),

  /** Fetch a single compliance control by ID. */
  getComplianceControlById: (id: string): Promise<Control> =>
    fetchData<Control>(`/compliance/controls/${id}`),

  /** Create a new compliance control. */
  createComplianceControl: (data: ControlInput): Promise<Control> =>
    request<Control>('/compliance/controls/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance control. */
  updateComplianceControl: (id: string, data: ControlInput): Promise<Control> =>
    request<Control>(`/compliance/controls/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance control. */
  deleteComplianceControl: (id: string): Promise<void> =>
    request<void>(`/compliance/controls/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance audits. */
  getComplianceAudits: (): Promise<Audit[]> =>
    fetchData<Audit[]>('/compliance/audits/'),

  /** Fetch a single compliance audit by ID. */
  getComplianceAuditById: (id: string): Promise<Audit> =>
    fetchData<Audit>(`/compliance/audits/${id}`),

  /** Create a new compliance audit. */
  createComplianceAudit: (data: AuditInput): Promise<Audit> =>
    request<Audit>('/compliance/audits/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance audit. */
  updateComplianceAudit: (id: string, data: AuditInput): Promise<Audit> =>
    request<Audit>(`/compliance/audits/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance audit. */
  deleteComplianceAudit: (id: string): Promise<void> =>
    request<void>(`/compliance/audits/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance findings. */
  getComplianceFindings: (): Promise<Finding[]> =>
    fetchData<Finding[]>('/compliance/findings/'),

  /** Fetch a single compliance finding by ID. */
  getComplianceFindingById: (id: string): Promise<Finding> =>
    fetchData<Finding>(`/compliance/findings/${id}`),

  /** Create a new compliance finding. */
  createComplianceFinding: (data: FindingInput): Promise<Finding> =>
    request<Finding>('/compliance/findings/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance finding. */
  updateComplianceFinding: (id: string, data: FindingInput): Promise<Finding> =>
    request<Finding>(`/compliance/findings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance finding. */
  deleteComplianceFinding: (id: string): Promise<void> =>
    request<void>(`/compliance/findings/${id}`, { method: 'DELETE' }),

  /** Fetch all compliance remediation plans. */
  getComplianceRemediationPlans: (): Promise<RemediationPlan[]> =>
    fetchData<RemediationPlan[]>('/compliance/remediation-plans/'),

  /** Fetch a single compliance remediation plan by ID. */
  getComplianceRemediationPlanById: (id: string): Promise<RemediationPlan> =>
    fetchData<RemediationPlan>(`/compliance/remediation-plans/${id}`),

  /** Create a new compliance remediation plan. */
  createComplianceRemediationPlan: (data: RemediationPlanInput): Promise<RemediationPlan> =>
    request<RemediationPlan>('/compliance/remediation-plans/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing compliance remediation plan. */
  updateComplianceRemediationPlan: (id: string, data: RemediationPlanInput): Promise<RemediationPlan> =>
    request<RemediationPlan>(`/compliance/remediation-plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a compliance remediation plan. */
  deleteComplianceRemediationPlan: (id: string): Promise<void> =>
    request<void>(`/compliance/remediation-plans/${id}`, { method: 'DELETE' }),

  // ── Budgeting CRUD ──────────────────────────────────────────────────────────

  /** Fetch all budgets. */
  getBudgets: (): Promise<Budget[]> =>
    fetchData<Budget[]>('/budgeting/budgets/'),

  /** Fetch a single budget by ID. */
  getBudgetById: (id: number): Promise<Budget> =>
    fetchData<Budget>(`/budgeting/budgets/${id}`),

  /** Create a new budget. */
  createBudget: (data: Partial<Budget>): Promise<Budget> =>
    request<Budget>('/budgeting/budgets/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing budget. */
  updateBudget: (id: number, data: Partial<Budget>): Promise<Budget> =>
    request<Budget>(`/budgeting/budgets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a budget. */
  deleteBudget: (id: number): Promise<void> =>
    request<void>(`/budgeting/budgets/${id}`, { method: 'DELETE' }),

  /** Fetch all budget lines. */
  getBudgetLines: (): Promise<BudgetLine[]> =>
    fetchData<BudgetLine[]>('/budgeting/budget-lines/'),

  /** Fetch a single budget line by ID. */
  getBudgetLineById: (id: number): Promise<BudgetLine> =>
    fetchData<BudgetLine>(`/budgeting/budget-lines/${id}`),

  /** Create a new budget line. */
  createBudgetLine: (data: Partial<BudgetLine>): Promise<BudgetLine> =>
    request<BudgetLine>('/budgeting/budget-lines/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing budget line. */
  updateBudgetLine: (id: number, data: Partial<BudgetLine>): Promise<BudgetLine> =>
    request<BudgetLine>(`/budgeting/budget-lines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a budget line. */
  deleteBudgetLine: (id: number): Promise<void> =>
    request<void>(`/budgeting/budget-lines/${id}`, { method: 'DELETE' }),

  /** Fetch all cost centers. */
  getCostCenters: (): Promise<CostCenter[]> =>
    fetchData<CostCenter[]>('/budgeting/cost-centers/'),

  /** Fetch a single cost center by ID. */
  getCostCenterById: (id: number): Promise<CostCenter> =>
    fetchData<CostCenter>(`/budgeting/cost-centers/${id}`),

  /** Create a new cost center. */
  createCostCenter: (data: Partial<CostCenter>): Promise<CostCenter> =>
    request<CostCenter>('/budgeting/cost-centers/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing cost center. */
  updateCostCenter: (id: number, data: Partial<CostCenter>): Promise<CostCenter> =>
    request<CostCenter>(`/budgeting/cost-centers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a cost center. */
  deleteCostCenter: (id: number): Promise<void> =>
    request<void>(`/budgeting/cost-centers/${id}`, { method: 'DELETE' }),

  /** Fetch all variance analysis records. */
  getVarianceAnalysis: (): Promise<VarianceAnalysis[]> =>
    fetchData<VarianceAnalysis[]>('/budgeting/variance-analysis/'),

  /** Fetch a single variance analysis by ID. */
  getVarianceAnalysisById: (id: number): Promise<VarianceAnalysis> =>
    fetchData<VarianceAnalysis>(`/budgeting/variance-analysis/${id}`),

  /** Create a new variance analysis record. */
  createVarianceAnalysis: (data: Partial<VarianceAnalysis>): Promise<VarianceAnalysis> =>
    request<VarianceAnalysis>('/budgeting/variance-analysis/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing variance analysis record. */
  updateVarianceAnalysis: (id: number, data: Partial<VarianceAnalysis>): Promise<VarianceAnalysis> =>
    request<VarianceAnalysis>(`/budgeting/variance-analysis/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a variance analysis record. */
  deleteVarianceAnalysis: (id: number): Promise<void> =>
    request<void>(`/budgeting/variance-analysis/${id}`, { method: 'DELETE' }),

  // ── Inventory: Products CRUD ──────────────────────────────────────────────

  /** Fetch paginated products with optional category/supplier filter. */
  getProducts: (params?: { skip?: number; limit?: number; category_id?: number; supplier_id?: number }): Promise<Product[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.category_id != null) sp.set('category_id', String(params.category_id))
    if (params?.supplier_id != null) sp.set('supplier_id', String(params.supplier_id))
    const qs = sp.toString()
    return request<Product[]>(`/inventory/products${qs ? `?${qs}` : ''}`)
  },

  /** Fetch a single product by ID. */
  getProduct: (id: number): Promise<Product> =>
    request<Product>(`/inventory/products/${id}`),

  /** Create a new product. */
  createProduct: (data: ProductInput): Promise<Product> =>
    request<Product>('/inventory/products', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing product. */
  updateProduct: (id: number, data: Partial<ProductInput>): Promise<Product> =>
    request<Product>(`/inventory/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a product. */
  deleteProduct: (id: number): Promise<void> =>
    request<void>(`/inventory/products/${id}`, { method: 'DELETE' }),

  // ── Inventory: Categories CRUD ────────────────────────────────────────────

  /** Fetch all categories. */
  getCategories: (): Promise<Category[]> =>
    request<Category[]>('/inventory/categories'),

  /** Fetch a single category by ID. */
  getCategory: (id: number): Promise<Category> =>
    request<Category>(`/inventory/categories/${id}`),

  /** Create a new category. */
  createCategory: (data: CategoryInput): Promise<Category> =>
    request<Category>('/inventory/categories', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing category. */
  updateCategory: (id: number, data: Partial<CategoryInput>): Promise<Category> =>
    request<Category>(`/inventory/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a category. */
  deleteCategory: (id: number): Promise<void> =>
    request<void>(`/inventory/categories/${id}`, { method: 'DELETE' }),

  // ── Inventory: Suppliers CRUD ─────────────────────────────────────────────

  /** Fetch all suppliers. */
  getSuppliers: (): Promise<Supplier[]> =>
    request<Supplier[]>('/inventory/suppliers'),

  /** Fetch a single supplier by ID. */
  getSupplier: (id: number): Promise<Supplier> =>
    request<Supplier>(`/inventory/suppliers/${id}`),

  /** Create a new supplier. */
  createSupplier: (data: SupplierInput): Promise<Supplier> =>
    request<Supplier>('/inventory/suppliers', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing supplier. */
  updateSupplier: (id: number, data: Partial<SupplierInput>): Promise<Supplier> =>
    request<Supplier>(`/inventory/suppliers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a supplier. */
  deleteSupplier: (id: number): Promise<void> =>
    request<void>(`/inventory/suppliers/${id}`, { method: 'DELETE' }),

  // ── Inventory: Stock Orders CRUD ──────────────────────────────────────────

  /** Fetch paginated stock orders with optional status/product filter. */
  getStockOrders: (params?: { skip?: number; limit?: number; status?: string; product_id?: number }): Promise<StockOrder[]> => {
    const sp = new URLSearchParams()
    if (params?.skip != null) sp.set('skip', String(params.skip))
    if (params?.limit != null) sp.set('limit', String(params.limit))
    if (params?.status) sp.set('status', params.status)
    if (params?.product_id != null) sp.set('product_id', String(params.product_id))
    const qs = sp.toString()
    return request<StockOrder[]>(`/inventory/stock-orders${qs ? `?${qs}` : ''}`)
  },

  /** Fetch a single stock order by ID. */
  getStockOrder: (id: number): Promise<StockOrder> =>
    request<StockOrder>(`/inventory/stock-orders/${id}`),

  /** Create a new stock order. */
  createStockOrder: (data: StockOrderInput): Promise<StockOrder> =>
    request<StockOrder>('/inventory/stock-orders', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing stock order. */
  updateStockOrder: (id: number, data: Partial<StockOrderInput>): Promise<StockOrder> =>
    request<StockOrder>(`/inventory/stock-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a stock order. */
  deleteStockOrder: (id: number): Promise<void> =>
    request<void>(`/inventory/stock-orders/${id}`, { method: 'DELETE' }),

  // ── Inventory: Warehouse Locations CRUD ───────────────────────────────────

  /** Fetch all warehouse locations. */
  getWarehouseLocations: (): Promise<WarehouseLocation[]> =>
    request<WarehouseLocation[]>('/inventory/warehouse-locations'),

  /** Fetch a single warehouse location by ID. */
  getWarehouseLocation: (id: number): Promise<WarehouseLocation> =>
    request<WarehouseLocation>(`/inventory/warehouse-locations/${id}`),

  /** Create a new warehouse location. */
  createWarehouseLocation: (data: WarehouseLocationInput): Promise<WarehouseLocation> =>
    request<WarehouseLocation>('/inventory/warehouse-locations', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing warehouse location. */
  updateWarehouseLocation: (id: number, data: Partial<WarehouseLocationInput>): Promise<WarehouseLocation> =>
    request<WarehouseLocation>(`/inventory/warehouse-locations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a warehouse location. */
  deleteWarehouseLocation: (id: number): Promise<void> =>
    request<void>(`/inventory/warehouse-locations/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Suppliers CRUD ──────────────────────────────────────────

  /** Fetch all supply chain suppliers. */
  getSupplyChainSuppliers: (): Promise<Supplier[]> =>
    request<Supplier[]>('/supply-chain/suppliers'),

  /** Fetch a single supply chain supplier by ID. */
  getSupplyChainSupplier: (id: number): Promise<Supplier> =>
    request<Supplier>(`/supply-chain/suppliers/${id}`),

  /** Create a new supply chain supplier. */
  createSupplyChainSupplier: (data: SupplierInput): Promise<Supplier> =>
    request<Supplier>('/supply-chain/suppliers', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing supply chain supplier. */
  updateSupplyChainSupplier: (id: number, data: Partial<SupplierInput>): Promise<Supplier> =>
    request<Supplier>(`/supply-chain/suppliers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a supply chain supplier. */
  deleteSupplyChainSupplier: (id: number): Promise<void> =>
    request<void>(`/supply-chain/suppliers/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Purchase Orders CRUD ────────────────────────────────────

  /** Fetch all purchase orders. */
  getPurchaseOrders: (): Promise<PurchaseOrder[]> =>
    request<PurchaseOrder[]>('/supply-chain/purchase-orders'),

  /** Fetch a single purchase order by ID. */
  getPurchaseOrder: (id: number): Promise<PurchaseOrder> =>
    request<PurchaseOrder>(`/supply-chain/purchase-orders/${id}`),

  /** Create a new purchase order. */
  createPurchaseOrder: (data: PurchaseOrderInput): Promise<PurchaseOrder> =>
    request<PurchaseOrder>('/supply-chain/purchase-orders', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing purchase order. */
  updatePurchaseOrder: (id: number, data: Partial<PurchaseOrderInput>): Promise<PurchaseOrder> =>
    request<PurchaseOrder>(`/supply-chain/purchase-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a purchase order. */
  deletePurchaseOrder: (id: number): Promise<void> =>
    request<void>(`/supply-chain/purchase-orders/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Shipments CRUD ───────────────────────────────────────────

  /** Fetch all shipments. */
  getShipments: (): Promise<Shipment[]> =>
    request<Shipment[]>('/supply-chain/shipments'),

  /** Fetch a single shipment by ID. */
  getShipment: (id: number): Promise<Shipment> =>
    request<Shipment>(`/supply-chain/shipments/${id}`),

  /** Create a new shipment. */
  createShipment: (data: ShipmentInput): Promise<Shipment> =>
    request<Shipment>('/supply-chain/shipments', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing shipment. */
  updateShipment: (id: number, data: Partial<ShipmentInput>): Promise<Shipment> =>
    request<Shipment>(`/supply-chain/shipments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a shipment. */
  deleteShipment: (id: number): Promise<void> =>
    request<void>(`/supply-chain/shipments/${id}`, { method: 'DELETE' }),

  // ── Supply Chain: Logistics Routes CRUD ───────────────────────────────────

  /** Fetch all logistics routes. */
  getLogisticsRoutes: (): Promise<LogisticsRoute[]> =>
    request<LogisticsRoute[]>('/supply-chain/logistics-routes'),

  /** Fetch a single logistics route by ID. */
  getLogisticsRoute: (id: number): Promise<LogisticsRoute> =>
    request<LogisticsRoute>(`/supply-chain/logistics-routes/${id}`),

  /** Create a new logistics route. */
  createLogisticsRoute: (data: LogisticsRouteInput): Promise<LogisticsRoute> =>
    request<LogisticsRoute>('/supply-chain/logistics-routes', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing logistics route. */
  updateLogisticsRoute: (id: number, data: Partial<LogisticsRouteInput>): Promise<LogisticsRoute> =>
    request<LogisticsRoute>(`/supply-chain/logistics-routes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a logistics route. */
  deleteLogisticsRoute: (id: number): Promise<void> =>
    request<void>(`/supply-chain/logistics-routes/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Production Lines CRUD ─────────────────────────────────

  /** Fetch all production lines. */
  getProductionLines: (): Promise<ProductionLine[]> =>
    request<ProductionLine[]>('/manufacturing/production-lines/'),

  /** Fetch a single production line by ID. */
  getProductionLine: (id: number): Promise<ProductionLine> =>
    request<ProductionLine>(`/manufacturing/production-lines/${id}`),

  /** Create a new production line. */
  createProductionLine: (data: ProductionLineInput): Promise<ProductionLine> =>
    request<ProductionLine>('/manufacturing/production-lines/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing production line. */
  updateProductionLine: (id: number, data: Partial<ProductionLineInput>): Promise<ProductionLine> =>
    request<ProductionLine>(`/manufacturing/production-lines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a production line. */
  deleteProductionLine: (id: number): Promise<void> =>
    request<void>(`/manufacturing/production-lines/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Work Orders CRUD ───────────────────────────────────────

  /** Fetch all work orders. */
  getWorkOrders: (): Promise<WorkOrder[]> =>
    request<WorkOrder[]>('/manufacturing/work-orders/'),

  /** Fetch a single work order by ID. */
  getWorkOrder: (id: number): Promise<WorkOrder> =>
    request<WorkOrder>(`/manufacturing/work-orders/${id}`),

  /** Create a new work order. */
  createWorkOrder: (data: WorkOrderInput): Promise<WorkOrder> =>
    request<WorkOrder>('/manufacturing/work-orders/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing work order. */
  updateWorkOrder: (id: number, data: Partial<WorkOrderInput>): Promise<WorkOrder> =>
    request<WorkOrder>(`/manufacturing/work-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a work order. */
  deleteWorkOrder: (id: number): Promise<void> =>
    request<void>(`/manufacturing/work-orders/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Quality Checks CRUD ────────────────────────────────────

  /** Fetch all quality checks. */
  getQualityChecks: (): Promise<QualityCheck[]> =>
    request<QualityCheck[]>('/manufacturing/quality-checks/'),

  /** Fetch a single quality check by ID. */
  getQualityCheck: (id: number): Promise<QualityCheck> =>
    request<QualityCheck>(`/manufacturing/quality-checks/${id}`),

  /** Create a new quality check. */
  createQualityCheck: (data: QualityCheckInput): Promise<QualityCheck> =>
    request<QualityCheck>('/manufacturing/quality-checks/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing quality check. */
  updateQualityCheck: (id: number, data: Partial<QualityCheckInput>): Promise<QualityCheck> =>
    request<QualityCheck>(`/manufacturing/quality-checks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a quality check. */
  deleteQualityCheck: (id: number): Promise<void> =>
    request<void>(`/manufacturing/quality-checks/${id}`, { method: 'DELETE' }),

  // ── Manufacturing: Bills of Materials CRUD ────────────────────────────────

  /** Fetch all bills of materials. */
  getBillsOfMaterials: (): Promise<BillOfMaterials[]> =>
    request<BillOfMaterials[]>('/manufacturing/bills-of-materials/'),

  /** Fetch a single bill of materials by ID. */
  getBillOfMaterials: (id: number): Promise<BillOfMaterials> =>
    request<BillOfMaterials>(`/manufacturing/bills-of-materials/${id}`),

  /** Create a new bill of materials. */
  createBillOfMaterials: (data: BillOfMaterialsInput): Promise<BillOfMaterials> =>
    request<BillOfMaterials>('/manufacturing/bills-of-materials/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing bill of materials. */
  updateBillOfMaterials: (id: number, data: Partial<BillOfMaterialsInput>): Promise<BillOfMaterials> =>
    request<BillOfMaterials>(`/manufacturing/bills-of-materials/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a bill of materials. */
  deleteBillOfMaterials: (id: number): Promise<void> =>
    request<void>(`/manufacturing/bills-of-materials/${id}`, { method: 'DELETE' }),

  // ── Reporting CRUD ─────────────────────────────────────────────────────────

  /** Fetch paginated reports. */
  getReports: (params?: { page?: number; limit?: number; search?: string }): Promise<Report[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.search) sp.set('search', params.search);
    const qs = sp.toString();
    return request<Report[]>(`/reporting/reports${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single report by ID. */
  getReportById: (id: number): Promise<Report> =>
    request<Report>(`/reporting/reports/${id}`),

  /** Create a new report. */
  createReport: (data: ReportInput): Promise<Report> =>
    request<Report>('/reporting/reports', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing report by ID. */
  updateReport: (id: number, data: ReportInput): Promise<Report> =>
    request<Report>(`/reporting/reports/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a report by ID. */
  deleteReport: (id: number): Promise<void> =>
    request<void>(`/reporting/reports/${id}`, { method: 'DELETE' }),

  /** Fetch paginated report templates. */
  getReportTemplates: (params?: { page?: number; limit?: number }): Promise<ReportTemplate[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<ReportTemplate[]>(`/reporting/templates${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single report template by ID. */
  getReportTemplateById: (id: number): Promise<ReportTemplate> =>
    request<ReportTemplate>(`/reporting/templates/${id}`),

  /** Create a new report template. */
  createReportTemplate: (data: ReportTemplateInput): Promise<ReportTemplate> =>
    request<ReportTemplate>('/reporting/templates', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing report template by ID. */
  updateReportTemplate: (id: number, data: ReportTemplateInput): Promise<ReportTemplate> =>
    request<ReportTemplate>(`/reporting/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a report template by ID. */
  deleteReportTemplate: (id: number): Promise<void> =>
    request<void>(`/reporting/templates/${id}`, { method: 'DELETE' }),

  /** Fetch paginated scheduled reports. */
  getScheduledReports: (params?: { page?: number; limit?: number }): Promise<ScheduledReport[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<ScheduledReport[]>(`/reporting/scheduled${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single scheduled report by ID. */
  getScheduledReportById: (id: number): Promise<ScheduledReport> =>
    request<ScheduledReport>(`/reporting/scheduled/${id}`),

  /** Create a new scheduled report. */
  createScheduledReport: (data: ScheduledReportInput): Promise<ScheduledReport> =>
    request<ScheduledReport>('/reporting/scheduled', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing scheduled report by ID. */
  updateScheduledReport: (id: number, data: ScheduledReportInput): Promise<ScheduledReport> =>
    request<ScheduledReport>(`/reporting/scheduled/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a scheduled report by ID. */
  deleteScheduledReport: (id: number): Promise<void> =>
    request<void>(`/reporting/scheduled/${id}`, { method: 'DELETE' }),

  /** Fetch paginated report subscriptions. */
  getReportSubscriptions: (params?: { page?: number; limit?: number }): Promise<ReportSubscription[]> => {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<ReportSubscription[]>(`/reporting/subscriptions${qs ? `?${qs}` : ''}`);
  },

  /** Fetch a single report subscription by ID. */
  getReportSubscriptionById: (id: number): Promise<ReportSubscription> =>
    request<ReportSubscription>(`/reporting/subscriptions/${id}`),

  /** Create a new report subscription. */
  createReportSubscription: (data: ReportSubscriptionInput): Promise<ReportSubscription> =>
    request<ReportSubscription>('/reporting/subscriptions', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing report subscription by ID. */
  updateReportSubscription: (id: number, data: ReportSubscriptionInput): Promise<ReportSubscription> =>
    request<ReportSubscription>(`/reporting/subscriptions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a report subscription by ID. */
  deleteReportSubscription: (id: number): Promise<void> =>
    request<void>(`/reporting/subscriptions/${id}`, { method: 'DELETE' }),

  // ── Asset Management CRUD ───────────────────────────────────────────────────

  /** Fetch all assets. */
  getAssets: (): Promise<Asset[]> =>
    fetchData<Asset[]>('/assets/'),

  /** Fetch a single asset by ID. */
  getAssetById: (id: number): Promise<Asset> =>
    fetchData<Asset>(`/assets/${id}`),

  /** Create a new asset. */
  createAsset: (data: AssetInput): Promise<Asset> =>
    request<Asset>('/assets/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing asset by ID. */
  updateAsset: (id: number, data: AssetInput): Promise<Asset> =>
    request<Asset>(`/assets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an asset by ID. */
  deleteAsset: (id: number): Promise<void> =>
    request<void>(`/assets/${id}`, { method: 'DELETE' }),

  /** Fetch all asset categories. */
  getAssetCategories: (): Promise<AssetCategory[]> =>
    fetchData<AssetCategory[]>('/assets/categories/'),

  /** Fetch a single asset category by ID. */
  getAssetCategoryById: (id: number): Promise<AssetCategory> =>
    fetchData<AssetCategory>(`/assets/categories/${id}`),

  /** Create a new asset category. */
  createAssetCategory: (data: AssetCategoryInput): Promise<AssetCategory> =>
    request<AssetCategory>('/assets/categories/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing asset category by ID. */
  updateAssetCategory: (id: number, data: AssetCategoryInput): Promise<AssetCategory> =>
    request<AssetCategory>(`/assets/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an asset category by ID. */
  deleteAssetCategory: (id: number): Promise<void> =>
    request<void>(`/assets/categories/${id}`, { method: 'DELETE' }),

  /** Fetch all maintenance schedules. */
  getMaintenanceSchedules: (): Promise<MaintenanceSchedule[]> =>
    fetchData<MaintenanceSchedule[]>('/assets/maintenance/'),

  /** Fetch a single maintenance schedule by ID. */
  getMaintenanceScheduleById: (id: number): Promise<MaintenanceSchedule> =>
    fetchData<MaintenanceSchedule>(`/assets/maintenance/${id}`),

  /** Create a new maintenance schedule. */
  createMaintenanceSchedule: (data: MaintenanceScheduleInput): Promise<MaintenanceSchedule> =>
    request<MaintenanceSchedule>('/assets/maintenance/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing maintenance schedule by ID. */
  updateMaintenanceSchedule: (id: number, data: MaintenanceScheduleInput): Promise<MaintenanceSchedule> =>
    request<MaintenanceSchedule>(`/assets/maintenance/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a maintenance schedule by ID. */
  deleteMaintenanceSchedule: (id: number): Promise<void> =>
    request<void>(`/assets/maintenance/${id}`, { method: 'DELETE' }),

  /** Fetch all depreciation records. */
  getDepreciationRecords: (): Promise<DepreciationRecord[]> =>
    fetchData<DepreciationRecord[]>('/assets/depreciation/'),

  /** Fetch a single depreciation record by ID. */
  getDepreciationRecordById: (id: number): Promise<DepreciationRecord> =>
    fetchData<DepreciationRecord>(`/assets/depreciation/${id}`),

  /** Create a new depreciation record. */
  createDepreciationRecord: (data: DepreciationRecordInput): Promise<DepreciationRecord> =>
    request<DepreciationRecord>('/assets/depreciation/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing depreciation record by ID. */
  updateDepreciationRecord: (id: number, data: DepreciationRecordInput): Promise<DepreciationRecord> =>
    request<DepreciationRecord>(`/assets/depreciation/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a depreciation record by ID. */
  deleteDepreciationRecord: (id: number): Promise<void> =>
    request<void>(`/assets/depreciation/${id}`, { method: 'DELETE' }),

  // ── IoT CRUD ───────────────────────────────────────────────────────────────

  /** Fetch all IoT devices. */
  getIoTDevices: (): Promise<IoTDevice[]> =>
    fetchData<IoTDevice[]>('/iot/devices/'),

  /** Fetch a single IoT device by ID. */
  getIoTDeviceById: (id: number): Promise<IoTDevice> =>
    fetchData<IoTDevice>(`/iot/devices/${id}`),

  /** Create a new IoT device. */
  createIoTDevice: (data: IoTDeviceInput): Promise<IoTDevice> =>
    request<IoTDevice>('/iot/devices/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT device. */
  updateIoTDevice: (id: number, data: IoTDeviceInput): Promise<IoTDevice> =>
    request<IoTDevice>(`/iot/devices/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT device. */
  deleteIoTDevice: (id: number): Promise<void> =>
    request<void>(`/iot/devices/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT sensors. */
  getIoTSensors: (): Promise<IoTSensor[]> =>
    fetchData<IoTSensor[]>('/iot/sensors/'),

  /** Fetch a single IoT sensor by ID. */
  getIoTSensorById: (id: number): Promise<IoTSensor> =>
    fetchData<IoTSensor>(`/iot/sensors/${id}`),

  /** Create a new IoT sensor. */
  createIoTSensor: (data: IoTSensorInput): Promise<IoTSensor> =>
    request<IoTSensor>('/iot/sensors/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT sensor. */
  updateIoTSensor: (id: number, data: IoTSensorInput): Promise<IoTSensor> =>
    request<IoTSensor>(`/iot/sensors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT sensor. */
  deleteIoTSensor: (id: number): Promise<void> =>
    request<void>(`/iot/sensors/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT telemetry data. */
  getIoTTelemetry: (): Promise<IoTTelemetry[]> =>
    fetchData<IoTTelemetry[]>('/iot/telemetry/'),

  /** Fetch a single IoT telemetry entry by ID. */
  getIoTTelemetryById: (id: number): Promise<IoTTelemetry> =>
    fetchData<IoTTelemetry>(`/iot/telemetry/${id}`),

  /** Create a new IoT telemetry entry. */
  createIoTTelemetry: (data: IoTTelemetryInput): Promise<IoTTelemetry> =>
    request<IoTTelemetry>('/iot/telemetry/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT telemetry entry. */
  updateIoTTelemetry: (id: number, data: IoTTelemetryInput): Promise<IoTTelemetry> =>
    request<IoTTelemetry>(`/iot/telemetry/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT telemetry entry. */
  deleteIoTTelemetry: (id: number): Promise<void> =>
    request<void>(`/iot/telemetry/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT alerts. */
  getIoTAlerts: (): Promise<IoTAlert[]> =>
    fetchData<IoTAlert[]>('/iot/alerts/'),

  /** Fetch a single IoT alert by ID. */
  getIoTAlertById: (id: number): Promise<IoTAlert> =>
    fetchData<IoTAlert>(`/iot/alerts/${id}`),

  /** Create a new IoT alert. */
  createIoTAlert: (data: IoTAlertInput): Promise<IoTAlert> =>
    request<IoTAlert>('/iot/alerts/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT alert. */
  updateIoTAlert: (id: number, data: IoTAlertInput): Promise<IoTAlert> =>
    request<IoTAlert>(`/iot/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT alert. */
  deleteIoTAlert: (id: number): Promise<void> =>
    request<void>(`/iot/alerts/${id}`, { method: 'DELETE' }),

  /** Fetch all IoT device groups. */
  getIoTGroups: (): Promise<IoTDeviceGroup[]> =>
    fetchData<IoTDeviceGroup[]>('/iot/groups/'),

  /** Fetch a single IoT device group by ID. */
  getIoTGroupById: (id: number): Promise<IoTDeviceGroup> =>
    fetchData<IoTDeviceGroup>(`/iot/groups/${id}`),

  /** Create a new IoT device group. */
  createIoTGroup: (data: IoTGroupInput): Promise<IoTDeviceGroup> =>
    request<IoTDeviceGroup>('/iot/groups/', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing IoT device group. */
  updateIoTGroup: (id: number, data: IoTGroupInput): Promise<IoTDeviceGroup> =>
    request<IoTDeviceGroup>(`/iot/groups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an IoT device group. */
  deleteIoTGroup: (id: number): Promise<void> =>
    request<void>(`/iot/groups/${id}`, { method: 'DELETE' }),

  // ── HR: Employees CRUD ─────────────────────────────────────────────────────

  /** Fetch all employees. */
  getEmployees: (): Promise<Employee[]> =>
    request<Employee[]>('/hr/employees'),

  /** Fetch a single employee by ID. */
  getEmployee: (id: number): Promise<Employee> =>
    request<Employee>(`/hr/employees/${id}`),

  /** Create a new employee. */
  createEmployee: (data: EmployeeInput): Promise<Employee> =>
    request<Employee>('/hr/employees', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing employee. */
  updateEmployee: (id: number, data: Partial<EmployeeInput>): Promise<Employee> =>
    request<Employee>(`/hr/employees/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete an employee. */
  deleteEmployee: (id: number): Promise<void> =>
    request<void>(`/hr/employees/${id}`, { method: 'DELETE' }),

  // ── HR: Departments CRUD ───────────────────────────────────────────────────

  /** Fetch all departments. */
  getDepartments: (): Promise<Department[]> =>
    request<Department[]>('/hr/departments'),

  /** Fetch a single department by ID. */
  getDepartment: (id: number): Promise<Department> =>
    request<Department>(`/hr/departments/${id}`),

  /** Create a new department. */
  createDepartment: (data: DepartmentInput): Promise<Department> =>
    request<Department>('/hr/departments', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing department. */
  updateDepartment: (id: number, data: Partial<DepartmentInput>): Promise<Department> =>
    request<Department>(`/hr/departments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a department. */
  deleteDepartment: (id: number): Promise<void> =>
    request<void>(`/hr/departments/${id}`, { method: 'DELETE' }),

  // ── IoT: Devices & Sensors (short aliases) ─────────────────────────────────

  /** Fetch all devices (alias for getIoTDevices). */
  getDevices: (): Promise<IoTDevice[]> =>
    request<IoTDevice[]>('/iot/devices/'),

  /** Fetch all sensors (alias for getIoTSensors). */
  getSensors: (): Promise<IoTSensor[]> =>
    request<IoTSensor[]>('/iot/sensors/'),

  // ── Compliance: Controls (short alias) ─────────────────────────────────────

  /** Fetch all controls (alias for getComplianceControls). */
  getControls: (): Promise<Control[]> =>
    request<Control[]>('/compliance/controls/'),

  // ── Project Management CRUD ────────────────────────────────────────────────

  /** Fetch all projects. */
  getProjects: (): Promise<Project[]> =>
    request<Project[]>('/projects'),

  /** Fetch a single project by ID. */
  getProject: (id: number): Promise<Project> =>
    request<Project>(`/projects/${id}`),

  /** Create a new project. */
  createProject: (data: ProjectInput): Promise<Project> =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing project. */
  updateProject: (id: number, data: Partial<ProjectInput>): Promise<Project> =>
    request<Project>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a project. */
  deleteProject: (id: number): Promise<void> =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  /** Fetch all milestones. */
  getMilestones: (): Promise<Milestone[]> =>
    request<Milestone[]>('/projects/milestones'),

  /** Fetch a single milestone by ID. */
  getMilestone: (id: number): Promise<Milestone> =>
    request<Milestone>(`/projects/milestones/${id}`),

  /** Create a new milestone. */
  createMilestone: (data: MilestoneInput): Promise<Milestone> =>
    request<Milestone>('/projects/milestones', { method: 'POST', body: JSON.stringify(data) }),

  /** Update an existing milestone. */
  updateMilestone: (id: number, data: Partial<MilestoneInput>): Promise<Milestone> =>
    request<Milestone>(`/projects/milestones/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** Delete a milestone. */
  deleteMilestone: (id: number): Promise<void> =>
    request<void>(`/projects/milestones/${id}`, { method: 'DELETE' }),
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
