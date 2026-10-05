import React, { useState, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { ActionButtons } from '../components/ActionButtons';

const models = [
  { name: 'XGBoost-v3', accuracy: 0.94, precision: 0.92, recall: 0.89, f1: 0.905, latency: 12, status: 'production' },
  { name: 'LightGBM-v2', accuracy: 0.91, precision: 0.89, recall: 0.87, f1: 0.880, latency: 8, status: 'production' },
  { name: 'NeuralNet-v4', accuracy: 0.96, precision: 0.95, recall: 0.93, f1: 0.940, latency: 45, status: 'staging' },
  { name: 'RandomForest-v1', accuracy: 0.87, precision: 0.85, recall: 0.83, f1: 0.840, latency: 5, status: 'archived' },
];

const featureImportance = [
  { feature: 'tenure', importance: 0.28 }, { feature: 'monthly_spend', importance: 0.22 },
  { feature: 'support_tickets', importance: 0.18 }, { feature: 'login_freq', importance: 0.14 },
  { feature: 'nps_score', importance: 0.10 }, { feature: 'region', importance: 0.08 },
];

const experiments = [
  { id: 'EXP-001', name: 'Hyperparameter Tuning', progress: 100, status: 'completed', bestF1: 0.94 },
  { id: 'EXP-002', name: 'Feature Selection v2', progress: 75, status: 'running', bestF1: 0.91 },
  { id: 'EXP-003', name: 'Ensemble Stacking', progress: 40, status: 'running', bestF1: 0.89 },
  { id: 'EXP-004', name: 'Data Augmentation', progress: 15, status: 'queued', bestF1: 0.0 },
];

const registry = [
  { name: 'churn-predictor', version: '3.2.1', stage: 'Production', updated: '2026-10-01', author: 'alice' },
  { name: 'churn-predictor', version: '3.2.0', stage: 'Staging', updated: '2026-09-28', author: 'bob' },
  { name: 'churn-predictor', version: '3.1.0', stage: 'Archived', updated: '2026-09-15', author: 'alice' },
  { name: 'recommendation', version: '2.0.3', stage: 'Production', updated: '2026-10-02', author: 'carol' },
  { name: 'anomaly-detector', version: '1.4.0', stage: 'Staging', updated: '2026-09-30', author: 'dave' },
];

const latencyData = [
  { name: 'RF-v1', p50: 3, p95: 5, p99: 8 }, { name: 'LGBM-v2', p50: 5, p95: 8, p99: 12 },
  { name: 'XGB-v3', p50: 8, p95: 12, p99: 18 }, { name: 'NN-v4', p50: 32, p95: 45, p99: 62 },
];

const abTests = [
  { test: 'T-101', variant: 'A: Control', conversion: 12.4, lift: 0, significance: 95 },
  { test: 'T-101', variant: 'B: Treatment', conversion: 14.8, lift: 19.4, significance: 97 },
  { test: 'T-102', variant: 'A: Control', conversion: 8.2, lift: 0, significance: 92 },
  { test: 'T-102', variant: 'B: Treatment', conversion: 9.1, lift: 11.0, significance: 88 },
];

const driftAlerts = [
  { feature: 'monthly_spend', psi: 0.32, severity: 'high', detected: '2h ago' },
  { feature: 'login_freq', psi: 0.18, severity: 'medium', detected: '6h ago' },
  { feature: 'nps_score', psi: 0.09, severity: 'low', detected: '1d ago' },
];

const trainingHistory = [
  { epoch: 1, trainLoss: 0.68, valLoss: 0.72, auc: 0.71 },
  { epoch: 5, trainLoss: 0.45, valLoss: 0.52, auc: 0.82 },
  { epoch: 10, trainLoss: 0.32, valLoss: 0.41, auc: 0.89 },
  { epoch: 15, trainLoss: 0.25, valLoss: 0.38, auc: 0.92 },
  { epoch: 20, trainLoss: 0.21, valLoss: 0.36, auc: 0.94 },
  { epoch: 25, trainLoss: 0.19, valLoss: 0.37, auc: 0.94 },
];

const severityColor: Record<string, string> = { high: 'bg-red-100 text-red-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-green-100 text-green-700' };
const stageColor: Record<string, string> = { Production: 'bg-emerald-100 text-emerald-700', Staging: 'bg-blue-100 text-blue-700', Archived: 'bg-gray-800 text-gray-400' };

const DataScienceEnhanced: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState('XGBoost-v3');
  const [activeTab, setActiveTab] = useState<'overview' | 'experiments' | 'registry'>('overview');

  const [_chartData] = useMemo(() => [models.map(m => ({ name: m.name, accuracy: m.accuracy * 100, f1: m.f1 * 100 }))], []);

  // Action Buttons State
  const [, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Action Buttons Handlers
  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleExportCSV = () => {
    if (!models || models.length === 0) return;
    const headers = Object.keys(models[0]);
    const csv = [headers.join(','), ...models.map((item: any) => headers.map(h => `"${String(item[h] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'DataScienceEnhanced_export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    if (!models || models.length === 0) return;
    const blob = new Blob([JSON.stringify(models, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'DataScienceEnhanced_export.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} selected item(s)?`)) return;
    setSelectedIds(new Set());
  };

  return (
    <div className="p-6 space-y-6 bg-gray-900 min-h-screen">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Data Science Platform</h1>
        <div className="flex gap-2">
          {(['overview', 'experiments', 'registry'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${activeTab === tab ? 'bg-indigo-600 text-white' : 'bg-gray-900 text-gray-400 border'}`}>
              {tab}
            </button>
          ))}
        </div>
      </div>
      <ActionButtons
        onSearch={handleSearch}
        onExportCSV={handleExportCSV}
        onExportJSON={handleExportJSON}
        onRefresh={handleRefresh}
        onBulkDelete={handleBulkDelete}
        selectedCount={selectedIds.size}
        searchPlaceholder="Search models..."
      />

      {/* Model Comparison Table */}
      <div className="bg-gray-900 rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-3">Model Comparison</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b text-left text-gray-400">
              <th className="pb-2">Model</th><th className="pb-2">Accuracy</th><th className="pb-2">Precision</th>
              <th className="pb-2">Recall</th><th className="pb-2">F1</th><th className="pb-2">Latency (ms)</th><th className="pb-2">Status</th>
            </tr></thead>
            <tbody>
              {models.map(m => (
                <tr key={m.name} className={`border-b cursor-pointer ${selectedModel === m.name ? 'bg-indigo-50' : ''}`}
                  onClick={() => setSelectedModel(m.name)}>
                  <td className="py-2 font-medium">{m.name}</td>
                  <td>{(m.accuracy * 100).toFixed(1)}%</td><td>{(m.precision * 100).toFixed(1)}%</td>
                  <td>{(m.recall * 100).toFixed(1)}%</td><td>{(m.f1 * 100).toFixed(1)}%</td>
                  <td>{m.latency}</td>
                  <td><span className={`px-2 py-0.5 rounded-full text-xs ${m.status === 'production' ? 'bg-emerald-100 text-emerald-700' : m.status === 'staging' ? 'bg-blue-100 text-blue-700' : 'bg-gray-800 text-gray-400'}`}>{m.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Feature Importance */}
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Feature Importance</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={featureImportance} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 0.3]} />
              <YAxis type="category" dataKey="feature" width={100} />
              <Tooltip />
              <Bar dataKey="importance" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Latency Comparison */}
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Latency Comparison (ms)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={latencyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" /><YAxis />
              <Tooltip /><Legend />
              <Bar dataKey="p50" fill="#818cf8" name="p50" />
              <Bar dataKey="p95" fill="#6366f1" name="p95" />
              <Bar dataKey="p99" fill="#4338ca" name="p99" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Training History */}
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Training History</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trainingHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="epoch" /><YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" domain={[0.6, 1]} />
              <Tooltip /><Legend />
              <Line yAxisId="left" type="monotone" dataKey="trainLoss" stroke="#6366f1" name="Train Loss" />
              <Line yAxisId="left" type="monotone" dataKey="valLoss" stroke="#f59e0b" name="Val Loss" />
              <Line yAxisId="right" type="monotone" dataKey="auc" stroke="#10b981" name="AUC" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* A/B Test Results */}
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">A/B Test Results</h2>
          <div className="space-y-3">
            {abTests.map((t, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
                <div>
                  <span className="font-medium text-sm">{t.test}</span>
                  <span className="ml-2 text-xs text-gray-400">{t.variant}</span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span>Conv: <strong>{t.conversion}%</strong></span>
                  <span className={t.lift > 0 ? 'text-green-600' : 'text-gray-400'}>Lift: {t.lift > 0 ? '+' : ''}{t.lift}%</span>
                  <span className="text-xs text-gray-400">sig: {t.significance}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Experiment Progress */}
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Experiment Progress</h2>
          <div className="space-y-4">
            {experiments.map(exp => (
              <div key={exp.id}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{exp.name}</span>
                  <span className="text-gray-400">{exp.progress}% · {exp.status}</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2.5">
                  <div className={`h-2.5 rounded-full ${exp.status === 'completed' ? 'bg-emerald-500' : exp.status === 'running' ? 'bg-indigo-500' : 'bg-gray-400'}`}
                    style={{ width: `${exp.progress}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Drift Detection */}
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Drift Detection Alerts</h2>
          <div className="space-y-3">
            {driftAlerts.map((d, i) => (
              <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <span className="font-medium text-sm">{d.feature}</span>
                  <span className="ml-2 text-xs text-gray-400">{d.detected}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm">PSI: <strong>{d.psi}</strong></span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${severityColor[d.severity]}`}>{d.severity}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Model Registry */}
      <div className="bg-gray-900 rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-3">Model Registry</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b text-left text-gray-400">
              <th className="pb-2">Model</th><th className="pb-2">Version</th><th className="pb-2">Stage</th>
              <th className="pb-2">Author</th><th className="pb-2">Updated</th>
            </tr></thead>
            <tbody>
              {registry.map((r, i) => (
                <tr key={i} className="border-b">
                  <td className="py-2 font-medium">{r.name}</td>
                  <td className="py-2"><code className="bg-gray-800 px-1.5 py-0.5 rounded">{r.version}</code></td>
                  <td className="py-2"><span className={`px-2 py-0.5 rounded-full text-xs ${stageColor[r.stage]}`}>{r.stage}</span></td>
                  <td className="py-2">{r.author}</td><td className="py-2 text-gray-400">{r.updated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DataScienceEnhanced;
