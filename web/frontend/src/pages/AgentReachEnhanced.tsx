import React, { useState, useEffect, useMemo, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid, Legend } from "recharts";

type AgentStatus = "online" | "busy" | "idle" | "offline";
interface Agent { id: string; name: string; status: AgentStatus; latency: number; throughput: number; success: number; }
interface Route { from: string; to: string; cost: number; hops: number; active: boolean; }

const AGENT_NAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"];
const COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#ef4444", "#a855f7", "#ec4899", "#14b8a6"];
const STATUS_COLORS: Record<AgentStatus, string> = { online: "#10b981", busy: "#f59e0b", idle: "#6366f1", offline: "#ef4444" };

const genAgents = (): Agent[] => AGENT_NAMES.map((name, i) => ({
  id: `agent-${i}`, name,
  status: (["online", "busy", "idle", "offline"] as AgentStatus[])[Math.floor(Math.random() * 4)],
  latency: Math.round(Math.random() * 200 + 20), throughput: Math.round(Math.random() * 500 + 50), success: Math.round(Math.random() * 15 + 85),
}));

const genRoutes = (): Route[] => {
  const r: Route[] = [];
  for (let i = 0; i < AGENT_NAMES.length; i++) for (let j = i + 1; j < AGENT_NAMES.length; j++)
    if (Math.random() > 0.6) r.push({ from: AGENT_NAMES[i], to: AGENT_NAMES[j], cost: +(Math.random() * 10 + 1).toFixed(1), hops: Math.floor(Math.random() * 4 + 1), active: Math.random() > 0.3 });
  return r;
};

const NetworkTopology: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const [tick, setTick] = useState(0);
  useEffect(() => { const t = setInterval(() => setTick((v) => v + 1), 2000); return () => clearInterval(t); }, []);
  const cx = 200, cy = 150, rx = 130, ry = 100;
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Network Topology</h3>
      <svg viewBox="0 0 400 300" className="w-full h-48">
        {agents.map((a, i) => {
          const angle = (i / agents.length) * Math.PI * 2 + tick * 0.1;
          const x = cx + rx * Math.cos(angle), y = cy + ry * Math.sin(angle);
          return <g key={a.id}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="#374151" strokeWidth={1} strokeDasharray={a.status === "offline" ? "4 2" : "none"} />
            <circle cx={x} cy={y} r={14} fill={STATUS_COLORS[a.status]} opacity={0.9}><animate attributeName="r" values="14;16;14" dur="2s" repeatCount="indefinite" /></circle>
            <text x={x} y={y + 4} textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">{a.name[0]}</text>
            <text x={x} y={y + 28} textAnchor="middle" fill="#9ca3af" fontSize="8">{a.name}</text>
          </g>;
        })}
        <circle cx={cx} cy={cy} r={18} fill="#1f2937" stroke="#6366f1" strokeWidth={2} />
        <text x={cx} y={cy + 5} textAnchor="middle" fill="#6366f1" fontSize="10" fontWeight="bold">HUB</text>
      </svg>
    </div>
  );
};

const AgentCard: React.FC<{ agent: Agent }> = ({ agent }) => (
  <div className="bg-gray-800 rounded-lg p-3 border-l-4 transition-all duration-300 hover:scale-105" style={{ borderLeftColor: STATUS_COLORS[agent.status] }}>
    <div className="flex items-center justify-between mb-1">
      <span className="text-sm font-medium text-gray-100">{agent.name}</span>
      <span className="relative flex h-2.5 w-2.5">
        {agent.status === "online" && <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: STATUS_COLORS[agent.status] }} />}
        <span className="relative inline-flex rounded-full h-2.5 w-2.5" style={{ backgroundColor: STATUS_COLORS[agent.status] }} />
      </span>
    </div>
    <div className="text-xs text-gray-400 capitalize">{agent.status}</div>
    <div className="mt-2 space-y-1">
      <div className="flex justify-between text-xs"><span className="text-gray-500">Latency</span><span className="text-gray-300">{agent.latency}ms</span></div>
      <div className="flex justify-between text-xs"><span className="text-gray-500">Throughput</span><span className="text-gray-300">{agent.throughput}/s</span></div>
      <div className="flex justify-between text-xs"><span className="text-gray-500">Success</span><span className="text-gray-300">{agent.success}%</span></div>
    </div>
  </div>
);

const MessageFlow: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const [flow, setFlow] = useState<{ from: number; to: number; progress: number }[]>([]);
  useEffect(() => {
    const t = setInterval(() => {
      setFlow((prev) => {
        const next = prev.map((f) => ({ ...f, progress: f.progress + 0.05 })).filter((f) => f.progress < 1);
        if (Math.random() > 0.5 && agents.length > 1) {
          const from = Math.floor(Math.random() * agents.length);
          let to = Math.floor(Math.random() * agents.length);
          if (to === from) to = (to + 1) % agents.length;
          next.push({ from, to, progress: 0 });
        }
        return next;
      });
    }, 100);
    return () => clearInterval(t);
  }, [agents.length]);
  const nodes = agents.slice(0, 6);
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Message Flow</h3>
      <svg viewBox="0 0 400 120" className="w-full h-28">
        {nodes.map((n, i) => { const x = 40 + i * 64; return <g key={n.id}><rect x={x - 18} y={45} width={36} height={30} rx={6} fill={STATUS_COLORS[n.status]} opacity={0.8} /><text x={x} y={64} textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">{n.name}</text></g>; })}
        {flow.map((f, i) => { const x1 = 40 + f.from * 64, x2 = 40 + f.to * 64; const mx = x1 + (x2 - x1) * f.progress; return <circle key={i} cx={mx} cy={60} r={3} fill="#22d3ee" opacity={0.9} />; })}
      </svg>
    </div>
  );
};

const ThroughputChart: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const [data, setData] = useState<{ time: string; [k: string]: number | string }[]>([]);
  useEffect(() => {
    const t = setInterval(() => {
      setData((prev) => {
        const point: { time: string; [k: string]: number | string } = { time: new Date().toLocaleTimeString() };
        agents.forEach((a) => { point[a.name] = Math.round(Math.random() * 500 + 50); });
        return [...prev.slice(-19), point];
      });
    }, 1000);
    return () => clearInterval(t);
  }, [agents]);
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Throughput (real-time)</h3>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: 8 }} />
          {agents.slice(0, 4).map((a, i) => <Line key={a.id} type="monotone" dataKey={a.name} stroke={COLORS[i]} strokeWidth={2} dot={false} isAnimationActive={false} />)}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const DonutChart: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const dist = useMemo(() => {
    const counts: Record<string, number> = {};
    agents.forEach((a) => { counts[a.status] = (counts[a.status] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [agents]);
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Message Distribution</h3>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie data={dist} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={3} dataKey="value">
            {dist.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: 8 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

const PerformanceTable: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const [sortKey, setSortKey] = useState<keyof Agent>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const sorted = useMemo(() => [...agents].sort((a, b) => {
    const aV = a[sortKey], bV = b[sortKey];
    if (typeof aV === "string") return sortDir === "asc" ? aV.localeCompare(bV as string) : (bV as string).localeCompare(aV);
    return sortDir === "asc" ? (aV as number) - (bV as number) : (bV as number) - (aV as number);
  }), [agents, sortKey, sortDir]);
  const handleSort = useCallback((key: keyof Agent) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc")); else { setSortKey(key); setSortDir("asc"); }
  }, [sortKey]);
  const cols: { key: keyof Agent; label: string }[] = [
    { key: "name", label: "Agent" }, { key: "status", label: "Status" }, { key: "latency", label: "Latency" }, { key: "throughput", label: "Throughput" }, { key: "success", label: "Success %" },
  ];
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700 overflow-x-auto">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Performance</h3>
      <table className="w-full text-xs">
        <thead><tr className="text-gray-400 border-b border-gray-700">
          {cols.map((c) => <th key={c.key} className="text-left py-2 px-2 cursor-pointer hover:text-gray-200" onClick={() => handleSort(c.key)}>{c.label} {sortKey === c.key && (sortDir === "asc" ? "↑" : "↓")}</th>)}
        </tr></thead>
        <tbody>{sorted.map((a) => (
          <tr key={a.id} className="border-b border-gray-800 hover:bg-gray-800/50">
            <td className="py-2 px-2 text-gray-200 font-medium">{a.name}</td>
            <td className="py-2 px-2"><span className="px-2 py-0.5 rounded-full text-xs" style={{ backgroundColor: STATUS_COLORS[a.status] + "22", color: STATUS_COLORS[a.status] }}>{a.status}</span></td>
            <td className="py-2 px-2 text-gray-300">{a.latency}ms</td><td className="py-2 px-2 text-gray-300">{a.throughput}/s</td><td className="py-2 px-2 text-gray-300">{a.success}%</td>
          </tr>))}</tbody>
      </table>
    </div>
  );
};

const HealthMonitor: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const health = useMemo(() => {
    const online = agents.filter((a) => a.status === "online").length;
    return { online, total: agents.length, avgLatency: agents.length ? Math.round(agents.reduce((s, a) => s + a.latency, 0) / agents.length) : 0, avgSuccess: agents.length ? Math.round(agents.reduce((s, a) => s + a.success, 0) / agents.length) : 0 };
  }, [agents]);
  const metrics = [
    { label: "Online", value: `${health.online}/${health.total}`, color: "#10b981" },
    { label: "Avg Latency", value: `${health.avgLatency}ms`, color: "#6366f1" },
    { label: "Avg Success", value: `${health.avgSuccess}%`, color: "#22d3ee" },
  ];
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">Agent Health</h3>
      <div className="grid grid-cols-3 gap-3">{metrics.map((m) => (<div key={m.label} className="text-center"><div className="text-lg font-bold" style={{ color: m.color }}>{m.value}</div><div className="text-xs text-gray-500">{m.label}</div></div>))}</div>
      <div className="mt-3 h-2 bg-gray-800 rounded-full overflow-hidden"><div className="h-full rounded-full transition-all duration-500" style={{ width: `${health.total ? (health.online / health.total) * 100 : 0}%`, backgroundColor: "#10b981" }} /></div>
    </div>
  );
};

const RouteOptimization: React.FC<{ routes: Route[] }> = ({ routes }) => {
  const sorted = useMemo(() => [...routes].sort((a, b) => a.cost - b.cost).slice(0, 8), [routes]);
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Route Optimization</h3>
      <div className="space-y-1.5 max-h-48 overflow-y-auto">{sorted.map((r, i) => (
        <div key={i} className="flex items-center justify-between text-xs bg-gray-800/50 rounded px-2 py-1.5">
          <span className="text-gray-300">{r.from} → {r.to}</span>
          <div className="flex items-center gap-2"><span className="text-gray-500">{r.hops} hops</span><span className="font-mono text-cyan-400">{r.cost.toFixed(1)}</span><span className={`w-1.5 h-1.5 rounded-full ${r.active ? "bg-green-400" : "bg-red-400"}`} /></div>
        </div>))}</div>
    </div>
  );
};

const AgentReachEnhanced: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>(genAgents);
  const [routes, setRoutes] = useState<Route[]>(genRoutes);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => {
      setAgents((prev) => prev.map((a) => ({ ...a, latency: Math.max(10, a.latency + Math.round((Math.random() - 0.5) * 20)), throughput: Math.max(10, a.throughput + Math.round((Math.random() - 0.5) * 50)), success: Math.min(100, Math.max(70, a.success + Math.round((Math.random() - 0.5) * 4))) })));
      setRoutes(genRoutes()); setLastUpdate(new Date());
    }, 3000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6"><div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-2xl font-bold">AgentReach <span className="text-indigo-400">Enhanced</span></h1><p className="text-sm text-gray-500">Real-time agent network monitoring & optimization</p></div>
        <div className="text-xs text-gray-500">Last update: {lastUpdate.toLocaleTimeString()}</div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4"><NetworkTopology agents={agents} /><MessageFlow agents={agents} /><HealthMonitor agents={agents} /></div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4"><ThroughputChart agents={agents} /><DonutChart agents={agents} /></div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4"><div className="lg:col-span-2"><PerformanceTable agents={agents} /></div><RouteOptimization routes={routes} /></div>
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">{agents.map((a) => <AgentCard key={a.id} agent={a} />)}</div>
    </div></div>
  );
};

export default AgentReachEnhanced;
