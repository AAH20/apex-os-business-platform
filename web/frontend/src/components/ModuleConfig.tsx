import React, { useState, useMemo } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

type Scale = 'Startup' | 'SMB' | 'Enterprise';
type ModuleStatus = 'active' | 'inactive' | 'recommended';
type Category = 'Core' | 'Advanced' | 'Enterprise';

interface ModuleDef {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: Category;
  dependencies: string[];
  recommendedFor: Scale[];
}

// ─── Module Definitions ─────────────────────────────────────────────────────

const MODULES: ModuleDef[] = [
  {
    id: 'accounting',
    name: 'Accounting',
    description: 'General ledger, accounts payable/receivable, and financial statements.',
    icon: '📊',
    category: 'Core',
    dependencies: [],
    recommendedFor: ['Startup', 'SMB', 'Enterprise'],
  },
  {
    id: 'crm',
    name: 'CRM',
    description: 'Customer relationship management, sales pipeline, and contact tracking.',
    icon: '🤝',
    category: 'Core',
    dependencies: [],
    recommendedFor: ['Startup', 'SMB', 'Enterprise'],
  },
  {
    id: 'tasks',
    name: 'Tasks',
    description: 'Task management, assignments, and progress tracking.',
    icon: '✅',
    category: 'Core',
    dependencies: [],
    recommendedFor: ['Startup', 'SMB', 'Enterprise'],
  },
  {
    id: 'projects',
    name: 'Projects',
    description: 'Project planning, milestones, Gantt charts, and resource allocation.',
    icon: '📁',
    category: 'Core',
    dependencies: ['tasks'],
    recommendedFor: ['Startup', 'SMB', 'Enterprise'],
  },
  {
    id: 'billing',
    name: 'Billing',
    description: 'Invoicing, payment processing, and subscription management.',
    icon: '💳',
    category: 'Core',
    dependencies: ['accounting'],
    recommendedFor: ['SMB', 'Enterprise'],
  },
  {
    id: 'inventory',
    name: 'Inventory',
    description: 'Stock tracking, warehouse management, and supply chain oversight.',
    icon: '📦',
    category: 'Advanced',
    dependencies: ['accounting'],
    recommendedFor: ['SMB', 'Enterprise'],
  },
  {
    id: 'analytics',
    name: 'Analytics',
    description: 'Business intelligence dashboards, KPIs, and custom reports.',
    icon: '📈',
    category: 'Advanced',
    dependencies: ['accounting', 'crm'],
    recommendedFor: ['SMB', 'Enterprise'],
  },
  {
    id: 'hr',
    name: 'HR',
    description: 'Employee records, payroll, leave management, and performance reviews.',
    icon: '👥',
    category: 'Advanced',
    dependencies: ['accounting'],
    recommendedFor: ['SMB', 'Enterprise'],
  },
  {
    id: 'reporting',
    name: 'Reporting',
    description: 'Advanced report builder, scheduled exports, and compliance reports.',
    icon: '📋',
    category: 'Advanced',
    dependencies: ['analytics'],
    recommendedFor: ['Enterprise'],
  },
  {
    id: 'audit',
    name: 'Audit Trail',
    description: 'Immutable activity logs, compliance tracking, and change history.',
    icon: '🔒',
    category: 'Enterprise',
    dependencies: ['reporting'],
    recommendedFor: ['Enterprise'],
  },
  {
    id: 'multi-entity',
    name: 'Multi-Entity',
    description: 'Consolidate multiple legal entities with inter-company transactions.',
    icon: '🏢',
    category: 'Enterprise',
    dependencies: ['accounting', 'reporting'],
    recommendedFor: ['Enterprise'],
  },
  {
    id: 'workflow',
    name: 'Workflow Automation',
    description: 'Custom approval workflows, triggers, and automated business processes.',
    icon: '⚡',
    category: 'Enterprise',
    dependencies: ['projects', 'tasks'],
    recommendedFor: ['Enterprise'],
  },
];

// ─── Scale Config ────────────────────────────────────────────────────────────

const SCALE_MODULES: Record<Scale, string[]> = {
  Startup: ['accounting', 'crm', 'tasks', 'projects'],
  SMB: ['accounting', 'crm', 'tasks', 'projects', 'billing', 'inventory', 'analytics', 'hr'],
  Enterprise: MODULES.map((m) => m.id),
};

// ─── Component ───────────────────────────────────────────────────────────────

const ModuleConfig: React.FC = () => {
  const [scale, setScale] = useState<Scale>('Startup');
  const [activeModules, setActiveModules] = useState<Set<string>>(
    () => new Set(SCALE_MODULES.Startup)
  );

  const recommended = useMemo(() => new Set(SCALE_MODULES[scale]), [scale]);

  const getStatus = (id: string): ModuleStatus => {
    if (activeModules.has(id)) return 'active';
    if (recommended.has(id)) return 'recommended';
    return 'inactive';
  };

  const toggleModule = (id: string) => {
    setActiveModules((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        // Check if any active module depends on this one
        const dependents = MODULES.filter(
          (m) => next.has(m.id) && m.dependencies.includes(id)
        );
        if (dependents.length > 0) {
          alert(
            `Cannot deactivate: ${dependents.map((d) => d.name).join(', ')} depend(s) on this module.`
          );
          return prev;
        }
        next.delete(id);
      } else {
        // Auto-activate dependencies
        const mod = MODULES.find((m) => m.id === id);
        if (mod) {
          mod.dependencies.forEach((dep) => next.add(dep));
        }
        next.add(id);
      }
      return next;
    });
  };

  const applyScale = (newScale: Scale) => {
    setScale(newScale);
    setActiveModules(new Set(SCALE_MODULES[newScale]));
  };

  const exportConfig = () => {
    const config = {
      scale,
      modules: MODULES.filter((m) => activeModules.has(m.id)).map((m) => ({
        id: m.id,
        name: m.name,
        category: m.category,
        dependencies: m.dependencies,
      })),
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `module-config-${scale.toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const statusColor = (status: ModuleStatus) => {
    switch (status) {
      case 'active':
        return '#22c55e';
      case 'recommended':
        return '#f59e0b';
      default:
        return '#6b7280';
    }
  };

  return (
    <div
      style={{
        background: '#0f172a',
        color: '#e2e8f0',
        fontFamily: 'system-ui, sans-serif',
        padding: '24px',
        minHeight: '100vh',
      }}
    >
      <h1 style={{ margin: '0 0 8px', fontSize: '24px' }}>Module Configuration</h1>
      <p style={{ color: '#94a3b8', margin: '0 0 24px' }}>
        Configure which modules are active for your organization.
      </p>

      {/* Scale Selector */}
      <div style={{ marginBottom: '24px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
          Organization Scale
        </label>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(['Startup', 'SMB', 'Enterprise'] as Scale[]).map((s) => (
            <button className="bg-gray-700 hover:bg-gray-600 text-gray-100 px-4 py-2 rounded-lg"
              key={s}
              onClick={() => applyScale(s)}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                background: scale === s ? '#3b82f6' : '#1e293b',
                color: scale === s ? '#fff' : '#94a3b8',
                fontWeight: scale === s ? 600 : 400,
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Module Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        {MODULES.map((mod) => {
          const status = getStatus(mod.id);
          return (
            <div
              key={mod.id}
              style={{
                background: '#1e293b',
                borderRadius: '8px',
                padding: '16px',
                border: `1px solid ${statusColor(status)}33`,
                opacity: status === 'inactive' ? 0.6 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '24px' }}>{mod.icon}</span>
                <div>
                  <div style={{ fontWeight: 600 }}>{mod.name}</div>
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>{mod.category}</div>
                </div>
              </div>
              <p style={{ fontSize: '13px', color: '#94a3b8', margin: '0 0 12px' }}>
                {mod.description}
              </p>
              {mod.dependencies.length > 0 && (
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '12px' }}>
                  Requires: {mod.dependencies.join(', ')}
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span
                  style={{
                    fontSize: '12px',
                    color: statusColor(status),
                    fontWeight: 600,
                    textTransform: 'capitalize',
                  }}
                >
                  {status === 'active' ? '● Active' : status === 'recommended' ? '◐ Recommended' : '○ Inactive'}
                </span>
                <button className="bg-gray-700 hover:bg-gray-600 text-gray-100 px-4 py-2 rounded-lg"
                  onClick={() => toggleModule(mod.id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '4px',
                    border: 'none',
                    cursor: 'pointer',
                    background: activeModules.has(mod.id) ? '#ef4444' : '#22c55e',
                    color: '#fff',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                >
                  {activeModules.has(mod.id) ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Export */}
      <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        onClick={exportConfig}
        style={{
          padding: '12px 24px',
          borderRadius: '8px',
          border: 'none',
          cursor: 'pointer',
          background: '#3b82f6',
          color: '#fff',
          fontSize: '14px',
          fontWeight: 600,
        }}
      >
        Export Configuration (JSON)
      </button>
    </div>
  );
};

export default ModuleConfig;
