import React, { useState, useEffect } from 'react';
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import {
  TrendingUp, Users, DollarSign, ShoppingCart,
  Activity, Zap, Shield, Server, Database, Globe, Bell,
  Settings, UserPlus, FileText, Calendar, ArrowUpRight,
  CheckCircle, AlertTriangle, Clock, Cpu, HardDrive,
} from 'lucide-react';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];

const kpiData = [
  { title: 'Total Revenue', value: '$128,430', change: '+12.5%', trend: 'up', icon: DollarSign, spark: [30, 45, 35, 55, 48, 62, 58, 72, 68, 85, 78, 92] },
  { title: 'Active Users', value: '24,842', change: '+8.2%', trend: 'up', icon: Users, spark: [20, 28, 25, 35, 32, 42, 38, 48, 45, 55, 52, 62] },
  { title: 'Orders', value: '1,847', change: '-2.4%', trend: 'down', icon: ShoppingCart, spark: [50, 45, 55, 42, 48, 40, 44, 38, 42, 36, 40, 34] },
  { title: 'Conversion', value: '3.24%', change: '+0.8%', trend: 'up', icon: Zap, spark: [2, 2.5, 2.2, 2.8, 2.6, 3, 2.9, 3.1, 3, 3.2, 3.1, 3.24] },
];

const revenueData = [
  { month: 'Jan', revenue: 4200, expenses: 2400 }, { month: 'Feb', revenue: 5800, expenses: 2800 },
  { month: 'Mar', revenue: 5200, expenses: 2600 }, { month: 'Apr', revenue: 7800, expenses: 3200 },
  { month: 'May', revenue: 6900, expenses: 2900 }, { month: 'Jun', revenue: 9200, expenses: 3600 },
  { month: 'Jul', revenue: 8400, expenses: 3100 }, { month: 'Aug', revenue: 10500, expenses: 3800 },
  { month: 'Sep', revenue: 9800, expenses: 3400 }, { month: 'Oct', revenue: 11200, expenses: 4000 },
  { month: 'Nov', revenue: 10800, expenses: 3700 }, { month: 'Dec', revenue: 12800, expenses: 4200 },
];

const userGrowthData = [
  { month: 'Jan', users: 12000 }, { month: 'Feb', users: 14500 }, { month: 'Mar', users: 13800 },
  { month: 'Apr', users: 18200 }, { month: 'May', users: 21000 }, { month: 'Jun', users: 19500 },
  { month: 'Jul', users: 22800 }, { month: 'Aug', users: 24200 }, { month: 'Sep', users: 23500 },
  { month: 'Oct', users: 26100 }, { month: 'Nov', users: 25400 }, { month: 'Dec', users: 28400 },
];

const activityData = [
  { icon: UserPlus, text: 'New user Sarah K. registered', time: '2 min ago', color: 'text-green-500' },
  { icon: ShoppingCart, text: 'Order #4821 placed by Mike R.', time: '5 min ago', color: 'text-blue-500' },
  { icon: AlertTriangle, text: 'Server load exceeded 85%', time: '12 min ago', color: 'text-amber-500' },
  { icon: FileText, text: 'Report Q3-2026 generated', time: '1 hour ago', color: 'text-purple-500' },
  { icon: CheckCircle, text: 'Backup completed successfully', time: '2 hours ago', color: 'text-green-500' },
  { icon: Globe, text: 'New region: EU-West deployed', time: '3 hours ago', color: 'text-indigo-500' },
];

const systemHealth = [
  { name: 'API Server', status: 'operational', uptime: 99.98, icon: Server },
  { name: 'Database', status: 'operational', uptime: 99.95, icon: Database },
  { name: 'CDN Edge', status: 'operational', uptime: 99.99, icon: Globe },
  { name: 'Auth Service', status: 'degraded', uptime: 98.50, icon: Shield },
];

const performanceMetrics = [
  { name: 'CPU Usage', value: 62, color: 'bg-indigo-500' },
  { name: 'Memory', value: 78, color: 'bg-purple-500' },
  { name: 'Disk I/O', value: 45, color: 'bg-blue-500' },
  { name: 'Network', value: 34, color: 'bg-violet-500' },
];

const pieData = [
  { name: 'Desktop', value: 45 }, { name: 'Mobile', value: 35 },
  { name: 'Tablet', value: 15 }, { name: 'Other', value: 5 },
];

const Sparkline: React.FC<{ data: number[]; color: string }> = ({ data, color }) => {
  const max = Math.max(...data), min = Math.min(...data), range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * 100},${32 - ((v - min) / range) * 28 - 2}`).join(' ');
  return <svg viewBox="0 0 100 32" className="w-20 h-8"><polyline fill="none" stroke={color} strokeWidth="2" points={points} /></svg>;
};

const AnimatedCounter: React.FC<{ value: string }> = ({ value }) => {
  const [display, setDisplay] = useState('0');
  useEffect(() => {
    const numeric = parseFloat(value.replace(/[^0-9.]/g, ''));
    const prefix = value.match(/^[^0-9]/) ? value.match(/^[^0-9]/)![0] : '';
    const suffix = value.match(/[^0-9.]$/) ? value.match(/[^0-9.]$/)![0] : '';
    const duration = 1200; const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(prefix + (numeric * eased).toLocaleString(undefined, { maximumFractionDigits: numeric % 1 !== 0 ? 2 : 0 }) + suffix);
      if (progress < 1) requestAnimationFrame(animate);
    };
    animate();
  }, [value]);
  return <span>{display}</span>;
};

const DashboardEnhanced: React.FC = () => {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  const containerClass = `transition-all duration-700 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-indigo-600 via-purple-600 to-violet-700 text-white">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-10 left-10 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-300 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight">Dashboard Overview</h1>
              <p className="mt-2 text-indigo-100 text-lg">Welcome back, Admin. Here's what's happening today.</p>
              <div className="mt-4 flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> Last updated: just now</span>
                <span className="flex items-center gap-1"><Activity className="w-4 h-4" /> All systems operational</span>
              </div>
            </div>
            <div className="mt-6 md:mt-0 flex gap-3">
              <button className="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-lg hover:bg-white/30 transition-colors text-sm font-medium">
                <Calendar className="w-4 h-4 inline mr-1" /> Oct 2026
              </button>
              <button className="px-4 py-2 bg-white text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors text-sm font-semibold shadow-lg">
                <ArrowUpRight className="w-4 h-4 inline mr-1" /> Export
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 -mt-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {kpiData.map((kpi, i) => {
            const Icon = kpi.icon;
            return (
              <div key={i} className={`${containerClass} bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 hover:shadow-md transition-shadow`} style={{ transitionDelay: `${i * 100}ms` }}>
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-2 rounded-lg ${kpi.trend === 'up' ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                    <Icon className={`w-5 h-5 ${kpi.trend === 'up' ? 'text-green-600' : 'text-red-600'}`} />
                  </div>
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${kpi.trend === 'up' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>{kpi.change}</span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400">{kpi.title}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1"><AnimatedCounter value={kpi.value} /></p>
                <div className="mt-3"><Sparkline data={kpi.spark} color={kpi.trend === 'up' ? '#10b981' : '#ef4444'} /></div>
              </div>
            );
          })}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <div><h3 className="text-lg font-semibold text-gray-900 dark:text-white">Revenue & Expenses</h3><p className="text-sm text-gray-500 dark:text-gray-400">Monthly financial overview</p></div>
              <div className="flex gap-4 text-xs"><span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-indigo-500" /> Revenue</span><span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-purple-300" /> Expenses</span></div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={revenueData}>
                <defs>
                  <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} /><stop offset="95%" stopColor="#6366f1" stopOpacity={0} /></linearGradient>
                  <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#a78bfa" stopOpacity={0.3} /><stop offset="95%" stopColor="#a78bfa" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="month" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
                <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2} fill="url(#revenueGrad)" />
                <Area type="monotone" dataKey="expenses" stroke="#a78bfa" strokeWidth={2} fill="url(#expenseGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Traffic by Device</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Session distribution</p>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart><Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">{pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}</Pie><Tooltip /></PieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 gap-2 mt-2">{pieData.map((d, i) => (<div key={i} className="flex items-center gap-2 text-xs"><span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }} /><span className="text-gray-600 dark:text-gray-300">{d.name} ({d.value}%)</span></div>))}</div>
          </div>
        </div>

        {/* User Growth + Activity Timeline */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <div><h3 className="text-lg font-semibold text-gray-900 dark:text-white">User Growth</h3><p className="text-sm text-gray-500 dark:text-gray-400">Monthly active users trend</p></div>
              <span className="text-sm font-medium text-green-600 flex items-center gap-1"><TrendingUp className="w-4 h-4" /> +18.2% YoY</span>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={userGrowthData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="month" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
                <Line type="monotone" dataKey="users" stroke="#8b5cf6" strokeWidth={3} dot={{ fill: '#8b5cf6', r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Activity</h3>
            <div className="space-y-4">{activityData.map((item, i) => { const Icon = item.icon; return (<div key={i} className="flex items-start gap-3 group"><div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-700 group-hover:scale-110 transition-transform"><Icon className={`w-4 h-4 ${item.color}`} /></div><div className="flex-1 min-w-0"><p className="text-sm text-gray-700 dark:text-gray-300 truncate">{item.text}</p><p className="text-xs text-gray-400 mt-0.5">{item.time}</p></div></div>); })}</div>
          </div>
        </div>

        {/* System Health + Performance + Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">System Health</h3>
            <div className="space-y-4">{systemHealth.map((svc, i) => { const Icon = svc.icon; return (<div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"><div className="flex items-center gap-3"><Icon className="w-5 h-5 text-gray-500 dark:text-gray-400" /><div><p className="text-sm font-medium text-gray-900 dark:text-white">{svc.name}</p><p className="text-xs text-gray-500">{svc.uptime}% uptime</p></div></div><span className={`px-2 py-1 rounded-full text-xs font-medium ${svc.status === 'operational' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}`}>{svc.status}</span></div>); })}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance</h3>
            <div className="space-y-5">{performanceMetrics.map((m, i) => (<div key={i}><div className="flex justify-between text-sm mb-1"><span className="text-gray-600 dark:text-gray-300">{m.name}</span><span className="font-medium text-gray-900 dark:text-white">{m.value}%</span></div><div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5"><div className={`h-2.5 rounded-full ${m.color} transition-all duration-1000`} style={{ width: `${m.value}%` }} /></div></div>))}</div>
            <div className="mt-6 grid grid-cols-2 gap-3"><div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"><Cpu className="w-5 h-5 mx-auto text-indigo-500 mb-1" /><p className="text-xs text-gray-500">8 vCPU</p></div><div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"><HardDrive className="w-5 h-5 mx-auto text-purple-500 mb-1" /><p className="text-xs text-gray-500">256 GB</p></div></div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-3">{[{ icon: UserPlus, label: 'Add User', color: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20' }, { icon: FileText, label: 'New Report', color: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20' }, { icon: Bell, label: 'Send Alert', color: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20' }, { icon: Settings, label: 'Settings', color: 'bg-gray-100 text-gray-600 dark:bg-gray-700' }].map((a, i) => { const Icon = a.icon; return (<button key={i} className={`flex flex-col items-center gap-2 p-4 rounded-xl ${a.color} hover:scale-105 transition-transform`}><Icon className="w-6 h-6" /><span className="text-xs font-medium">{a.label}</span></button>); })}</div>
            <div className="mt-4 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl"><p className="text-sm font-medium text-gray-900 dark:text-white">Need help?</p><p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Check our documentation or contact support.</p></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardEnhanced;
