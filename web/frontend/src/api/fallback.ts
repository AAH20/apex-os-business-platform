// Shared fetch utility with timeout, API key, and fallback support.

const API_KEY = 'test-api-key-12345';
const DEFAULT_TIMEOUT = 8000; // 8 seconds

export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout = DEFAULT_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        ...options.headers,
      },
    });
    return res;
  } finally {
    clearTimeout(timer);
  }
}

export function getErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) {
    if (err.name === 'AbortError') return 'Request timed out — server may be unreachable';
    return err.message;
  }
  return fallback;
}

// ── Synthetic fallback data ─────────────────────────────────────────────────

export const FALLBACK_OPPORTUNITIES = [
  { id: '1', name: 'Enterprise Deal — Acme Corp', stage: 'negotiation', value: 150000, probability: 75, expectedClose: '2026-11-15', owner: 'Sarah Chen' },
  { id: '2', name: 'Mid-Market — Globex', stage: 'proposal', value: 80000, probability: 50, expectedClose: '2026-12-01', owner: 'Mike Ross' },
  { id: '3', name: 'SMB — Initech', stage: 'prospecting', value: 25000, probability: 25, expectedClose: '2027-01-10', owner: 'Sarah Chen' },
  { id: '4', name: 'Renewal — Umbrella Corp', stage: 'qualification', value: 45000, probability: 90, expectedClose: '2026-10-20', owner: 'Mike Ross' },
  { id: '5', name: 'New Logo — Stark Industries', stage: 'prospecting', value: 200000, probability: 15, expectedClose: '2027-02-28', owner: 'Sarah Chen' },
];

export const FALLBACK_CAMPAIGNS = [
  { id: '1', name: 'Q4 Email Nurture', type: 'email', status: 'active', startDate: '2026-10-01', endDate: '2026-12-31', budget: 15000, spent: 5200 },
  { id: '2', name: 'Product Launch — Social', type: 'social', status: 'active', startDate: '2026-09-15', endDate: '2026-11-15', budget: 30000, spent: 18500 },
  { id: '3', name: 'Retargeting — Display', type: 'display', status: 'paused', startDate: '2026-08-01', endDate: '2026-10-31', budget: 12000, spent: 9800 },
  { id: '4', name: 'Content Marketing', type: 'content', status: 'draft', startDate: '2026-11-01', endDate: '2027-03-31', budget: 25000, spent: 0 },
  { id: '5', name: 'PPC — Brand Terms', type: 'ppc', status: 'completed', startDate: '2026-07-01', endDate: '2026-09-30', budget: 20000, spent: 19500 },
];

export const FALLBACK_ALERTS = [
  { id: '1', name: 'High-value deal stalled', condition: 'stage = negotiation AND days_in_stage > 14', severity: 'high', enabled: true },
  { id: '2', name: 'Campaign budget threshold', condition: 'spent / budget > 0.8', severity: 'medium', enabled: true },
  { id: '3', name: 'New lead assignment', condition: 'lead.created AND lead.owner IS NULL', severity: 'low', enabled: true },
  { id: '4', name: 'Report delivery failure', condition: 'report.delivery_status = failed', severity: 'critical', enabled: true },
  { id: '5', name: 'User login anomaly', condition: 'user.login_count_1h > 10', severity: 'high', enabled: false },
];

export const FALLBACK_USERS = [
  { id: 1, name: 'Admin User', email: 'admin@apexos.io', role: 'admin', is_active: true },
  { id: 2, name: 'Sarah Chen', email: 'sarah@apexos.io', role: 'editor', is_active: true },
  { id: 3, name: 'Mike Ross', email: 'mike@apexos.io', role: 'editor', is_active: true },
  { id: 4, name: 'Jane Smith', email: 'jane@apexos.io', role: 'viewer', is_active: false },
  { id: 5, name: 'Bob Wilson', email: 'bob@apexos.io', role: 'viewer', is_active: true },
];

export const FALLBACK_LEADS = [
  { id: '1', name: 'John Doe', email: 'john@acme.com', phone: '+1-555-0101', company: 'Acme Corp', status: 'new', source: 'Website', notes: 'Interested in enterprise plan', created_at: '2026-10-01' },
  { id: '2', name: 'Alice Wong', email: 'alice@globex.com', phone: '+1-555-0102', company: 'Globex', status: 'contacted', source: 'Referral', notes: 'Follow up next week', created_at: '2026-10-02' },
  { id: '3', name: 'Carlos Ruiz', email: 'carlos@initech.com', phone: '+1-555-0103', company: 'Initech', status: 'qualified', source: 'PPC', notes: 'Budget approved', created_at: '2026-10-03' },
  { id: '4', name: 'Emma Davis', email: 'emma@umbrella.com', phone: '+1-555-0104', company: 'Umbrella Corp', status: 'lost', source: 'Social', notes: 'Went with competitor', created_at: '2026-09-15' },
  { id: '5', name: 'Liam Park', email: 'liam@stark.com', phone: '+1-555-0105', company: 'Stark Industries', status: 'new', source: 'Event', notes: 'Met at conference', created_at: '2026-10-04' },
];

export const FALLBACK_REPORTS = [
  { id: '1', name: 'Monthly Sales Summary', type: 'sales', description: 'Aggregated sales metrics for the current month', schedule: 'monthly', recipients: ['admin@apexos.io'], status: 'active', deliveryStatus: 'delivered', views: 142, downloads: 38, lastRun: '2026-10-01T08:00:00Z', createdAt: '2026-01-15' },
  { id: '2', name: 'Inventory Health Check', type: 'inventory', description: 'Stock levels, turnover rates, and reorder alerts', schedule: 'weekly', recipients: ['admin@apexos.io', 'sarah@apexos.io'], status: 'active', deliveryStatus: 'delivered', views: 89, downloads: 21, lastRun: '2026-10-03T06:00:00Z', createdAt: '2026-02-10' },
  { id: '3', name: 'Financial Dashboard', type: 'financial', description: 'Revenue, expenses, and profitability analysis', schedule: 'daily', recipients: ['admin@apexos.io'], status: 'active', deliveryStatus: 'pending', views: 256, downloads: 67, lastRun: '2026-10-05T00:00:00Z', createdAt: '2026-01-01' },
  { id: '4', name: 'Customer Churn Analysis', type: 'customer', description: 'Churn patterns and retention metrics', schedule: 'weekly', recipients: ['sarah@apexos.io'], status: 'paused', deliveryStatus: 'failed', views: 45, downloads: 12, lastRun: '2026-09-28T06:00:00Z', createdAt: '2026-03-05' },
  { id: '5', name: 'Custom Executive Report', type: 'custom', description: 'Ad-hoc executive summary with KPIs', schedule: 'none', recipients: ['admin@apexos.io'], status: 'draft', deliveryStatus: 'pending', views: 0, downloads: 0, createdAt: '2026-10-01' },
];
