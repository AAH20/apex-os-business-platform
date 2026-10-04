import React, { useState, useRef, useEffect } from 'react';
import { Truck, Package, ShoppingCart, MapPin } from 'lucide-react';
import { api } from '../api/client';
import type { Supplier, PurchaseOrder, Shipment, LogisticsRoute, SupplierInput, PurchaseOrderInput, ShipmentInput, LogisticsRouteInput } from '../api/client';
import { EmptyState } from '../components/ui';
import { ActionButtons } from '../components/ActionButtons';

type Tab = 'suppliers' | 'purchase-orders' | 'shipments' | 'logistics-routes';

const PAGE_SIZE = 10;

const SupplyChainManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('suppliers');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [logisticsRoutes, setLogisticsRoutes] = useState<LogisticsRoute[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [announcement, setAnnouncement] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterValue, setFilterValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (isModalOpen && firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, [isModalOpen]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sup, po, sh, lr] = await Promise.all([
        api.getSupplyChainSuppliers(),
        api.getPurchaseOrders(),
        api.getShipments(),
        api.getLogisticsRoutes(),
      ]);
      setSuppliers(sup);
      setPurchaseOrders(po);
      setShipments(sh);
      setLogisticsRoutes(lr);
    } catch (err) {
      setAnnouncement('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const getCurrentData = () => {
    switch (activeTab) {
      case 'suppliers': return suppliers;
      case 'purchase-orders': return purchaseOrders;
      case 'shipments': return shipments;
      case 'logistics-routes': return logisticsRoutes;
    }
  };
  const totalPages = Math.ceil(getCurrentData().length / PAGE_SIZE);
  const pagedData = getCurrentData().slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const getFormFields = (): { key: string; label: string; type: string; required?: boolean; options?: { value: string; label: string }[] }[] => {
    switch (activeTab) {
      case 'suppliers':
        return [
          { key: 'name', label: 'Name', type: 'text', required: true },
          { key: 'contact_email', label: 'Contact Email', type: 'email' },
          { key: 'contact_phone', label: 'Contact Phone', type: 'text' },
          { key: 'address', label: 'Address', type: 'text' },
          { key: 'country', label: 'Country', type: 'text' },
          { key: 'status', label: 'Status', type: 'select', options: [{ value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }] },
        ];
      case 'purchase-orders':
        return [
          { key: 'supplier_id', label: 'Supplier ID', type: 'number', required: true },
          { key: 'product_name', label: 'Product Name', type: 'text', required: true },
          { key: 'quantity', label: 'Quantity', type: 'number', required: true },
          { key: 'unit_price', label: 'Unit Price', type: 'number', required: true },
          { key: 'status', label: 'Status', type: 'select', options: [{ value: 'pending', label: 'Pending' }, { value: 'approved', label: 'Approved' }, { value: 'delivered', label: 'Delivered' }, { value: 'cancelled', label: 'Cancelled' }] },
          { key: 'expected_delivery', label: 'Expected Delivery', type: 'date' },
        ];
      case 'shipments':
        return [
          { key: 'purchase_order_id', label: 'Purchase Order ID', type: 'number', required: true },
          { key: 'origin', label: 'Origin', type: 'text', required: true },
          { key: 'destination', label: 'Destination', type: 'text', required: true },
          { key: 'carrier', label: 'Carrier', type: 'text' },
          { key: 'tracking_number', label: 'Tracking Number', type: 'text' },
          { key: 'status', label: 'Status', type: 'select', options: [{ value: 'in_transit', label: 'In Transit' }, { value: 'delivered', label: 'Delivered' }, { value: 'delayed', label: 'Delayed' }] },
          { key: 'shipped_date', label: 'Shipped Date', type: 'date' },
          { key: 'estimated_arrival', label: 'Estimated Arrival', type: 'date' },
        ];
      case 'logistics-routes':
        return [
          { key: 'name', label: 'Route Name', type: 'text', required: true },
          { key: 'origin', label: 'Origin', type: 'text', required: true },
          { key: 'destination', label: 'Destination', type: 'text', required: true },
          { key: 'distance_km', label: 'Distance (km)', type: 'number' },
          { key: 'estimated_duration_hours', label: 'Est. Duration (hrs)', type: 'number' },
          { key: 'transport_mode', label: 'Transport Mode', type: 'select', options: [{ value: 'sea', label: 'Sea' }, { value: 'air', label: 'Air' }, { value: 'road', label: 'Road' }, { value: 'rail', label: 'Rail' }] },
          { key: 'cost', label: 'Cost', type: 'number' },
          { key: 'is_active', label: 'Active', type: 'checkbox' },
        ];
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        switch (activeTab) {
          case 'suppliers': await api.updateSupplyChainSupplier(editingId, formData); break;
          case 'purchase-orders': await api.updatePurchaseOrder(editingId, formData); break;
          case 'shipments': await api.updateShipment(editingId, formData); break;
          case 'logistics-routes': await api.updateLogisticsRoute(editingId, formData); break;
        }
        setAnnouncement(`${activeTab} item updated successfully`);
      } else {
        switch (activeTab) {
          case 'suppliers': await api.createSupplyChainSupplier(formData as unknown as SupplierInput); break;
          case 'purchase-orders': await api.createPurchaseOrder(formData as unknown as PurchaseOrderInput); break;
          case 'shipments': await api.createShipment(formData as unknown as ShipmentInput); break;
          case 'logistics-routes': await api.createLogisticsRoute(formData as unknown as LogisticsRouteInput); break;
        }
        setAnnouncement(`${activeTab} item created successfully`);
      }
      await loadData();
      closeModal();
    } catch (err) {
      setAnnouncement('Operation failed');
    }
  };

  const handleEdit = (item: any) => {
    setEditingId(item.id);
    setFormData({ ...item });
    setIsModalOpen(true);
  };

  const handleDelete = async (item: any) => {
    try {
      switch (activeTab) {
        case 'suppliers': await api.deleteSupplyChainSupplier(item.id); break;
        case 'purchase-orders': await api.deletePurchaseOrder(item.id); break;
        case 'shipments': await api.deleteShipment(item.id); break;
        case 'logistics-routes': await api.deleteLogisticsRoute(item.id); break;
      }
      setAnnouncement(`${activeTab} item deleted successfully`);
      await loadData();
    } catch (err) {
      setAnnouncement('Delete failed');
    }
  };

  const handleSearch = () => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const filterFn = (item: any) =>
        Object.values(item).some(v => String(v ?? '').toLowerCase().includes(q));
      switch (activeTab) {
        case 'suppliers': setSuppliers(suppliers.filter(filterFn)); break;
        case 'purchase-orders': setPurchaseOrders(purchaseOrders.filter(filterFn)); break;
        case 'shipments': setShipments(shipments.filter(filterFn)); break;
        case 'logistics-routes': setLogisticsRoutes(logisticsRoutes.filter(filterFn)); break;
      }
    } else {
      loadData();
    }
  };

  const handleExport = () => {
    const data = getCurrentData();
    const fields = getFormFields().filter(f => f.key !== 'is_active');
    const headers = fields.map(f => f.label);
    const rows = data.map((item: any) =>
      fields.map(f => `"${String(item[f.key] ?? '')}"`).join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeTab}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingId(null);
    setFormData({});
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) closeModal();
  };

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'suppliers', label: 'Suppliers', icon: <Package size={16} /> },
    { key: 'purchase-orders', label: 'Purchase Orders', icon: <ShoppingCart size={16} /> },
    { key: 'shipments', label: 'Shipments', icon: <Truck size={16} /> },
    { key: 'logistics-routes', label: 'Logistics Routes', icon: <MapPin size={16} /> },
  ];

  const renderTable = () => {
    const data = getCurrentData();
    const fields = getFormFields();
    const displayFields = fields.filter(f => f.key !== 'is_active').slice(0, 6);

    if (loading){
      return <div className="flex items-center justify-center py-12"><div className="flex items-center gap-2"><div className="animate-spin rounded-full border-2 border-gray-600 border-t-blue-500 h-8 w-8"></div><span className="text-gray-400">Loading...</span></div></div>;
    }

    if (pagedData.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 bg-gray-800 rounded-lg">
          <EmptyState message={`No ${activeTab} found`} action={
            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-cyan-600 text-white px-4 py-2 rounded hover:bg-cyan-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
            >
              Create First Item
            </button>
          } />
        </div>
      );
    }

    return (
      <div className="overflow-x-auto">
        <table role="table" aria-label={`${activeTab} list`} className="min-w-full border-collapse border border-gray-700">
          <thead>
            <tr>
              {displayFields.map(f => (
                <th key={f.key} scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-200 text-left text-sm font-medium">
                  {f.label}
                </th>
              ))}
              <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-200 text-left text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pagedData.map((item: any) => (
              <tr key={item.id} className="hover:bg-gray-800/50">
                {displayFields.map(f => (
                  <td key={f.key} className="border border-gray-700 px-4 py-2 text-gray-300 text-sm">
                    {f.type === 'checkbox' ? (item[f.key] ? 'Yes' : 'No') : String(item[f.key] ?? '')}
                  </td>
                ))}
                <td className="border border-gray-700 px-4 py-2">
                  <button
                    onClick={() => handleEdit(item)}
                    aria-label={`Edit ${activeTab} item`}
                    className="bg-yellow-600 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2 text-sm"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(item)}
                    aria-label={`Delete ${activeTab} item`}
                    className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };


  // ── Action Buttons Handlers ──────────────────────────────────────────────
  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleExportCSV = () => {
    const data = (getCurrentData() as any) || [];
    if (data.length === 0) return;
    const headers = Object.keys(data[0]);
    const csv = [headers.join(','), ...data.map((item: any) => headers.map(h => `"${String(item[h] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'supplychainmanagement_export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const data = (getCurrentData() as any) || [];
    if (data.length === 0) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'supplychainmanagement_export.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRefresh = () => {
    loadData();
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} selected item(s)?`)) return;
    setSelectedIds(new Set());
  };

  return (
    <div className="p-6 bg-gray-900 min-h-full" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4 text-gray-100">Supply Chain Management</h1>
        <ActionButtons
          onSearch={handleSearch}
          onExportCSV={handleExportCSV}
          onExportJSON={handleExportJSON}
          onRefresh={handleRefresh}
          onBulkDelete={handleBulkDelete}
          selectedCount={selectedIds.size}
          searchPlaceholder="Search suppliers..."
        />

      {announcement && (
        <div className="mb-4 rounded bg-red-500/20 px-4 py-2 text-sm text-red-400 flex items-center justify-between">
          <span>{announcement}</span>
          <button onClick={loadData} className="ml-4 rounded bg-red-500/30 px-3 py-1 text-xs font-medium hover:bg-red-500/50">Retry</button>
        </div>
      )}

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setSearchQuery(''); setPage(1); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 ${
              activeTab === tab.key
                ? 'bg-cyan-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <input
          type="text"
          placeholder={`Search ${activeTab}...`}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="border border-gray-700 rounded px-3 py-2 bg-gray-800 text-gray-200 placeholder-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
        />
        <button
          onClick={handleSearch}
          className="bg-cyan-600 text-white px-4 py-2 rounded hover:bg-cyan-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
        >
          Search
        </button>
        <button
          onClick={handleExport}
          className="bg-gray-700 text-gray-200 px-4 py-2 rounded hover:bg-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
        >
          Export
        </button>
        <button
          onClick={() => setIsModalOpen(true)}
          aria-label={`Add new ${activeTab} item`}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
        >
          + Add Item
        </button>
      </div>

      {/* Table */}
      {renderTable()}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded">Prev</button>
          <span className="px-3 py-1">Page {page} of {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded">Next</button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="sc-modal-title"
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-md border border-gray-700">
            <h2 id="sc-modal-title" className="text-xl font-bold mb-4 text-gray-100">
              {editingId ? 'Edit Item' : 'Add New Item'}
            </h2>
            <form onSubmit={handleSubmit}>
              {getFormFields().map((field, idx) => (
                <div key={field.key} className="mb-4">
                  <label htmlFor={`sc-${field.key}`} className="block text-sm font-medium mb-1 text-gray-300">
                    {field.label}
                  </label>
                  {field.type === 'select' ? (
                    <select
                      id={`sc-${field.key}`}
                      value={formData[field.key] || ''}
                      onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                      className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
                    >
                      <option value="">Select...</option>
                      {field.options?.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : field.type === 'checkbox' ? (
                    <input
                      id={`sc-${field.key}`}
                      type="checkbox"
                      checked={formData[field.key] || false}
                      onChange={(e) => setFormData({ ...formData, [field.key]: e.target.checked })}
                      className="rounded border-gray-600 bg-gray-700 text-cyan-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
                    />
                  ) : (
                    <input
                      ref={idx === 0 ? firstInputRef : undefined}
                      id={`sc-${field.key}`}
                      type={field.type}
                      value={formData[field.key] || ''}
                      onChange={(e) => setFormData({ ...formData, [field.key]: field.type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value })}
                      required={field.required}
                      className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-700 text-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
                    />
                  )}
                </div>
              ))}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="bg-gray-600 text-gray-200 px-4 py-2 rounded hover:bg-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-cyan-600 text-white px-4 py-2 rounded hover:bg-cyan-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
                >
                  {editingId ? 'Save' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SupplyChainManagement;
