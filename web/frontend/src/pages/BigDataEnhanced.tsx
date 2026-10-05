import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, Legend } from 'recharts';
import { ActionButtons } from '../components/ActionButtons';

const storageData = [
  { name: 'Parquet', value: 420, color: '#3b82f6' },
  { name: 'ORC', value: 280, color: '#10b981' },
  { name: 'Avro', value: 150, color: '#f59e0b' },
  { name: 'JSON', value: 90, color: '#ef4444' },
  { name: 'CSV', value: 60, color: '#8b5cf6' },
];

const datasetComparison = [
  { name: 'events_2024', size: '2.4 TB', rows: '1.2B', format: 'Parquet', compression: 'Snappy', partitions: 365, quality: 98 },
  { name: 'user_profiles', size: '890 GB', rows: '450M', format: 'ORC', compression: 'Zlib', partitions: 128, quality: 95 },
  { name: 'transactions', size: '1.8 TB', rows: '3.8B', format: 'Parquet', compression: 'LZ4', partitions: 730, quality: 99 },
  { name: 'logs_raw', size: '5.2 TB', rows: '12B', format: 'Avro', compression: 'Deflate', partitions: 1095, quality: 87 },
  { name: 'analytics_agg', size: '340 GB', rows: '890M', format: 'Parquet', compression: 'Zstd', partitions: 64, quality: 97 },
];

const queryTimelineData = [
  { time: '00:00', queries: 12, latency: 45 }, { time: '02:00', queries: 8, latency: 38 },
  { time: '04:00', queries: 5, latency: 32 }, { time: '06:00', queries: 18, latency: 52 },
  { time: '08:00', queries: 45, latency: 78 }, { time: '10:00', queries: 62, latency: 95 },
  { time: '12:00', queries: 58, latency: 88 }, { time: '14:00', queries: 71, latency: 102 },
  { time: '16:00', queries: 65, latency: 91 }, { time: '18:00', queries: 42, latency: 67 },
  { time: '20:00', queries: 28, latency: 55 }, { time: '22:00', queries: 15, latency: 42 },
];

const compressionData = [
  { algorithm: 'Snappy', ratio: 2.1, speed: 450 }, { algorithm: 'LZ4', ratio: 2.8, speed: 520 },
  { algorithm: 'Zstd', ratio: 3.5, speed: 380 }, { algorithm: 'Gzip', ratio: 3.8, speed: 180 },
  { algorithm: 'Brotli', ratio: 4.2, speed: 120 }, { algorithm: 'Deflate', ratio: 3.2, speed: 250 },
];

const pipelineStages = [
  { name: 'Ingest', status: 'active', throughput: '2.4 GB/s', icon: '📥' },
  { name: 'Validate', status: 'active', throughput: '2.1 GB/s', icon: '✅' },
  { name: 'Transform', status: 'active', throughput: '1.8 GB/s', icon: '🔄' },
  { name: 'Compress', status: 'active', throughput: '1.5 GB/s', icon: '🗜️' },
  { name: 'Partition', status: 'active', throughput: '1.4 GB/s', icon: '📂' },
  { name: 'Index', status: 'active', throughput: '1.2 GB/s', icon: '🔍' },
  { name: 'Serve', status: 'active', throughput: '800 MB/s', icon: '🚀' },
];

const partitionStrategies = [
  { name: 'Date-based', column: 'event_date', granularity: 'daily', count: 365, efficiency: 94 },
  { name: 'Hash', column: 'user_id', granularity: '128 buckets', count: 128, efficiency: 88 },
  { name: 'Range', column: 'amount', granularity: '10 ranges', count: 10, efficiency: 76 },
  { name: 'List', column: 'region', granularity: '8 regions', count: 8, efficiency: 91 },
];

const indexMetrics = [
  { name: 'B-Tree (PK)', type: 'B-Tree', size: '12 GB', lookups: '2.3M/s', hitRate: 99.2 },
  { name: 'Bitmap (status)', type: 'Bitmap', size: '2.1 GB', lookups: '5.1M/s', hitRate: 97.8 },
  { name: 'Inverted (text)', type: 'Inverted', size: '28 GB', lookups: '890K/s', hitRate: 94.5 },
  { name: 'Bloom (dedup)', type: 'Bloom', size: '4.5 GB', lookups: '12M/s', hitRate: 99.9 },
];

const qualityIndicators = [
  { metric: 'Completeness', value: 98.5, threshold: 95, status: 'pass' },
  { metric: 'Uniqueness', value: 99.9, threshold: 99, status: 'pass' },
  { metric: 'Validity', value: 96.2, threshold: 95, status: 'pass' },
  { metric: 'Consistency', value: 94.1, threshold: 95, status: 'warn' },
  { metric: 'Timeliness', value: 91.8, threshold: 90, status: 'pass' },
  { metric: 'Accuracy', value: 97.3, threshold: 96, status: 'pass' },
];

const BigDataEnhanced: React.FC = () => {
  const [selectedStorage, setSelectedStorage] = useState<string | null>(null);
  const [queryFilter, setQueryFilter] = useState<'all' | 'peak' | 'offpeak'>('all');
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);

  const filteredQueries = useMemo(() => {
    if (queryFilter === 'peak') return queryTimelineData.filter(d => d.queries > 40);
    if (queryFilter === 'offpeak') return queryTimelineData.filter(d => d.queries <= 20);
    return queryTimelineData;
  }, [queryFilter]);

  const totalStorage = (storageData || []).reduce((s, d) => s + (d.value ?? 0), 0);

  // Action Buttons State
  const [, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Action Buttons Handlers
  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleExportCSV = () => {
    if (!datasetComparison || datasetComparison.length === 0) return;
    const headers = Object.keys(datasetComparison[0]);
    const csv = [headers.join(','), ...datasetComparison.map((item: any) => headers.map(h => `"${String(item[h] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'BigDataEnhanced_export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    if (!datasetComparison || datasetComparison.length === 0) return;
    const blob = new Blob([JSON.stringify(datasetComparison, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'BigDataEnhanced_export.json';
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
      <h1 className="text-2xl font-bold text-gray-200">BigData Platform — Enhanced Dashboard</h1>
      <ActionButtons
        onSearch={handleSearch}
        onExportCSV={handleExportCSV}
        onExportJSON={handleExportJSON}
        onRefresh={handleRefresh}
        onBulkDelete={handleBulkDelete}
        selectedCount={selectedIds.size}
        searchPlaceholder="Search datasets..."
      />

      {/* Row 1: Storage Donut + Dataset Table */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Storage Distribution</h2>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width="50%" height={200}>
              <PieChart>
                <Pie data={storageData} dataKey="value" innerRadius={50} outerRadius={80} onClick={(d: any) => setSelectedStorage(d.name)}>
                  {storageData.map((e, i) => <Cell key={i} fill={e.color} stroke={selectedStorage === e.name ? '#1f2937' : 'none'} strokeWidth={2} />)}
                </Pie>
                <Tooltip formatter={(v: number) => `${v} GB`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-1">
              {storageData.map(d => (
                <div key={d.name} className={`flex justify-between text-sm p-1 rounded cursor-pointer ${selectedStorage === d.name ? 'bg-blue-50' : ''}`} onClick={() => setSelectedStorage(d.name)}>
                  <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full" style={{ background: d.color }} />{d.name}</span>
                  <span className="font-medium">{d.value} GB ({((d.value ?? 0) / (totalStorage || 1) * 100).toFixed(1)}%)</span>
                </div>
              ))}
            </div>
          </div>
          {selectedStorage && <p className="text-sm text-blue-600 mt-2">Drill-down: {selectedStorage} — {storageData.find(d => d.name === selectedStorage)?.value} GB across {Math.floor(Math.random() * 500 + 100)} tables</p>}
        </div>

        <div className="bg-gray-900 rounded-xl shadow p-5 overflow-x-auto">
          <h2 className="text-lg font-semibold mb-3">Dataset Comparison</h2>
          <table className="w-full text-sm">
            <thead><tr className="border-b"><th className="text-left p-2">Dataset</th><th>Size</th><th>Rows</th><th>Format</th><th>Quality</th></tr></thead>
            <tbody>
              {datasetComparison.map((d, i) => (
                <tr key={d.name} className={`border-b cursor-pointer ${selectedDataset === i ? 'bg-blue-50' : 'hover:bg-gray-900'}`} onClick={() => setSelectedDataset(i)}>
                  <td className="p-2 font-medium">{d.name}</td><td>{d.size}</td><td>{d.rows}</td><td>{d.format}</td>
                  <td><span className={`px-2 py-0.5 rounded text-xs ${d.quality >= 97 ? 'bg-green-100 text-green-700' : d.quality >= 90 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>{d.quality}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Row 2: Query Timeline + Compression */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold">Query Timeline</h2>
            <div className="flex gap-1">
              {(['all', 'peak', 'offpeak'] as const).map(f => (
                <button key={f} onClick={() => setQueryFilter(f)} className={`px-3 py-1 text-xs rounded ${queryFilter === f ? 'bg-blue-600 text-white' : 'bg-gray-800'}`}>{f}</button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={filteredQueries}>
              <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" /><YAxis />
              <Tooltip /><Legend />
              <Line type="monotone" dataKey="queries" stroke="#3b82f6" strokeWidth={2} />
              <Line type="monotone" dataKey="latency" stroke="#ef4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Compression Analysis</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={compressionData}>
              <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="algorithm" /><YAxis />
              <Tooltip /><Legend />
              <Bar dataKey="ratio" fill="#10b981" name="Ratio (x)" />
              <Bar dataKey="speed" fill="#f59e0b" name="Speed (MB/s)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 3: Pipeline + Partition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Pipeline Flow</h2>
          <div className="flex items-center gap-1 overflow-x-auto">
            {pipelineStages.map((s, i) => (
              <React.Fragment key={s.name}>
                <div className="flex flex-col items-center min-w-[80px] p-2 bg-green-50 rounded-lg border border-green-200">
                  <span className="text-2xl">{s.icon}</span>
                  <span className="text-xs font-medium mt-1">{s.name}</span>
                  <span className="text-[10px] text-gray-400">{s.throughput}</span>
                </div>
                {i < pipelineStages.length - 1 && <span className="text-gray-400 mx-1">→</span>}
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Partition Strategies</h2>
          <div className="space-y-2">
            {partitionStrategies.map(p => (
              <div key={p.name} className="flex items-center justify-between p-2 bg-gray-900 rounded">
                <div><span className="font-medium text-sm">{p.name}</span><span className="text-xs text-gray-400 ml-2">{p.column} · {p.granularity}</span></div>
                <div className="flex items-center gap-3">
                  <span className="text-xs">{p.count} parts</span>
                  <div className="w-20 h-2 bg-gray-700 rounded-full"><div className="h-full bg-blue-500 rounded-full" style={{ width: `${p.efficiency}%` }} /></div>
                  <span className="text-xs font-medium">{p.efficiency}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 4: Index Metrics + Quality */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Index Metrics</h2>
          <div className="space-y-2">
            {indexMetrics.map(idx => (
              <div key={idx.name} className="flex items-center justify-between p-2 border-b">
                <div><span className="font-medium text-sm">{idx.name}</span><span className="text-xs text-gray-400 ml-2">{idx.type}</span></div>
                <div className="flex gap-4 text-xs"><span>{idx.size}</span><span>{idx.lookups}</span><span className="text-green-600 font-medium">{idx.hitRate}%</span></div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-3">Data Quality</h2>
          <div className="grid grid-cols-2 gap-3">
            {qualityIndicators.map(q => (
              <div key={q.metric} className={`p-3 rounded-lg border ${q.status === 'pass' ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'}`}>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">{q.metric}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${q.status === 'pass' ? 'bg-green-200 text-green-800' : 'bg-yellow-200 text-yellow-800'}`}>{q.status}</span>
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <div className="flex-1 h-2 bg-gray-700 rounded-full"><div className={`h-full rounded-full ${q.status === 'pass' ? 'bg-green-500' : 'bg-yellow-500'}`} style={{ width: `${q.value}%` }} /></div>
                  <span className="text-xs font-bold">{q.value}%</span>
                </div>
                <span className="text-[10px] text-gray-400">threshold: {q.threshold}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BigDataEnhanced;
