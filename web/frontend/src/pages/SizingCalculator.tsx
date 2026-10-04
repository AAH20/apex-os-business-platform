import React, { useState, useMemo } from 'react';

type ScaleTier = 'Startup' | 'SMB' | 'Enterprise' | 'Large Enterprise';
type InfraSize = 'small' | 'medium' | 'large' | 'xlarge';

interface Inputs {
  employees: number;
  monthlyTransactions: number;
  dataVolumeGB: number;
  concurrentUsers: number;
}

interface Module {
  name: string;
  description: string;
  required: boolean;
}

interface InfraSpec {
  size: InfraSize;
  cpu: string;
  ram: string;
  storage: string;
  nodes: number;
}

interface Recommendation {
  tier: ScaleTier;
  modules: Module[];
  infra: InfraSpec;
  monthlyCost: number;
  annualCost: number;
  timelineWeeks: number;
  summary: string;
}

const ALL_MODULES: Record<string, Module> = {
  core: { name: 'Core Platform', description: 'Authentication, RBAC, audit logging', required: true },
  crm: { name: 'CRM', description: 'Customer relationship management', required: false },
  erp: { name: 'ERP', description: 'Enterprise resource planning', required: false },
  analytics: { name: 'Analytics', description: 'Business intelligence & dashboards', required: false },
  workflow: { name: 'Workflow Engine', description: 'Process automation & approvals', required: false },
  integrations: { name: 'Integrations Hub', description: 'Third-party API connectors', required: false },
  ai: { name: 'AI Insights', description: 'Predictive analytics & recommendations', required: false },
  compliance: { name: 'Compliance Suite', description: 'GDPR, SOC2, HIPAA controls', required: false },
  multiTenant: { name: 'Multi-Tenant', description: 'Isolated tenant environments', required: false },
  advancedSecurity: { name: 'Advanced Security', description: 'SSO, MFA, encryption at rest', required: false },
};

function getTier(employees: number): ScaleTier {
  if (employees <= 10) return 'Startup';
  if (employees <= 100) return 'SMB';
  if (employees <= 1000) return 'Enterprise';
  return 'Large Enterprise';
}

function getModules(tier: ScaleTier, transactions: number): Module[] {
  const mods: Module[] = [ALL_MODULES.core];
  if (tier === 'Startup') {
    mods.push(ALL_MODULES.crm);
  } else if (tier === 'SMB') {
    mods.push(ALL_MODULES.crm, ALL_MODULES.analytics, ALL_MODULES.workflow);
  } else if (tier === 'Enterprise') {
    mods.push(ALL_MODULES.crm, ALL_MODULES.erp, ALL_MODULES.analytics, ALL_MODULES.workflow, ALL_MODULES.integrations, ALL_MODULES.advancedSecurity);
  } else {
    mods.push(ALL_MODULES.crm, ALL_MODULES.erp, ALL_MODULES.analytics, ALL_MODULES.workflow, ALL_MODULES.integrations, ALL_MODULES.ai, ALL_MODULES.compliance, ALL_MODULES.multiTenant, ALL_MODULES.advancedSecurity);
  }
  if (transactions > 100000 && tier !== 'Startup') {
    mods.push(ALL_MODULES.ai);
  }
  return mods;
}

function getInfra(tier: ScaleTier, dataGB: number, concurrent: number): InfraSpec {
  if (tier === 'Startup') {
    return { size: 'small', cpu: '2 vCPU', ram: '4 GB', storage: `${Math.max(50, Math.ceil(dataGB * 1.5))} GB SSD`, nodes: 1 };
  }
  if (tier === 'SMB') {
    return { size: 'medium', cpu: '4 vCPU', ram: '8 GB', storage: `${Math.max(200, Math.ceil(dataGB * 1.5))} GB SSD`, nodes: 2 };
  }
  if (tier === 'Enterprise') {
    const nodes = concurrent > 500 ? 4 : 3;
    return { size: 'large', cpu: '8 vCPU', ram: '16 GB', storage: `${Math.max(1000, Math.ceil(dataGB * 2))} GB SSD`, nodes };
  }
  const nodes = concurrent > 2000 ? 8 : 5;
  return { size: 'xlarge', cpu: '16 vCPU', ram: '32 GB', storage: `${Math.max(5000, Math.ceil(dataGB * 2))} GB NVMe`, nodes };
}

function getCost(tier: ScaleTier, infra: InfraSpec, modules: Module[]): { monthly: number; annual: number } {
  const baseCost: Record<ScaleTier, number> = { Startup: 99, SMB: 499, Enterprise: 2499, 'Large Enterprise': 9999 };
  const infraMultiplier: Record<InfraSize, number> = { small: 1, medium: 1.5, large: 2.5, xlarge: 4 };
  const moduleCost = modules.filter(m => m.required === false).length * 50;
  const monthly = Math.round(baseCost[tier] * infraMultiplier[infra.size] + moduleCost);
  return { monthly, annual: monthly * 12 };
}

function getTimeline(tier: ScaleTier, modules: Module[]): number {
  const baseWeeks: Record<ScaleTier, number> = { Startup: 2, SMB: 4, Enterprise: 8, 'Large Enterprise': 16 };
  return baseWeeks[tier] + Math.floor(modules.length / 3);
}

function buildRecommendation(inputs: Inputs): Recommendation {
  const tier = getTier(inputs.employees);
  const modules = getModules(tier, inputs.monthlyTransactions);
  const infra = getInfra(tier, inputs.dataVolumeGB, inputs.concurrentUsers);
  const cost = getCost(tier, infra, modules);
  const timelineWeeks = getTimeline(tier, modules);
  const summary = `${tier} deployment: ${modules.length} modules, ${infra.nodes} node(s) (${infra.cpu}, ${infra.ram}), ~$${cost.monthly}/mo, ${timelineWeeks}-week rollout.`;
  return { tier, modules, infra, monthlyCost: cost.monthly, annualCost: cost.annual, timelineWeeks, summary };
}

function exportJSON(rec: Recommendation, inputs: Inputs) {
  const blob = new Blob([JSON.stringify({ inputs, recommendation: rec }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sizing-${rec.tier.toLowerCase().replace(/\s+/g, '-')}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportPDF(rec: Recommendation, inputs: Inputs) {
  const lines = [
    'APEX-OS Sizing Recommendation', '',
    `Tier: ${rec.tier}`, `Timeline: ${rec.timelineWeeks} weeks`, '',
    'Inputs:', `  Employees: ${inputs.employees}`, `  Monthly Transactions: ${inputs.monthlyTransactions}`, `  Data Volume: ${inputs.dataVolumeGB} GB`, `  Concurrent Users: ${inputs.concurrentUsers}`, '',
    'Modules:', ...rec.modules.map(m => `  - ${m.name}: ${m.description}`), '',
    'Infrastructure:', `  Size: ${rec.infra.size}`, `  CPU: ${rec.infra.cpu}`, `  RAM: ${rec.infra.ram}`, `  Storage: ${rec.infra.storage}`, `  Nodes: ${rec.infra.nodes}`, '',
    'Cost:', `  Monthly: $${rec.monthlyCost}`, `  Annual: $${rec.annualCost}`,
  ];
  const win = window.open('', '_blank');
  if (win) {
    win.document.write(`<html><head><title>Sizing Recommendation</title><style>body{font-family:monospace;padding:40px;background:#1a1a2e;color:#e0e0e0;white-space:pre-wrap;}</style></head><body>${lines.join('\n')}</body></html>`);
    win.document.close();
    win.print();
  }
}

export default function SizingCalculator() {
  const [inputs, setInputs] = useState<Inputs>({ employees: 50, monthlyTransactions: 10000, dataVolumeGB: 500, concurrentUsers: 25 });
  const rec = useMemo(() => buildRecommendation(inputs), [inputs]);

  const inputStyle: React.CSSProperties = { background: '#16213e', border: '1px solid #0f3460', borderRadius: 6, color: '#e0e0e0', padding: '8px 12px', width: '100%' };
  const cardStyle: React.CSSProperties = { background: '#16213e', borderRadius: 12, padding: 20, border: '1px solid #0f3460' };
  const labelStyle: React.CSSProperties = { display: 'block', marginBottom: 4, fontSize: 13, color: '#a0a0b0' };

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', padding: 24 }}>
      <h1 style={{ marginBottom: 24 }}>APEX-OS Sizing Calculator</h1>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24, maxWidth: 1200, margin: '0 auto' }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0 }}>Organization Inputs</h2>
          {([['employees', 'Employees'], ['monthlyTransactions', 'Monthly Transactions'], ['dataVolumeGB', 'Data Volume (GB)'], ['concurrentUsers', 'Concurrent Users']] as const).map(([key, label]) => (
            <div key={key} style={{ marginBottom: 16 }}>
              <label style={labelStyle}>{label}</label>
              <input type="number" style={inputStyle} value={inputs[key]} onChange={e => setInputs(p => ({ ...p, [key]: Number(e.target.value) }))} />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Scale Tier: {rec.tier}</h2>
            <p style={{ color: '#a0a0b0' }}>{rec.summary}</p>
          </div>
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Recommended Modules ({rec.modules.length})</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {rec.modules.map(m => (
                <div key={m.name} style={{ background: '#1a1a2e', padding: 10, borderRadius: 6, border: '1px solid #0f3460' }}>
                  <strong>{m.name}</strong>
                  <p style={{ margin: '4px 0 0', fontSize: 12, color: '#a0a0b0' }}>{m.description}</p>
                </div>
              ))}
            </div>
          </div>
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Infrastructure: {rec.infra.size}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, textAlign: 'center' }}>
              {([['CPU', rec.infra.cpu], ['RAM', rec.infra.ram], ['Storage', rec.infra.storage], ['Nodes', String(rec.infra.nodes)], ['Timeline', `${rec.timelineWeeks} wks`]] as const).map(([k, v]) => (
                <div key={k} style={{ background: '#1a1a2e', padding: 10, borderRadius: 6 }}>
                  <div style={{ fontSize: 11, color: '#a0a0b0' }}>{k}</div>
                  <div style={{ fontWeight: 600 }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Cost Estimate</h3>
            <div style={{ display: 'flex', gap: 32 }}>
              <div><span style={{ fontSize: 28, fontWeight: 700 }}>${rec.monthlyCost}</span><span style={{ color: '#a0a0b0' }}>/mo</span></div>
              <div><span style={{ fontSize: 28, fontWeight: 700 }}>${rec.annualCost}</span><span style={{ color: '#a0a0b0' }}>/yr</span></div>
            </div>
            <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
              <button onClick={() => exportPDF(rec, inputs)} style={{ background: '#0f3460', color: '#e0e0e0', border: 'none', borderRadius: 6, padding: '10px 20px', cursor: 'pointer' }}>Export PDF</button>
              <button onClick={() => exportJSON(rec, inputs)} style={{ background: '#0f3460', color: '#e0e0e0', border: 'none', borderRadius: 6, padding: '10px 20px', cursor: 'pointer' }}>Export JSON</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
