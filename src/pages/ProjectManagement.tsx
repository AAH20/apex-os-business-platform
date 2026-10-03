import React, { useState, useRef, useEffect } from 'react';
import { Briefcase } from 'lucide-react';

interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  startDate: string;
}

const ProjectManagement: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '', status: '', startDate: '' });
  const [announcement, setAnnouncement] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isModalOpen && firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, [isModalOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingProject) {
      setProjects(projects.map(p => p.id === editingProject.id ? { ...p, ...formData } : p));
      setAnnouncement(`Project "${formData.name}" updated successfully`);
    } else {
      const newProject: Project = { id: Date.now(), ...formData };
      setProjects([...projects, newProject]);
      setAnnouncement(`Project "${formData.name}" added successfully`);
    }
    closeModal();
  };

  const handleEdit = (project: Project) => {
    setEditingProject(project);
    setFormData({ name: project.name, description: project.description, status: project.status, startDate: project.startDate });
    setIsModalOpen(true);
  };

  const handleDelete = (project: Project) => {
    setProjects(projects.filter(p => p.id !== project.id));
    setAnnouncement(`Project "${project.name}" removed`);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingProject(null);
    setFormData({ name: '', description: '', status: '', startDate: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4 text-gray-100">Project Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={() => setIsModalOpen(true)}
        aria-label="Add new project"
        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2 mb-4"
      >
        + Add Project
      </button>

      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-800 rounded-lg">
          <Briefcase className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-gray-100 text-lg mb-4">No projects found. Create your first project!</p>
          <button
            onClick={() => setIsModalOpen(true)}
            aria-label="Create project"
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
          >
            Create Project
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Projects list" className="min-w-full border-collapse border border-gray-700">
            <thead>
              <tr>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Name</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Description</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Status</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Start Date</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Actions</th>
              </tr>
            </thead>
            <tbody>
              {projects.map(project => (
                <tr key={project.id}>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{project.name}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{project.description}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{project.status}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{project.startDate}</td>
                  <td className="border border-gray-700 px-4 py-2">
                    <button
                      onClick={() => handleEdit(project)}
                      aria-label={`Edit project ${project.name}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(project)}
                      aria-label={`Delete project ${project.name}`}
                      className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
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
          aria-labelledby="project-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-gray-800 p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="project-modal-title" className="text-xl font-bold mb-4 text-gray-100">
              {editingProject ? 'Edit Project' : 'Add New Project'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="project-name" className="block text-sm font-medium mb-1 text-gray-100">Name</label>
                <input
                  ref={firstInputRef}
                  id="project-name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  aria-label="Project name"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="project-description" className="block text-sm font-medium mb-1 text-gray-100">Description</label>
                <input
                  id="project-description"
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  aria-label="Project description"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="project-status" className="block text-sm font-medium mb-1 text-gray-100">Status</label>
                <input
                  id="project-status"
                  type="text"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  aria-label="Project status"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="project-start-date" className="block text-sm font-medium mb-1 text-gray-100">Start Date</label>
                <input
                  id="project-start-date"
                  type="date"
                  value={formData.startDate}
                  onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                  aria-label="Project start date"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  aria-label="Cancel"
                  className="bg-gray-600 text-gray-100 px-4 py-2 rounded hover:bg-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  aria-label={editingProject ? 'Save project changes' : 'Add project'}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                >
                  {editingProject ? 'Save' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectManagement;
