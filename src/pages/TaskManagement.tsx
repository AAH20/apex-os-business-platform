import React, { useState, useRef, useEffect } from 'react';
import { CheckSquare } from 'lucide-react';

interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed';
  priority: 'low' | 'medium' | 'high';
}

const TaskManagement: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [formData, setFormData] = useState({ title: '', description: '', status: 'pending' as Task['status'], priority: 'medium' as Task['priority'] });
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
    if (editingTask) {
      setTasks(tasks.map(t => t.id === editingTask.id ? { ...t, ...formData } : t));
      setAnnouncement(`Task "${formData.title}" updated successfully`);
    } else {
      const newTask: Task = { id: Date.now(), ...formData };
      setTasks([...tasks, newTask]);
      setAnnouncement(`Task "${formData.title}" created successfully`);
    }
    closeModal();
  };

  const handleEdit = (task: Task) => {
    setEditingTask(task);
    setFormData({ title: task.title, description: task.description, status: task.status, priority: task.priority });
    setIsModalOpen(true);
  };

  const handleDelete = (task: Task) => {
    setTasks(tasks.filter(t => t.id !== task.id));
    setAnnouncement(`Task "${task.title}" deleted successfully`);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingTask(null);
    setFormData({ title: '', description: '', status: 'pending', priority: 'medium' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  };

  return (
    <div className="p-6" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4">Task Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <button
        onClick={() => setIsModalOpen(true)}
        aria-label="Create new task"
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 mb-4"
      >
        + New Task
      </button>

      {tasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-900 text-gray-100 rounded-lg">
          <CheckSquare className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-lg mb-4">No tasks found. Create your first task!</p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Create Task
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Tasks list" className="min-w-full border-collapse border border-gray-300">
          <thead>
            <tr>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Title</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Description</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Status</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Priority</th>
              <th scope="col" className="border border-gray-300 px-4 py-2 bg-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.length === 0 ? (
              <tr>
                <td colSpan={5} className="border border-gray-300 px-4 py-2 text-center">
                  No tasks found. Create your first task!
                </td>
              </tr>
            ) : (
              tasks.map(task => (
                <tr key={task.id}>
                  <td className="border border-gray-300 px-4 py-2">{task.title}</td>
                  <td className="border border-gray-300 px-4 py-2">{task.description}</td>
                  <td className="border border-gray-300 px-4 py-2">{task.status}</td>
                  <td className="border border-gray-300 px-4 py-2">{task.priority}</td>
                  <td className="border border-gray-300 px-4 py-2">
                    <button
                      onClick={() => handleEdit(task)}
                      aria-label={`Edit task ${task.title}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(task)}
                      aria-label={`Delete task ${task.title}`}
                      className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
          </table>
        </div>
      )}

      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="task-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="task-modal-title" className="text-xl font-bold mb-4">
              {editingTask ? 'Edit Task' : 'Create New Task'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="task-title" className="block text-sm font-medium mb-1">Title</label>
                <input
                  ref={firstInputRef}
                  id="task-title"
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  aria-label="Task title"
                  aria-required="true"
                  required
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="task-description" className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  id="task-description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  aria-label="Task description"
                  rows={3}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="task-status" className="block text-sm font-medium mb-1">Status</label>
                <select
                  id="task-status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as Task['status'] })}
                  aria-label="Task status"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  <option value="pending">Pending</option>
                  <option value="in-progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
              <div className="mb-4">
                <label htmlFor="task-priority" className="block text-sm font-medium mb-1">Priority</label>
                <select
                  id="task-priority"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value as Task['priority'] })}
                  aria-label="Task priority"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  aria-label="Cancel"
                  className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  aria-label={editingTask ? 'Save task changes' : 'Create task'}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  {editingTask ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskManagement;
