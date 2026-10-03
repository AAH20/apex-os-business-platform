import React, { useState, useRef, useEffect } from 'react';

interface Lead {
  id: number;
  name: string;
  company: string;
  email: string;
  status: string;
  value: number;
}

const LeadManagement: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([
    { id: 1, name: 'John Doe', company: 'Acme Corp', email: 'john@acme.com', status: 'New', value: 5000 },
    { id: 2, name: 'Jane Roe', company: 'Beta Inc', email: 'jane@beta.com', status: 'Contacted', value: 12000 },
    { id: 3, name: 'Sam Green', company: 'Gamma LLC', email: 'sam@gamma.com', status: 'Qualified', value: 8000 },
  ]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isModalOpen && firstFieldRef.current) {
      firstFieldRef.current.focus();
    }
  }, [isModalOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      setIsModalOpen(false);
    }
  };

  const openCreateModal = () => {
    setEditingLead(null);
    setIsModalOpen(true);
    setAnnouncement('Create lead dialog opened');
  };

  const openEditModal = (lead: Lead) => {
    setEditingLead(lead);
    setIsModalOpen(true);
    setAnnouncement(`Edit lead dialog opened for ${lead.name}`);
  };

  const handleDelete = (lead: Lead) => {
    setLeads(leads.filter(l => l.id !== lead.id));
    setAnnouncement(`Lead ${lead.name} deleted`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAnnouncement(editingLead ? 'Lead updated successfully' : 'Lead created successfully');
    setIsModalOpen(false);
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">Lead Management</h1>

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={openCreateModal}
        aria-label="Create new lead"
        className="bg-green-600 text-white px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
      >
        Create Lead
      </button>

      <div className="mt-4 overflow-x-auto">
        <table
          role="table"
          aria-label="Leads list"
          className="min-w-full border-collapse border border-gray-300"
        >
          <thead>
            <tr>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Name</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Company</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Email</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Status</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Value</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody>
            {leads.map(lead => (
              <tr key={lead.id}>
                <td className="border border-gray-300 px-4 py-2">{lead.name}</td>
                <td className="border border-gray-300 px-4 py-2">{lead.company}</td>
                <td className="border border-gray-300 px-4 py-2">{lead.email}</td>
                <td className="border border-gray-300 px-4 py-2">{lead.status}</td>
                <td className="border border-gray-300 px-4 py-2">${lead.value.toLocaleString()}</td>
                <td className="border border-gray-300 px-4 py-2">
                  <button
                    onClick={() => openEditModal(lead)}
                    aria-label={`Edit lead ${lead.name}`}
                    className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(lead)}
                    aria-label={`Delete lead ${lead.name}`}
                    className="bg-red-600 text-white px-3 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="lead-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          ref={modalRef}
        >
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 id="lead-modal-title" className="text-xl font-bold mb-4">
              {editingLead ? 'Edit Lead' : 'Create Lead'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="lead-name" className="block text-sm font-medium mb-1">
                  Name
                </label>
                <input
                  ref={firstFieldRef}
                  id="lead-name"
                  type="text"
                  aria-label="Lead name"
                  aria-required="true"
                  defaultValue={editingLead?.name || ''}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="lead-company" className="block text-sm font-medium mb-1">
                  Company
                </label>
                <input
                  id="lead-company"
                  type="text"
                  aria-label="Lead company"
                  aria-required="true"
                  defaultValue={editingLead?.company || ''}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="lead-email" className="block text-sm font-medium mb-1">
                  Email
                </label>
                <input
                  id="lead-email"
                  type="email"
                  aria-label="Lead email"
                  aria-required="true"
                  defaultValue={editingLead?.email || ''}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="lead-status" className="block text-sm font-medium mb-1">
                  Status
                </label>
                <select
                  id="lead-status"
                  aria-label="Lead status"
                  aria-required="true"
                  defaultValue={editingLead?.status || 'New'}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                >
                  <option value="New">New</option>
                  <option value="Contacted">Contacted</option>
                  <option value="Qualified">Qualified</option>
                  <option value="Lost">Lost</option>
                </select>
              </div>
              <div className="mb-4">
                <label htmlFor="lead-value" className="block text-sm font-medium mb-1">
                  Value
                </label>
                <input
                  id="lead-value"
                  type="number"
                  aria-label="Lead value"
                  aria-required="true"
                  defaultValue={editingLead?.value || 0}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  aria-label="Cancel"
                  className="bg-gray-300 text-gray-800 px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  aria-label={editingLead ? 'Save lead changes' : 'Create lead'}
                  className="bg-green-600 text-white px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                >
                  {editingLead ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadManagement;
