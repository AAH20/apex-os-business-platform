import React, { useState, useEffect, useCallback, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { useSort } from '../hooks/useSort';
import { useKeyboardShortcuts, exportToCSV } from '../hooks/useKeyboardShortcuts';
import { api } from '../api/client';
import type { IoTDevice, IoTSensor, IoTTelemetry, IoTAlert, IoTDeviceGroup } from '../api/client';

const PAGE_SIZE = 10;

// ── Tab definitions ──────────────────────────────────────────────────────────

type TabKey = 'devices' | 'sensors' | 'telemetry' | 'alerts' | 'groups';

const tabs: { key: TabKey; label: string }[] = [
  { key: 'devices', label: 'Devices' },
  { key: 'sensors', label: 'Sensors' },
  { key: 'telemetry', label: 'Telemetry' },
  { key: 'alerts', label: 'Alerts' },
  { key: 'groups', label: 'Groups' },
];

// ── Empty form templates ─────────────────────────────────────────────────────

const emptyDevice = { name: '', type: 'temperature', status: 'active', location: '', group_id: undefined as number | undefined };
const emptySensor = { device_id: 0, name: '', unit: '', min_val: 0, max_val: 100, calibration_date: '' };
const emptyTelemetry = { sensor_id: 0, value: 0, quality: 'good' };
const emptyAlert = { device_id: 0, rule: '', severity: 'warning', message: '', is_active: true };
const emptyGroup = { name: '', description: '', color: '#06b6d4' };

// ── Main Component ───────────────────────────────────────────────────────────

const IoTManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('devices');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [filterValue, setFilterValue] = useState('');
  const [page, setPage] = useState(1);

  // Data states
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [sensors, setSensors] = useState<IoTSensor[]>([]);
  const [telemetry, setTelemetry] = useState<IoTTelemetry[]>([]);
  const [alerts, setAlerts] = useState<IoTAlert[]>([]);
  const [groups, setGroups] = useState<IoTDeviceGroup[]>([]);

  // Form states
  const [deviceForm, setDeviceForm] = useState(emptyDevice);
  const [sensorForm, setSensorForm] = useState(emptySensor);
  const [telemetryForm, setTelemetryForm] = useState(emptyTelemetry);
  const [alertForm, setAlertForm] = useState(emptyAlert);
  const [groupForm, setGroupForm] = useState(emptyGroup);

  const searchRef = useRef<HTMLInputElement>(null);
  const [showDashboard, setShowDashboard] = useState(true);

  // ── Fetch helpers ─────────────────────────────────────────────────────────

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getIoTDevices();
      setDevices(data);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch devices');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSensors = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getIoTSensors();
      setSensors(data);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch sensors');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTelemetry = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getIoTTelemetry();
      setTelemetry(data);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch telemetry');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getIoTAlerts();
      setAlerts(data);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchGroups = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getIoTGroups();
      setGroups(data);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch groups');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAll = useCallback(() => {
    fetchDevices();
    fetchSensors();
    fetchTelemetry();
    fetchAlerts();
    fetchGroups();
  }, [fetchDevices, fetchSensors, fetchTelemetry, fetchAlerts, fetchGroups]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── CRUD handlers ─────────────────────────────────────────────────────────

  const handleDeviceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await api.updateIoTDevice(editingId, deviceForm);
      } else {
        await api.createIoTDevice(deviceForm);
      }
      setShowForm(false);
      setEditingId(null);
      setDeviceForm(emptyDevice);
      fetchDevices();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleSensorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await api.updateIoTSensor(editingId, sensorForm);
      } else {
        await api.createIoTSensor(sensorForm);
      }
      setShowForm(false);
      setEditingId(null);
      setSensorForm(emptySensor);
      fetchSensors();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleTelemetrySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await api.updateIoTTelemetry(editingId, telemetryForm);
      } else {
        await api.createIoTTelemetry(telemetryForm);
      }
      setShowForm(false);
      setEditingId(null);
      setTelemetryForm(emptyTelemetry);
      fetchTelemetry();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleAlertSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await api.updateIoTAlert(editingId, alertForm);
      } else {
        await api.createIoTAlert(alertForm);
      }
      setShowForm(false);
      setEditingId(null);
      setAlertForm(emptyAlert);
      fetchAlerts();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleGroupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await api.updateIoTGroup(editingId, groupForm);
      } else {
        await api.createIoTGroup(groupForm);
      }
      setShowForm(false);
      setEditingId(null);
      setGroupForm(emptyGroup);
      fetchGroups();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(true);
    try {
      switch (activeTab) {
        case 'devices': await api.deleteIoTDevice(id); fetchDevices(); break;
        case 'sensors': await api.deleteIoTSensor(id); fetchSensors(); break;
        case 'telemetry': await api.deleteIoTTelemetry(id); fetchTelemetry(); break;
        case 'alerts': await api.deleteIoTAlert(id); fetchAlerts(); break;
        case 'groups': await api.deleteIoTGroup(id); fetchGroups(); break;
      }
      setShowDeleteConfirm(null);
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  // ── Edit handlers ─────────────────────────────────────────────────────────

  const handleEdit = (id: number) => {
    switch (activeTab) {
      case 'devices': {
        const d = devices.find(x => x.id === id);
        if (d) { setDeviceForm({ name: d.name, type: d.type, status: d.status, location: d.location, group_id: d.group_id }); setEditingId(id); setShowForm(true); }
        break;
      }
      case 'sensors': {
        const s = sensors.find(x => x.id === id);
        if (s) { setSensorForm({ device_id: s.device_id, name: s.name, unit: s.unit, min_val: s.min_val, max_val: s.max_val, calibration_date: s.calibration_date || '' }); setEditingId(id); setShowForm(true); }
        break;
      }
      case 'telemetry': {
        const t = telemetry.find(x => x.id === id);
        if (t) { setTelemetryForm({ sensor_id: t.sensor_id, value: t.value, quality: t.quality }); setEditingId(id); setShowForm(true); }
        break;
      }
      case 'alerts': {
        const a = alerts.find(x => x.id === id);
        if (a) { setAlertForm({ device_id: a.device_id, rule: a.rule, severity: a.severity, message: a.message, is_active: a.is_active }); setEditingId(id); setShowForm(true); }
        break;
      }
      case 'groups': {
        const g = groups.find(x => x.id === id);
        if (g) { setGroupForm({ name: g.name, description: g.description, color: g.color }); setEditingId(id); setShowForm(true); }
        break;
      }
    }
  };

  // ── Sorting ───────────────────────────────────────────────────────────────

  const { sortedData: sortedDevices, requestSort: sortDevices, getSortIndicator: devSort } = useSort(devices);
  const { sortedData: sortedSensors, requestSort: sortSensors, getSortIndicator: senSort } = useSort(sensors);
  const { sortedData: sortedTelemetry, requestSort: sortTelemetry, getSortIndicator: telSort } = useSort(telemetry);
  const { sortedData: sortedAlerts, requestSort: sortAlerts, getSortIndicator: alertSort } = useSort(alerts);
  const { sortedData: sortedGroups, requestSort: sortGroups, getSortIndicator: grpSort } = useSort(groups);

  // ── Filter options ────────────────────────────────────────────────────────

  const getFilterOptions = (): { value: string; label: string }[] => {
    switch (activeTab) {
      case 'devices':
        return [{ value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }, { value: 'maintenance', label: 'Maintenance' }];
      case 'sensors':
        return [];
      case 'telemetry':
        return [{ value: 'good', label: 'Good' }, { value: 'fair', label: 'Fair' }, { value: 'poor', label: 'Poor' }];
      case 'alerts':
        return [{ value: 'info', label: 'Info' }, { value: 'warning', label: 'Warning' }, { value: 'critical', label: 'Critical' }];
      case 'groups':
        return [];
    }
  };



  // ── Keyboard shortcuts ────────────────────────────────────────────────────

  useKeyboardShortcuts({
    onNew: () => { setShowForm(true); setEditingId(null); },
    onSearch: () => searchRef.current?.focus(),
    searchRef,
    onExport: () => {
      const data = activeTab === 'devices' ? devices : activeTab === 'sensors' ? sensors : activeTab === 'telemetry' ? telemetry : activeTab === 'alerts' ? alerts : groups;
      exportToCSV(data as unknown as Record<string, unknown>[], `${activeTab}_export.csv`);
    },
    onDelete: () => {
      const data = activeTab === 'devices' ? devices : activeTab === 'sensors' ? sensors : activeTab === 'telemetry' ? telemetry : activeTab === 'alerts' ? alerts : groups;
      if (data.length > 0) setShowDeleteConfirm(data[0].id);
    },
    onClose: () => setShowForm(false),
  });

  // ── Render helpers ────────────────────────────────────────────────────────

  const renderForm = () => {
    if (!showForm) return null;
    const cancel = () => { setShowForm(false); setEditingId(null); };

    if (activeTab === 'devices') {
      return (
        <form onSubmit={handleDeviceSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Device' : 'Create New Device'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={deviceForm.name} onChange={e => setDeviceForm({ ...deviceForm, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Type</label>
              <select value={deviceForm.type} onChange={e => setDeviceForm({ ...deviceForm, type: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="temperature">Temperature</option>
                <option value="humidity">Humidity</option>
                <option value="pressure">Pressure</option>
                <option value="flow">Flow</option>
                <option value="vibration">Vibration</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Status</label>
              <select value={deviceForm.status} onChange={e => setDeviceForm({ ...deviceForm, status: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="maintenance">Maintenance</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Location</label>
              <input value={deviceForm.location} onChange={e => setDeviceForm({ ...deviceForm, location: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Group ID</label>
              <input type="number" value={deviceForm.group_id ?? ''} onChange={e => setDeviceForm({ ...deviceForm, group_id: e.target.value ? Number(e.target.value) : undefined })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">{saving ? 'Saving...' : editingId ? 'Update' : 'Create'}</button>
            <button type="button" onClick={cancel} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
          </div>
        </form>
      );
    }

    if (activeTab === 'sensors') {
      return (
        <form onSubmit={handleSensorSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Sensor' : 'Create New Sensor'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Device ID *</label>
              <input type="number" required value={sensorForm.device_id || ''} onChange={e => setSensorForm({ ...sensorForm, device_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={sensorForm.name} onChange={e => setSensorForm({ ...sensorForm, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Unit</label>
              <input value={sensorForm.unit} onChange={e => setSensorForm({ ...sensorForm, unit: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Min Value</label>
              <input type="number" step="0.1" value={sensorForm.min_val} onChange={e => setSensorForm({ ...sensorForm, min_val: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Max Value</label>
              <input type="number" step="0.1" value={sensorForm.max_val} onChange={e => setSensorForm({ ...sensorForm, max_val: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Calibration Date</label>
              <input type="date" value={sensorForm.calibration_date} onChange={e => setSensorForm({ ...sensorForm, calibration_date: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">{saving ? 'Saving...' : editingId ? 'Update' : 'Create'}</button>
            <button type="button" onClick={cancel} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
          </div>
        </form>
      );
    }

    if (activeTab === 'telemetry') {
      return (
        <form onSubmit={handleTelemetrySubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Telemetry' : 'Create New Telemetry'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Sensor ID *</label>
              <input type="number" required value={telemetryForm.sensor_id || ''} onChange={e => setTelemetryForm({ ...telemetryForm, sensor_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Value *</label>
              <input type="number" step="0.01" required value={telemetryForm.value} onChange={e => setTelemetryForm({ ...telemetryForm, value: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Quality</label>
              <select value={telemetryForm.quality} onChange={e => setTelemetryForm({ ...telemetryForm, quality: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="good">Good</option>
                <option value="fair">Fair</option>
                <option value="poor">Poor</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">{saving ? 'Saving...' : editingId ? 'Update' : 'Create'}</button>
            <button type="button" onClick={cancel} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
          </div>
        </form>
      );
    }

    if (activeTab === 'alerts') {
      return (
        <form onSubmit={handleAlertSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Alert' : 'Create New Alert'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Device ID *</label>
              <input type="number" required value={alertForm.device_id || ''} onChange={e => setAlertForm({ ...alertForm, device_id: Number(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Severity</label>
              <select value={alertForm.severity} onChange={e => setAlertForm({ ...alertForm, severity: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100">
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Rule *</label>
              <input required value={alertForm.rule} onChange={e => setAlertForm({ ...alertForm, rule: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Message</label>
              <input value={alertForm.message} onChange={e => setAlertForm({ ...alertForm, message: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div className="md:col-span-2">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input type="checkbox" checked={alertForm.is_active} onChange={e => setAlertForm({ ...alertForm, is_active: e.target.checked })} className="rounded" />
                Active
              </label>
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">{saving ? 'Saving...' : editingId ? 'Update' : 'Create'}</button>
            <button type="button" onClick={cancel} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
          </div>
        </form>
      );
    }

    if (activeTab === 'groups') {
      return (
        <form onSubmit={handleGroupSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6 shadow">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Group' : 'Create New Group'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Name *</label>
              <input required value={groupForm.name} onChange={e => setGroupForm({ ...groupForm, name: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-300">Color</label>
              <input type="color" value={groupForm.color} onChange={e => setGroupForm({ ...groupForm, color: e.target.value })} className="w-full h-10 bg-gray-700 border border-gray-600 rounded px-1 py-1" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-gray-300">Description</label>
              <input value={groupForm.description} onChange={e => setGroupForm({ ...groupForm, description: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100" />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button type="submit" disabled={saving} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">{saving ? 'Saving...' : editingId ? 'Update' : 'Create'}</button>
            <button type="button" onClick={cancel} disabled={saving} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
          </div>
        </form>
      );
    }

    return null;
  };

  const renderTable = () => {
    if (loading) {
      return <div className="px-4 py-8 text-center text-gray-500">Loading...</div>;
    }

    if (activeTab === 'devices') {
      const filtered = sortedDevices.filter(d => {
        const matchesSearch = !search || d.name.toLowerCase().includes(search.toLowerCase()) || d.type.toLowerCase().includes(search.toLowerCase()) || d.location.toLowerCase().includes(search.toLowerCase());
        const matchesFilter = !filterValue || d.status === filterValue;
        return matchesSearch && matchesFilter;
      });
      const start = (page - 1) * PAGE_SIZE;
      const paged = filtered.slice(start, start + PAGE_SIZE);
      if (paged.length === 0) return <div className="px-4 py-8 text-center text-gray-500">No devices found</div>;
      return (
        <table className="w-full">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortDevices('id')}>ID{devSort('id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortDevices('name')}>Name{devSort('name')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Type</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Location</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Last Seen</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(d => (
              <tr key={d.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-4 py-3">{d.id}</td>
                <td className="px-4 py-3 font-medium">{d.name}</td>
                <td className="px-4 py-3 text-gray-400">{d.type}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${d.status === 'active' ? 'bg-green-900/50 text-green-300' : d.status === 'maintenance' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-gray-700 text-gray-400'}`}>{d.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-400">{d.location}</td>
                <td className="px-4 py-3 text-gray-400 text-sm">{d.last_seen}</td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(d.id)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(d.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === 'sensors') {
      const filtered = sortedSensors.filter(s => {
        const matchesSearch = !search || s.name.toLowerCase().includes(search.toLowerCase()) || s.unit.toLowerCase().includes(search.toLowerCase());
        return matchesSearch;
      });
      const start = (page - 1) * PAGE_SIZE;
      const paged = filtered.slice(start, start + PAGE_SIZE);
      if (paged.length === 0) return <div className="px-4 py-8 text-center text-gray-500">No sensors found</div>;
      return (
        <table className="w-full">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortSensors('id')}>ID{senSort('id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortSensors('name')}>Name{senSort('name')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Device ID</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Unit</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Range</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Calibration</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(s => (
              <tr key={s.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-4 py-3">{s.id}</td>
                <td className="px-4 py-3 font-medium">{s.name}</td>
                <td className="px-4 py-3 text-gray-400">{s.device_id}</td>
                <td className="px-4 py-3 text-gray-400">{s.unit}</td>
                <td className="px-4 py-3 text-gray-400">{s.min_val} – {s.max_val}</td>
                <td className="px-4 py-3 text-gray-400 text-sm">{s.calibration_date || '—'}</td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(s.id)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(s.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === 'telemetry') {
      const filtered = sortedTelemetry.filter(t => {
        const matchesSearch = !search || String(t.value).includes(search) || t.quality.toLowerCase().includes(search.toLowerCase());
        const matchesFilter = !filterValue || t.quality === filterValue;
        return matchesSearch && matchesFilter;
      });
      const start = (page - 1) * PAGE_SIZE;
      const paged = filtered.slice(start, start + PAGE_SIZE);
      if (paged.length === 0) return <div className="px-4 py-8 text-center text-gray-500">No telemetry data found</div>;
      return (
        <table className="w-full">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortTelemetry('id')}>ID{telSort('id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Sensor ID</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortTelemetry('value')}>Value{telSort('value')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Quality</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Timestamp</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(t => (
              <tr key={t.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-4 py-3">{t.id}</td>
                <td className="px-4 py-3 text-gray-400">{t.sensor_id}</td>
                <td className="px-4 py-3 font-medium">{t.value}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${t.quality === 'good' ? 'bg-green-900/50 text-green-300' : t.quality === 'fair' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-red-900/50 text-red-300'}`}>{t.quality}</span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-sm">{t.timestamp}</td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(t.id)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(t.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === 'alerts') {
      const filtered = sortedAlerts.filter(a => {
        const matchesSearch = !search || a.rule.toLowerCase().includes(search.toLowerCase()) || a.message.toLowerCase().includes(search.toLowerCase()) || a.severity.toLowerCase().includes(search.toLowerCase());
        const matchesFilter = !filterValue || a.severity === filterValue;
        return matchesSearch && matchesFilter;
      });
      const start = (page - 1) * PAGE_SIZE;
      const paged = filtered.slice(start, start + PAGE_SIZE);
      if (paged.length === 0) return <div className="px-4 py-8 text-center text-gray-500">No alerts found</div>;
      return (
        <table className="w-full">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortAlerts('id')}>ID{alertSort('id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Device ID</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Rule</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortAlerts('severity')}>Severity{alertSort('severity')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Message</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Active</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(a => (
              <tr key={a.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-4 py-3">{a.id}</td>
                <td className="px-4 py-3 text-gray-400">{a.device_id}</td>
                <td className="px-4 py-3 font-medium">{a.rule}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${a.severity === 'critical' ? 'bg-red-900/50 text-red-300' : a.severity === 'warning' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-blue-900/50 text-blue-300'}`}>{a.severity}</span>
                </td>
                <td className="px-4 py-3 text-gray-400">{a.message}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${a.is_active ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-400'}`}>{a.is_active ? 'Yes' : 'No'}</span>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(a.id)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(a.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === 'groups') {
      const filtered = sortedGroups.filter(g => {
        const matchesSearch = !search || g.name.toLowerCase().includes(search.toLowerCase()) || g.description.toLowerCase().includes(search.toLowerCase());
        return matchesSearch;
      });
      const start = (page - 1) * PAGE_SIZE;
      const paged = filtered.slice(start, start + PAGE_SIZE);
      if (paged.length === 0) return <div className="px-4 py-8 text-center text-gray-500">No groups found</div>;
      return (
        <table className="w-full">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortGroups('id')}>ID{grpSort('id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300 cursor-pointer select-none" onClick={() => sortGroups('name')}>Name{grpSort('name')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Description</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Color</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(g => (
              <tr key={g.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-4 py-3">{g.id}</td>
                <td className="px-4 py-3 font-medium">{g.name}</td>
                <td className="px-4 py-3 text-gray-400">{g.description}</td>
                <td className="px-4 py-3">
                  <span className="inline-block w-4 h-4 rounded" style={{ background: g.color }} />
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => handleEdit(g.id)} className="text-blue-400 hover:text-blue-300 mr-3 text-sm">Edit</button>
                  <button onClick={() => setShowDeleteConfirm(g.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    return null;
  };

  const getCurrentData = () => {
    switch (activeTab) {
      case 'devices': return devices;
      case 'sensors': return sensors;
      case 'telemetry': return telemetry;
      case 'alerts': return alerts;
      case 'groups': return groups;
    }
  };

  const getCurrentTotal = () => {
    const data = getCurrentData();
    if (!search) return data.length;
    // Approximate filtered count for pagination
    return data.length;
  };

  const totalPages = Math.ceil(getCurrentTotal() / PAGE_SIZE);

  return (
    <div className="p-6 max-w-6xl mx-auto bg-gray-900 text-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">IoT Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100 font-bold ml-4">&times;</button>
        </div>
      )}

      {/* Dashboard Toggle */}
      <button
        onClick={() => setShowDashboard(!showDashboard)}
        className="mb-4 text-sm text-cyan-400 hover:text-cyan-300"
      >
        {showDashboard ? '▼ Hide Dashboard' : '▶ Show Dashboard'}
      </button>

      {/* Dashboard */}
      {showDashboard && (
        <div className="mb-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 shadow">
              <p className="text-sm text-gray-400">Active Devices</p>
              <p className="text-2xl font-bold text-cyan-400">{devices.filter(d => d.status === 'active').length}</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 shadow">
              <p className="text-sm text-gray-400">Online Sensors</p>
              <p className="text-2xl font-bold text-green-400">{sensors.length}</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 shadow">
              <p className="text-sm text-gray-400">Active Alerts</p>
              <p className="text-2xl font-bold text-red-400">{alerts.filter(a => a.is_active).length}</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 shadow">
              <p className="text-sm text-gray-400">Device Groups</p>
              <p className="text-2xl font-bold text-purple-400">{groups.length}</p>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Devices by Status */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 shadow">
              <h3 className="text-sm font-medium text-gray-300 mb-4">Devices by Status</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={[
                  { name: 'Active', value: devices.filter(d => d.status === 'active').length },
                  { name: 'Inactive', value: devices.filter(d => d.status === 'inactive').length },
                  { name: 'Maintenance', value: devices.filter(d => d.status === 'maintenance').length },
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.375rem' }} />
                  <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Alerts by Severity */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 shadow">
              <h3 className="text-sm font-medium text-gray-300 mb-4">Alerts by Severity</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Info', value: alerts.filter(a => a.severity === 'info').length, color: '#3b82f6' },
                      { name: 'Warning', value: alerts.filter(a => a.severity === 'warning').length, color: '#eab308' },
                      { name: 'Critical', value: alerts.filter(a => a.severity === 'critical').length, color: '#ef4444' },
                    ]}
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {[
                      { color: '#3b82f6' },
                      { color: '#eab308' },
                      { color: '#ef4444' },
                    ].map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.375rem' }} />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-4">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setPage(1); setSearch(''); setFilterValue(''); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.key ? 'bg-cyan-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search + Filter + New */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder={`Search ${activeTab}...`}
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex-1 min-w-[200px] text-gray-100 placeholder-gray-500"
          ref={searchRef}
        />
        {getFilterOptions().length > 0 && (
          <select
            value={filterValue}
            onChange={e => { setFilterValue(e.target.value); setPage(1); }}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-100"
          >
            <option value="">All {activeTab}</option>
            {getFilterOptions().map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        )}
        <button
          onClick={() => { setShowForm(true); setEditingId(null); }}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New {activeTab.slice(0, -1).replace(/^\w/, c => c.toUpperCase())}
        </button>
      </div>

      {/* Form */}
      {renderForm()}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Confirm Delete</h3>
            <p className="text-gray-400 mb-4">Are you sure you want to delete this item? This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)} disabled={deleting} className="bg-gray-600 px-4 py-2 rounded hover:bg-gray-500 disabled:opacity-50">Cancel</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} disabled={deleting} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50">
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden shadow">
        {renderTable()}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-gray-400">Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, getCurrentTotal())} of {getCurrentTotal()}</p>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border border-gray-600 rounded disabled:opacity-50 hover:bg-gray-700 text-gray-300">Previous</button>
            <span className="px-3 py-1 text-gray-400">{page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 border border-gray-600 rounded disabled:opacity-50 hover:bg-gray-700 text-gray-300">Next</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default IoTManagement;
