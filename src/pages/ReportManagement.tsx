import React, { useState, useRef, useEffect } from 'react';
import { FileText } from 'lucide-react';

interface Report {
  id: number;
  title: string;
  type: string;
  createdBy: string;
  createdAt: string;
  status: string;
}

const ReportManagement: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([
    { id: 1, title: 'Q3 Sales Report', type: 'Sales', createdBy: 'Alice', createdAt: '2026-09-15', status: 'Completed' },
    { id: 2, title: 'Marketing Analysis', type: 'Marketing', createdBy: 'Bob', createdAt: '2026-09-20', status: 'In Progress' },
    { id: 3, title: 'Financial Summary', type: 'Finance', createdBy: 'Carol', createdAt: '2026-09-25', status: 'Draft' },
  ]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingReport, setEditingReport] = useState<Report | null>(null);
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
    setEditingReport(null);
    setIsModalOpen(true);
    setAnnouncement('Create report dialog opened');
  };

  const openEditModal = (report: Report) => {
    setEditingReport(report);
    setIsModalOpen(true);
    setAnnouncement(`Edit report dialog opened for ${report.title}`);
  };

  const handleDelete = (report: Report) => {
    setReports(reports.filter(r => r.id !== report.id));
    setAnnouncement(`Report ${report.title} deleted`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAnnouncement(editingReport ? 'Report updated successfully' : 'Report created successfully');
    setIsModalOpen(false);
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">Report Management</h1>

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={openCreateModal}
        aria-label="Create new report"
        className="bg-purple-600 text-white px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
      >
        Create Report
      </button>

      {reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-900 text-gray-100 rounded-lg mt-4">
          <FileText className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-lg mb-4">No reports found. Create your first report!</p>
          <button
            onClick={openCreateModal}
            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
          >
            Create Report
          </button>
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table
            role="table"
            aria-label="Reports list"
            className="min-w-full border-collapse border border-gray-300"
          >
          <thead>
            <tr>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Title</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Type</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Created By</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Created At</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Status</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody>
            {reports.map(report => (
              <tr key={report.id}>
                <td className="border border-gray-300 px-4 py-2">{report.title}</td>
                <td className="border border-gray-300 px-4 py-2">{report.type}</td>
                <td className="border border-gray-300 px-4 py-2">{report.createdBy}</td>
                <td className="border border-gray-300 px-4 py-2">{report.createdAt}</td>
                <td className="border border-gray-300 px-4 py-2">{report.status}</td>
                <td className="border border-gray-300 px-4 py-2">
                  <button
                    onClick={() => openEditModal(report)}
                    aria-label={`Edit report ${report.title}`}
                    className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(report)}
                    aria-label={`Delete report ${report.title}`}
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
      )}

      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="report-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          ref={modalRef}
        >
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 id="report-modal-title" className="text-xl font-bold mb-4">
              {editingReport ? 'Edit Report' : 'Create Report'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="report-title" className="block text-sm font-medium mb-1">
                  Title
                </label>
                <input
                  ref={firstFieldRef}
                  id="report-title"
                  type="text"
                  aria-label="Report title"
                  aria-required="true"
                  defaultValue={editingReport?.title || ''}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="report-type" className="block text-sm font-medium mb-1">
                  Type
                </label>
                <select
                  id="report-type"
                  aria-label="Report type"
                  aria-required="true"
                  defaultValue={editingReport?.type || 'Sales'}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  <option value="Sales">Sales</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Finance">Finance</option>
                  <option value="Operations">Operations</option>
                </select>
              </div>
              <div className="mb-4">
                <label htmlFor="report-status" className="block text-sm font-medium mb-1">
                  Status
                </label>
                <select
                  id="report-status"
                  aria-label="Report status"
                  aria-required="true"
                  defaultValue={editingReport?.status || 'Draft'}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  <option value="Draft">Draft</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Completed">Completed</option>
                </select>
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
                  aria-label={editingReport ? 'Save report changes' : 'Create report'}
                  className="bg-purple-600 text-white px-4 py-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
                >
                  {editingReport ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportManagement;
