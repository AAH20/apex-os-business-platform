import React, { useState, useEffect, useCallback } from "react";
import { crud, ListResult } from "../api/crud";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Project {
  id: number;
  name: string;
  description?: string;
  status: string;
  owner?: string;
  start_date?: string;
  end_date?: string;
  created_at: string;
  updated_at: string;
}

interface Milestone {
  id: number;
  project_id: number;
  name: string;
  description?: string;
  due_date?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Task {
  id: number;
  project_id: number;
  milestone_id?: number;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignee?: string;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

interface Resource {
  id: number;
  project_id: number;
  name: string;
  type: string;
  allocation: number;
  created_at: string;
  updated_at: string;
}

interface TimeEntry {
  id: number;
  task_id: number;
  user: string;
  hours: number;
  date: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

type Tab = "projects" | "milestones" | "tasks" | "resources" | "time-entries";

const TABS: { key: Tab; label: string }[] = [
  { key: "projects", label: "Projects" },
  { key: "milestones", label: "Milestones" },
  { key: "tasks", label: "Tasks" },
  { key: "resources", label: "Resources" },
  { key: "time-entries", label: "Time Entries" },
];

const PROJECT_STATUSES = ["active", "archived", "completed", "on_hold"];
const MILESTONE_STATUSES = ["pending", "in_progress", "completed"];
const TASK_STATUSES = ["todo", "in_progress", "done"];
const TASK_PRIORITIES = ["low", "medium", "high"];
const RESOURCE_TYPES = ["human", "equipment", "software", "budget"];

const projectApi = crud<Project>("project-mgmt/projects");
const milestoneApi = crud<Milestone>("project-mgmt/milestones");
const taskApi = crud<Task>("project-mgmt/tasks");
const resourceApi = crud<Resource>("project-mgmt/resources");
const timeEntryApi = crud<TimeEntry>("project-mgmt/time-entries");

// ─── Component ───────────────────────────────────────────────────────────────

const ProjectMgmtManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>("projects");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showDashboard, setShowDashboard] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);

  // Data states
  const [projects, setProjects] = useState<ListResult<Project>>({ items: [], total: 0, page: 1, limit: 10 });
  const [milestones, setMilestones] = useState<ListResult<Milestone>>({ items: [], total: 0, page: 1, limit: 10 });
  const [tasks, setTasks] = useState<ListResult<Task>>({ items: [], total: 0, page: 1, limit: 10 });
  const [resources, setResources] = useState<ListResult<Resource>>({ items: [], total: 0, page: 1, limit: 10 });
  const [timeEntries, setTimeEntries] = useState<ListResult<TimeEntry>>({ items: [], total: 0, page: 1, limit: 10 });

  // Form states
  const [projectForm, setProjectForm] = useState({ name: "", description: "", status: "active", owner: "", start_date: "", end_date: "" });
  const [milestoneForm, setMilestoneForm] = useState({ project_id: 1, name: "", description: "", due_date: "", status: "pending" });
  const [taskForm, setTaskForm] = useState({ project_id: 1, milestone_id: undefined as number | undefined, title: "", description: "", status: "todo", priority: "medium", assignee: "", due_date: "" });
  const [resourceForm, setResourceForm] = useState({ project_id: 1, name: "", type: "human", allocation: 100 });
  const [timeEntryForm, setTimeEntryForm] = useState({ task_id: 1, user: "", hours: 1, date: "", description: "" });

  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // Fetch data
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const result = await projectApi.list({ page: 1, limit: 100 });
      setProjects(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchMilestones = useCallback(async () => {
    try {
      const result = await milestoneApi.list({ page: 1, limit: 100 });
      setMilestones(result);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const result = await taskApi.list({ page: 1, limit: 100 });
      setTasks(result);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const fetchResources = useCallback(async () => {
    try {
      const result = await resourceApi.list({ page: 1, limit: 100 });
      setResources(result);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const fetchTimeEntries = useCallback(async () => {
    try {
      const result = await timeEntryApi.list({ page: 1, limit: 100 });
      setTimeEntries(result);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
    fetchMilestones();
    fetchTasks();
    fetchResources();
    fetchTimeEntries();
  }, [fetchProjects, fetchMilestones, fetchTasks, fetchResources, fetchTimeEntries]);

  // CRUD handlers
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (activeTab === "projects") {
        if (editingId) {
          await projectApi.update(editingId, projectForm);
        } else {
          await projectApi.create(projectForm as unknown as Omit<Project, "id"> & Partial<Pick<Project, "id">>);
        }
        fetchProjects();
      } else if (activeTab === "milestones") {
        if (editingId) {
          await milestoneApi.update(editingId, milestoneForm);
        } else {
          await milestoneApi.create(milestoneForm as unknown as Omit<Milestone, "id"> & Partial<Pick<Milestone, "id">>);
        }
        fetchMilestones();
      } else if (activeTab === "tasks") {
        if (editingId) {
          await taskApi.update(editingId, taskForm);
        } else {
          await taskApi.create(taskForm as unknown as Omit<Task, "id"> & Partial<Pick<Task, "id">>);
        }
        fetchTasks();
      } else if (activeTab === "resources") {
        if (editingId) {
          await resourceApi.update(editingId, resourceForm);
        } else {
          await resourceApi.create(resourceForm as unknown as Omit<Resource, "id"> & Partial<Pick<Resource, "id">>);
        }
        fetchResources();
      } else if (activeTab === "time-entries") {
        if (editingId) {
          await timeEntryApi.update(editingId, timeEntryForm);
        } else {
          await timeEntryApi.create(timeEntryForm as unknown as Omit<TimeEntry, "id"> & Partial<Pick<TimeEntry, "id">>);
        }
        fetchTimeEntries();
      }
      setShowForm(false);
      setEditingId(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = (id: number) => {
    setDeleteTarget(id);
  };

  const confirmDelete = async () => {
    if (deleteTarget === null) return;
    setError(null);
    try {
      if (activeTab === "projects") {
        await projectApi.delete(deleteTarget);
        fetchProjects();
      } else if (activeTab === "milestones") {
        await milestoneApi.delete(deleteTarget);
        fetchMilestones();
      } else if (activeTab === "tasks") {
        await taskApi.delete(deleteTarget);
        fetchTasks();
      } else if (activeTab === "resources") {
        await resourceApi.delete(deleteTarget);
        fetchResources();
      } else if (activeTab === "time-entries") {
        await timeEntryApi.delete(deleteTarget);
        fetchTimeEntries();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleEdit = (item: any) => {
    setEditingId(item.id);
    if (activeTab === "projects") {
      setProjectForm({ name: item.name, description: item.description || "", status: item.status, owner: item.owner || "", start_date: item.start_date || "", end_date: item.end_date || "" });
    } else if (activeTab === "milestones") {
      setMilestoneForm({ project_id: item.project_id, name: item.name, description: item.description || "", due_date: item.due_date || "", status: item.status });
    } else if (activeTab === "tasks") {
      setTaskForm({ project_id: item.project_id, milestone_id: item.milestone_id, title: item.title, description: item.description || "", status: item.status, priority: item.priority, assignee: item.assignee || "", due_date: item.due_date || "" });
    } else if (activeTab === "resources") {
      setResourceForm({ project_id: item.project_id, name: item.name, type: item.type, allocation: item.allocation });
    } else if (activeTab === "time-entries") {
      setTimeEntryForm({ task_id: item.task_id, user: item.user, hours: item.hours, date: item.date, description: item.description || "" });
    }
    setShowForm(true);
  };

  const openCreate = () => {
    setEditingId(null);
    setProjectForm({ name: "", description: "", status: "active", owner: "", start_date: "", end_date: "" });
    setMilestoneForm({ project_id: 1, name: "", description: "", due_date: "", status: "pending" });
    setTaskForm({ project_id: 1, milestone_id: undefined, title: "", description: "", status: "todo", priority: "medium", assignee: "", due_date: "" });
    setResourceForm({ project_id: 1, name: "", type: "human", allocation: 100 });
    setTimeEntryForm({ task_id: 1, user: "", hours: 1, date: "", description: "" });
    setShowForm(true);
  };

  // ─── Search, Filter & Export ───────────────────────────────────────────────
  const getCurrentItems = (): any[] => {
    if (activeTab === "projects") return projects.items;
    if (activeTab === "milestones") return milestones.items;
    if (activeTab === "tasks") return tasks.items;
    if (activeTab === "resources") return resources.items;
    return timeEntries.items;
  };

  const filteredItems = getCurrentItems().filter((item) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch = !q || Object.values(item).some(v => String(v).toLowerCase().includes(q));
    const matchesStatus = !filterStatus || (item as any).status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const exportCSV = () => {
    if (filteredItems.length === 0) return;
    const headers = Object.keys(filteredItems[0]);
    const csv = [headers.join(","), ...filteredItems.map(item => headers.map(h => JSON.stringify((item as any)[h] ?? "")).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${activeTab}_export.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    if (filteredItems.length === 0) return;
    const blob = new Blob([JSON.stringify(filteredItems, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${activeTab}_export.json`; a.click();
    URL.revokeObjectURL(url);
  };

  // ─── Render helpers ────────────────────────────────────────────────────────

  const inputClass = "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm text-gray-100 focus:outline-none focus:border-cyan-500";
  const btnPrimary = "px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded text-sm font-medium transition-colors";
  const btnSecondary = "px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-sm transition-colors";
  const btnDanger = "px-3 py-1 bg-red-900/50 hover:bg-red-800 text-red-200 rounded text-xs transition-colors";

  const statusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: "bg-green-900/50 text-green-300",
      completed: "bg-blue-900/50 text-blue-300",
      on_hold: "bg-yellow-900/50 text-yellow-300",
      archived: "bg-gray-700 text-gray-300",
      pending: "bg-yellow-900/50 text-yellow-300",
      in_progress: "bg-cyan-900/50 text-cyan-300",
      todo: "bg-gray-700 text-gray-300",
      done: "bg-green-900/50 text-green-300",
      low: "bg-gray-700 text-gray-300",
      medium: "bg-yellow-900/50 text-yellow-300",
      high: "bg-red-900/50 text-red-300",
    };
    return colors[status] || "bg-gray-700 text-gray-300";
  };

  const renderTable = () => {
    if (loading) {
      return <div className="text-center py-8 text-gray-400">Loading...</div>;
    }

    if (activeTab === "projects") {
      return (
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left px-4 py-3 text-gray-300">Name</th>
              <th className="text-left px-4 py-3 text-gray-300">Status</th>
              <th className="text-left px-4 py-3 text-gray-300">Owner</th>
              <th className="text-left px-4 py-3 text-gray-300">Description</th>
              <th className="text-right px-4 py-3 text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((p: any) => (
              <tr key={p.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                <td className="px-4 py-3 font-medium text-gray-100">{p.name}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColor(p.status)}`}>{p.status}</span></td>
                <td className="px-4 py-3 text-gray-400">{p.owner || "-"}</td>
                <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{p.description || "-"}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(p)} className={btnSecondary}>Edit</button>
                  <button onClick={() => handleDelete(p.id)} className={btnDanger}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === "milestones") {
      return (
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left px-4 py-3 text-gray-300">Name</th>
              <th className="text-left px-4 py-3 text-gray-300">Project</th>
              <th className="text-left px-4 py-3 text-gray-300">Status</th>
              <th className="text-left px-4 py-3 text-gray-300">Due Date</th>
              <th className="text-right px-4 py-3 text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((m: any) => (
              <tr key={m.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                <td className="px-4 py-3 font-medium text-gray-100">{m.name}</td>
                <td className="px-4 py-3 text-gray-400">Project {m.project_id}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColor(m.status)}`}>{m.status}</span></td>
                <td className="px-4 py-3 text-gray-400">{m.due_date || "-"}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(m)} className={btnSecondary}>Edit</button>
                  <button onClick={() => handleDelete(m.id)} className={btnDanger}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === "tasks") {
      return (
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left px-4 py-3 text-gray-300">Title</th>
              <th className="text-left px-4 py-3 text-gray-300">Project</th>
              <th className="text-left px-4 py-3 text-gray-300">Status</th>
              <th className="text-left px-4 py-3 text-gray-300">Priority</th>
              <th className="text-left px-4 py-3 text-gray-300">Assignee</th>
              <th className="text-right px-4 py-3 text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((t: any) => (
              <tr key={t.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                <td className="px-4 py-3 font-medium text-gray-100">{t.title}</td>
                <td className="px-4 py-3 text-gray-400">Project {t.project_id}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColor(t.status)}`}>{t.status}</span></td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${statusColor(t.priority)}`}>{t.priority}</span></td>
                <td className="px-4 py-3 text-gray-400">{t.assignee || "-"}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(t)} className={btnSecondary}>Edit</button>
                  <button onClick={() => handleDelete(t.id)} className={btnDanger}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === "resources") {
      return (
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left px-4 py-3 text-gray-300">Name</th>
              <th className="text-left px-4 py-3 text-gray-300">Project</th>
              <th className="text-left px-4 py-3 text-gray-300">Type</th>
              <th className="text-left px-4 py-3 text-gray-300">Allocation</th>
              <th className="text-right px-4 py-3 text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((r: any) => (
              <tr key={r.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                <td className="px-4 py-3 font-medium text-gray-100">{r.name}</td>
                <td className="px-4 py-3 text-gray-400">Project {r.project_id}</td>
                <td className="px-4 py-3 text-gray-400">{r.type}</td>
                <td className="px-4 py-3 text-gray-400">{r.allocation}%</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(r)} className={btnSecondary}>Edit</button>
                  <button onClick={() => handleDelete(r.id)} className={btnDanger}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (activeTab === "time-entries") {
      return (
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left px-4 py-3 text-gray-300">Task</th>
              <th className="text-left px-4 py-3 text-gray-300">User</th>
              <th className="text-left px-4 py-3 text-gray-300">Hours</th>
              <th className="text-left px-4 py-3 text-gray-300">Date</th>
              <th className="text-left px-4 py-3 text-gray-300">Description</th>
              <th className="text-right px-4 py-3 text-gray-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((t: any) => (
              <tr key={t.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                <td className="px-4 py-3 text-gray-400">Task {t.task_id}</td>
                <td className="px-4 py-3 text-gray-100">{t.user}</td>
                <td className="px-4 py-3 text-gray-400">{t.hours}h</td>
                <td className="px-4 py-3 text-gray-400">{t.date}</td>
                <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{t.description || "-"}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(t)} className={btnSecondary}>Edit</button>
                  <button onClick={() => handleDelete(t.id)} className={btnDanger}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    return null;
  };

  const renderForm = () => {
    if (!showForm) return null;

    return (
      <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 max-h-[90vh] overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4 text-gray-100">
            {editingId ? "Edit" : "New"} {activeTab.replace("-", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {activeTab === "projects" && (
              <>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input type="text" required value={projectForm.name} onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Description</label>
                  <textarea rows={3} value={projectForm.description} onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Status</label>
                  <select value={projectForm.status} onChange={(e) => setProjectForm({ ...projectForm, status: e.target.value })} className={inputClass}>
                    {PROJECT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Owner</label>
                  <input type="text" value={projectForm.owner} onChange={(e) => setProjectForm({ ...projectForm, owner: e.target.value })} className={inputClass} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Start Date</label>
                    <input type="date" value={projectForm.start_date} onChange={(e) => setProjectForm({ ...projectForm, start_date: e.target.value })} className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">End Date</label>
                    <input type="date" value={projectForm.end_date} onChange={(e) => setProjectForm({ ...projectForm, end_date: e.target.value })} className={inputClass} />
                  </div>
                </div>
              </>
            )}

            {activeTab === "milestones" && (
              <>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Project</label>
                  <select value={milestoneForm.project_id} onChange={(e) => setMilestoneForm({ ...milestoneForm, project_id: Number(e.target.value) })} className={inputClass}>
                    {projects.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input type="text" required value={milestoneForm.name} onChange={(e) => setMilestoneForm({ ...milestoneForm, name: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Description</label>
                  <textarea rows={3} value={milestoneForm.description} onChange={(e) => setMilestoneForm({ ...milestoneForm, description: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Due Date</label>
                  <input type="date" value={milestoneForm.due_date} onChange={(e) => setMilestoneForm({ ...milestoneForm, due_date: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Status</label>
                  <select value={milestoneForm.status} onChange={(e) => setMilestoneForm({ ...milestoneForm, status: e.target.value })} className={inputClass}>
                    {MILESTONE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </>
            )}

            {activeTab === "tasks" && (
              <>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Project</label>
                  <select value={taskForm.project_id} onChange={(e) => setTaskForm({ ...taskForm, project_id: Number(e.target.value) })} className={inputClass}>
                    {projects.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Title</label>
                  <input type="text" required value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Description</label>
                  <textarea rows={3} value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} className={inputClass} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Status</label>
                    <select value={taskForm.status} onChange={(e) => setTaskForm({ ...taskForm, status: e.target.value })} className={inputClass}>
                      {TASK_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Priority</label>
                    <select value={taskForm.priority} onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })} className={inputClass}>
                      {TASK_PRIORITIES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Assignee</label>
                  <input type="text" value={taskForm.assignee} onChange={(e) => setTaskForm({ ...taskForm, assignee: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Due Date</label>
                  <input type="date" value={taskForm.due_date} onChange={(e) => setTaskForm({ ...taskForm, due_date: e.target.value })} className={inputClass} />
                </div>
              </>
            )}

            {activeTab === "resources" && (
              <>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Project</label>
                  <select value={resourceForm.project_id} onChange={(e) => setResourceForm({ ...resourceForm, project_id: Number(e.target.value) })} className={inputClass}>
                    {projects.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input type="text" required value={resourceForm.name} onChange={(e) => setResourceForm({ ...resourceForm, name: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Type</label>
                  <select value={resourceForm.type} onChange={(e) => setResourceForm({ ...resourceForm, type: e.target.value })} className={inputClass}>
                    {RESOURCE_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Allocation (%)</label>
                  <input type="number" min={0} max={100} value={resourceForm.allocation} onChange={(e) => setResourceForm({ ...resourceForm, allocation: Number(e.target.value) })} className={inputClass} />
                </div>
              </>
            )}

            {activeTab === "time-entries" && (
              <>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Task</label>
                  <select value={timeEntryForm.task_id} onChange={(e) => setTimeEntryForm({ ...timeEntryForm, task_id: Number(e.target.value) })} className={inputClass}>
                    {tasks.items.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">User</label>
                  <input type="text" required value={timeEntryForm.user} onChange={(e) => setTimeEntryForm({ ...timeEntryForm, user: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Hours</label>
                  <input type="number" min={0.5} max={24} step={0.5} value={timeEntryForm.hours} onChange={(e) => setTimeEntryForm({ ...timeEntryForm, hours: Number(e.target.value) })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Date</label>
                  <input type="date" value={timeEntryForm.date} onChange={(e) => setTimeEntryForm({ ...timeEntryForm, date: e.target.value })} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Description</label>
                  <textarea rows={2} value={timeEntryForm.description} onChange={(e) => setTimeEntryForm({ ...timeEntryForm, description: e.target.value })} className={inputClass} />
                </div>
              </>
            )}

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setShowForm(false); setEditingId(null); }} className={btnSecondary}>Cancel</button>
              <button type="submit" className={btnPrimary}>{editingId ? "Update" : "Create"}</button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  // ─── Dashboard ─────────────────────────────────────────────────────────────
  const activeProjects = projects.items.filter((p) => p.status === "active").length;
  const openMilestones = milestones.items.filter((m) => m.status !== "completed").length;
  const pendingTasks = tasks.items.filter((t) => t.status !== "done").length;
  const totalTimeEntries = timeEntries.items.length;

  const projectsByStatus = PROJECT_STATUSES.map((status) => ({
    name: status,
    count: projects.items.filter((p) => p.status === status).length,
  }));

  const tasksByPriority = TASK_PRIORITIES.map((priority) => ({
    name: priority,
    value: tasks.items.filter((t) => t.priority === priority).length,
  }));

  const PIE_COLORS = ["#6b7280", "#eab308", "#ef4444"];

  const renderDashboard = () => {
    if (!showDashboard) return null;
    return (
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">Dashboard</h2>
          <button onClick={() => setShowDashboard(false)} className={btnSecondary}>Hide Dashboard</button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Active Projects</div>
            <div className="text-2xl font-bold text-cyan-400 mt-1">{activeProjects}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Open Milestones</div>
            <div className="text-2xl font-bold text-yellow-400 mt-1">{openMilestones}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Pending Tasks</div>
            <div className="text-2xl font-bold text-red-400 mt-1">{pendingTasks}</div>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-400">Time Entries</div>
            <div className="text-2xl font-bold text-green-400 mt-1">{totalTimeEntries}</div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Projects by Status</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={projectsByStatus}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "6px" }} labelStyle={{ color: "#e5e7eb" }} />
                <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Tasks by Priority</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={tasksByPriority} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {tasksByPriority.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "6px" }} labelStyle={{ color: "#e5e7eb" }} />
                <Legend wrapperStyle={{ color: "#9ca3af", fontSize: "12px" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Project Management</h1>
          <div className="flex gap-2">
            <button onClick={() => setShowDashboard(!showDashboard)} className={btnSecondary}>
              {showDashboard ? "Hide Dashboard" : "Show Dashboard"}
            </button>
            <button onClick={openCreate} className={btnPrimary}>+ New {activeTab.replace("-", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>
        )}

        {/* Dashboard */}
        {renderDashboard()}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-gray-700">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "text-cyan-400 border-b-2 border-cyan-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search, Filter & Export */}
        <div className="flex flex-wrap gap-3 mb-4">
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm text-gray-100 focus:outline-none focus:border-cyan-500"
          />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm text-gray-100 focus:outline-none focus:border-cyan-500"
          >
            <option value="">All Statuses</option>
            {activeTab === "projects" && PROJECT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            {activeTab === "milestones" && MILESTONE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            {activeTab === "tasks" && TASK_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={exportCSV} className="px-4 py-2 bg-green-700 hover:bg-green-600 text-white rounded text-sm font-medium transition-colors">Export CSV</button>
          <button onClick={exportJSON} className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white rounded text-sm font-medium transition-colors">Export JSON</button>
        </div>

        {/* Table */}
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          {renderTable()}
        </div>

        {/* Delete Confirmation Modal */}
        {deleteTarget !== null && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setDeleteTarget(null)}>
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm border border-gray-700" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-lg font-semibold mb-3 text-gray-100">Confirm Delete</h2>
              <p className="text-sm text-gray-400 mb-5">Are you sure you want to delete this {activeTab.replace("-", " ")}? This action cannot be undone.</p>
              <div className="flex justify-end gap-2">
                <button onClick={() => setDeleteTarget(null)} className={btnSecondary}>Cancel</button>
                <button onClick={confirmDelete} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors">Delete</button>
              </div>
            </div>
          </div>
        )}

        {/* Form Modal */}
        {renderForm()}
      </div>
    </div>
  );
};

export default ProjectMgmtManagement;
