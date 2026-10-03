import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#818cf8', '#7c3aed'];

const kpiData = [
  { label: 'Revenue', value: '$284,500', change: '+12.4%', spark: [12, 15, 14, 18, 22, 20, 25, 28, 24, 30, 32, 35] },
  { label: 'Active Users', value: '48,291', change: '+8.1%', spark: [30, 32, 35, 33, 38, 40, 37, 42, 45, 43, 47, 48] },
  { label: 'Conversion', value: '3.42%', change: '-0.3%', spark: [4, 3.8, 3.9, 3.7, 3.5, 3.6, 3.4, 3.5, 3.3, 3.4, 3.4, 3.42] },
  { label: 'Avg Order', value: '$86.20', change: '+5.7%', spark: [70, 72, 75, 73, 78, 80, 79, 82, 84, 83, 85, 86] },
];

const revenueData = [
  { month: 'Jan', revenue: 42000, expenses: 24000 }, { month: 'Feb', revenue: 55000, expenses: 28000 },
  { month: 'Mar', revenue: 48000, expenses: 26000 }, { month: 'Apr', revenue: 62000, expenses: 30000 },
  { month: 'May', revenue: 58000, expenses: 29000 }, { month: 'Jun', revenue: 72000, expenses: 32000 },
  { month: 'Jul', revenue: 68000, expenses: 31000 }, { month: 'Aug', revenue: 78000, expenses: 34000 },
  { month: 'Sep', revenue: 84000, expenses: 36000 }, { month: 'Oct', revenue: 76000, expenses: 33000 },
  { month: 'Nov', revenue: 90000, expenses: 38000 }, { month: 'Dec', revenue: 95000, expenses: 40000 },
];

const funnelData = [
  { stage: 'Visitors', value: 100000, pct: 100 }, { stage: 'Signups', value: 24000, pct: 24 },
  { stage: 'Activated', value: 12000, pct: 12 }, { stage: 'Subscribed', value: 4800, pct: 4.8 },
  { stage: 'Enterprise', value: 960, pct: 0.96 },
];

const geoData = [
  { region: 'North America', revenue: 120000, growth: 15 }, { region: 'Europe', revenue: 85000, growth: 10 },
  { region: 'Asia Pacific', revenue: 52000, growth: 22 }, { region: 'Latin America', revenue: 18000, growth: 8 },
  { region: 'Middle East', revenue: 9500, growth: 18 },
];

const alertRules = [
  { id: 1, name: 'Revenue Drop', condition: 'Revenue < $50K/day', severity: 'critical', active: true },
  { id: 2, name: 'Churn Spike', condition: 'Churn > 5%', severity: 'warning', active: true },
  { id: 3, name: 'API Latency', condition: 'p99 > 500ms', severity: 'warning', active: false },
  { id: 4, name: 'Error Rate', condition: 'Errors > 1%', severity: 'critical', active: true },
  { id: 5, name: 'User Milestone', condition: 'Users > 50K', severity: 'info', active: true },
];

const perfMetrics = [
  { name: 'Page Load', value: '1.2s', status: 'good' }, { name: 'API Response', value: '85ms', status: 'good' },
  { name: 'DB Query', value: '12ms', status: 'good' }, { name: 'Cache Hit', value: '94%', status: 'good' },
  { name: 'Error Rate', value: '0.12%', status: 'good' }, { name: 'Uptime', value: '99.98%', status: 'good' },
];

const generateStreamRow = (id: number) => ({
  id,
  timestamp: new Date().toLocaleTimeString(),
  event: ['purchase', 'signup', 'login', 'upgrade', 'refund'][Math.floor(Math.random() * 5)],
  user: `user_${Math.floor(Math.random() * 10000)}`,
  amount: Math.random() > 0.5 ? `$${(Math.random() * 500).toFixed(2)}` : '—',
  region: ['US', 'EU', 'APAC', 'LATAM'][Math.floor(Math.random() * 4)],
});

const Sparkline: React.FC<{ data: number[]; color?: string }> = ({ data, color = '#6366f1' }) => {
  const max = Math.max(...data); const min = Math.min(...data);
  const points = data.map((v, i) => `${(i / (data.length - 1)) * 100},${30 - ((v - min) / (max - min || 1)) * 28}`).join(' ');
  return (
    <svg viewBox="0 0 100 32" className="w-20 h-8">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

const GlassCard: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-lg shadow-black/20 ${className}`}>
    {children}
  </div>
);

const ContinuousBIEnhanced: React.FC = () => {
  const [streamData, setStreamData] = useState(() => Array.from({ length: 8 }, (_, i) => generateStreamRow(i)));
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    if (!isLive) return;
    const interval = setInterval(() => {
      setStreamData(prev => [generateStreamRow(Date.now()), ...prev.slice(0, 7)]);
      setLastUpdate(new Date());
    }, 2000);
    return () => clearInterval(interval);
  }, [isLive]);

  const toggleLive = useCallback(() => setIsLive(v => !v), []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-white p-6">
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Continuous BI</h1>
          <p className="text-slate-400 text-sm mt-1">Real-time business intelligence dashboard</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            <span className="text-slate-300">{isLive ? 'Live' : 'Paused'}</span>
          </div>
          <span className="text-xs text-slate-500">Updated {lastUpdate.toLocaleTimeString()}</span>
          <button onClick={toggleLive} className="px-3 py-1.5 text-xs rounded-lg bg-white/10 hover:bg-white/20 transition">
            {isLive ? 'Pause' : 'Resume'}
          </button>
        </div>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpiData.map(kpi => (
          <GlassCard key={kpi.label}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider">{kpi.label}</p>
                <p className="text-2xl font-bold mt-1">{kpi.value}</p>
                <span className={`text-xs font-medium ${kpi.change.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'}`}>{kpi.change}</span>
              </div>
              <Sparkline data={kpi.spark} color={kpi.change.startsWith('+') ? '#34d399' : '#fb7185'} />
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Revenue Chart + Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <GlassCard className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Revenue vs Expenses</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={revenueData}>
              <defs>
                <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} tickFormatter={v => `$${v / 1000}K`} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, fontSize: 12 }} />
              <Area type="monotone" dataKey="revenue" stroke="#6366f1" fill="url(#revGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="expenses" stroke="#f43f5e" fill="url(#expGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard>
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Acquisition Funnel</h3>
          <div className="space-y-3">
            {funnelData.map((f, i) => (
              <div key={f.stage}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300">{f.stage}</span>
                  <span className="text-slate-400">{f.value.toLocaleString()} ({f.pct}%)</span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${f.pct}%`, backgroundColor: COLORS[i] }} />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Stream Table + Geo + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <GlassCard className="lg:col-span-1">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Real-time Stream</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-slate-500 border-b border-white/5">
                <th className="text-left pb-2">Event</th><th className="text-left pb-2">Region</th><th className="text-right pb-2">Amount</th>
              </tr></thead>
              <tbody>
                {streamData.slice(0, 6).map(row => (
                  <tr key={row.id} className="border-b border-white/5">
                    <td className="py-1.5 capitalize">{row.event}</td>
                    <td className="py-1.5">{row.region}</td>
                    <td className="py-1.5 text-right font-mono">{row.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Geographic Revenue</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={geoData} dataKey="revenue" nameKey="region" innerRadius={50} outerRadius={80} paddingAngle={3}>
                {geoData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-2 mt-2">
            {geoData.map((g, i) => (
              <span key={g.region} className="flex items-center gap-1 text-xs text-slate-400">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i] }} />{g.region}
              </span>
            ))}
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Alert Rules</h3>
          <div className="space-y-2">
            {alertRules.map(rule => (
              <div key={rule.id} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                <div>
                  <p className="text-xs font-medium">{rule.name}</p>
                  <p className="text-xs text-slate-500">{rule.condition}</p>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  rule.severity === 'critical' ? 'bg-rose-500/20 text-rose-400' :
                  rule.severity === 'warning' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'
                }`}>{rule.active ? 'Active' : 'Off'}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Performance Metrics */}
      <GlassCard>
        <h3 className="text-sm font-semibold text-slate-300 mb-4">System Performance</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {perfMetrics.map(m => (
            <div key={m.name} className="text-center p-3 rounded-xl bg-white/5">
              <p className="text-xs text-slate-400">{m.name}</p>
              <p className="text-lg font-bold mt-1">{m.value}</p>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 mt-1" />
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
};

export default ContinuousBIEnhanced;
