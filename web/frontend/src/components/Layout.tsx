import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Calculator,
  Users,
  BarChart3,
  Radio,
  Database,
  Brain,
  TrendingUp,
  Menu,
  X,
  Zap,
  Search,
  Bell,
  ChevronDown,
  ChevronRight,
  Settings,
  LogOut,
  User,
  CreditCard,
  Calendar,
  Clock,
  Plus,
  Download,
  RefreshCw,
  Sun,
  Moon,
  HelpCircle,
  FileText,
  Star,
  ArrowUpRight,
  Check,
  AlertTriangle,
  Info,
} from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────────────────────

interface NavItem {
  path: string
  label: string
  icon: React.ComponentType<{ size?: number | string; className?: string }>
  badge?: string
  description?: string
}

interface NavSection {
  title: string
  items: NavItem[]
}

interface Notification {
  id: string
  title: string
  message: string
  time: string
  read: boolean
  type: 'info' | 'warning' | 'success' | 'error'
}

interface BreadcrumbItem {
  label: string
  path?: string
}

// ─── Navigation Data ─────────────────────────────────────────────────────────

const navSections: NavSection[] = [
  {
    title: 'Overview',
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard, description: 'Main overview' },
      { path: '/analytics', label: 'Analytics', icon: BarChart3, description: 'Data insights' },
      { path: '/continuous-bi', label: 'Continuous BI', icon: TrendingUp, description: 'Real-time BI' },
    ],
  },
  {
    title: 'Finance',
    items: [
      { path: '/accounting', label: 'Accounting', icon: Calculator, description: 'Financial records' },
    ],
  },
  {
    title: 'Sales',
    items: [
      { path: '/crm', label: 'CRM', icon: Users, description: 'Customer relations' },
    ],
  },
  {
    title: 'Intelligence',
    items: [
      { path: '/agent-reach', label: 'Agent-Reach', icon: Radio, description: 'Agent network' },
      { path: '/bigdata', label: 'Big Data', icon: Database, description: 'Data lake' },
      { path: '/datascience', label: 'Data Science', icon: Brain, description: 'ML models' },
    ],
  },
  {
    title: 'CRUD Operations',
    items: [
      { path: '/dashboard-crud', label: 'Dashboard CRUD', icon: LayoutDashboard, description: 'Manage dashboards' },
      { path: '/accounting-crud', label: 'Accounting CRUD', icon: Calculator, description: 'Manage accounts' },
      { path: '/crm-crud', label: 'CRM CRUD', icon: Users, description: 'Manage leads' },
      { path: '/analytics-crud', label: 'Analytics CRUD', icon: BarChart3, description: 'Manage analytics' },
      { path: '/agent-reach-crud', label: 'Agent-Reach CRUD', icon: Radio, description: 'Manage agents' },
      { path: '/bigdata-crud', label: 'Big Data CRUD', icon: Database, description: 'Manage datasets' },
      { path: '/datascience-crud', label: 'Data Science CRUD', icon: Brain, description: 'Manage models' },
      { path: '/continuous-bi-crud', label: 'Continuous BI CRUD', icon: TrendingUp, description: 'Manage reports' },
      { path: '/users-crud', label: 'Users CRUD', icon: Users, description: 'Manage users' },
      { path: '/journal-entries-crud', label: 'Journal Entries CRUD', icon: FileText, description: 'Manage entries' },
      { path: '/invoices-crud', label: 'Invoices CRUD', icon: Receipt, description: 'Manage invoices' },
    ],
  },
]

// ─── Notifications Data ──────────────────────────────────────────────────────

const mockNotifications: Notification[] = [
  { id: '1', title: 'Server Alert', message: 'CPU usage exceeded 90% on prod-server-03', time: '2m ago', read: false, type: 'error' },
  { id: '2', title: 'New Lead', message: 'Acme Corp requested a demo', time: '15m ago', read: false, type: 'info' },
  { id: '3', title: 'Payment Received', message: 'Invoice #1042 paid — $12,400', time: '1h ago', read: false, type: 'success' },
  { id: '4', title: 'Report Ready', message: 'Q3 Financial Report is ready', time: '3h ago', read: true, type: 'info' },
  { id: '5', title: 'Security Warning', message: 'Unusual login detected from new IP', time: '5h ago', read: true, type: 'warning' },
]

// ─── Utility Functions ───────────────────────────────────────────────────────

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  })
}

// ─── Breadcrumb Generator ────────────────────────────────────────────────────

function generateBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean)
  const breadcrumbs: BreadcrumbItem[] = [{ label: 'Home', path: '/' }]

  let currentPath = ''
  for (const segment of segments) {
    currentPath += `/${segment}`
    const label = segment
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
    breadcrumbs.push({ label, path: currentPath })
  }

  return breadcrumbs
}

// ─── Notification Icon Helper ────────────────────────────────────────────────

function NotificationTypeIcon({ type }: { type: Notification['type'] }) {
  const iconMap = {
    info: Info,
    warning: AlertTriangle,
    success: Check,
    error: AlertTriangle,
  }
  const Icon = iconMap[type]
  const colorMap = {
    info: 'text-blue-400',
    warning: 'text-amber-400',
    success: 'text-emerald-400',
    error: 'text-red-400',
  }
  return <Icon size={14} className={colorMap[type]} />
}

// ─── Main Layout Component ───────────────────────────────────────────────────

export default function Layout() {
  // State
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    Overview: true,
    Finance: true,
    Sales: true,
    Intelligence: false,
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [isDark, setIsDark] = useState(true)
  const [notifications, setNotifications] = useState(mockNotifications)
  const [quickActionOpen, setQuickActionOpen] = useState(false)

  // Refs
  const location = useLocation()
  const navigate = useNavigate()
  const searchInputRef = useRef<HTMLInputElement>(null)
  const notificationRef = useRef<HTMLDivElement>(null)
  const profileRef = useRef<HTMLDivElement>(null)
  const quickActionRef = useRef<HTMLDivElement>(null)

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false)
      }
      if (quickActionRef.current && !quickActionRef.current.contains(event.target as Node)) {
        setQuickActionOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Keyboard shortcut for search
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        searchInputRef.current?.focus()
      }
      if (event.key === 'Escape') {
        setSearchFocused(false)
        searchInputRef.current?.blur()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Toggle section expansion
  const toggleSection = useCallback((title: string) => {
    setExpandedSections((prev) => ({ ...prev, [title]: !prev[title] }))
  }, [])

  // Toggle sidebar collapse (desktop)
  const toggleSidebarCollapse = useCallback(() => {
    setSidebarCollapsed((prev) => !prev)
  }, [])

  // Toggle mobile sidebar
  const toggleMobileSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev)
  }, [])

  // Close mobile sidebar
  const closeMobileSidebar = useCallback(() => {
    setSidebarOpen(false)
  }, [])

  // Mark notification as read
  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }, [])

  // Mark all notifications as read
  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }, [])

  // Filter navigation items based on search
  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return navSections
    const query = searchQuery.toLowerCase()
    return navSections
      .map((section) => ({
        ...section,
        items: section.items.filter(
          (item) =>
            item.label.toLowerCase().includes(query) ||
            item.description?.toLowerCase().includes(query)
        ),
      }))
      .filter((section) => section.items.length > 0)
  }, [searchQuery])

  // Unread notification count
  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications]
  )

  // Generate breadcrumbs
  const breadcrumbs = useMemo(
    () => generateBreadcrumbs(location.pathname),
    [location.pathname]
  )

  // Quick actions
  const quickActions = [
    { label: 'New Report', icon: FileText, action: () => navigate('/analytics') },
    { label: 'Add User', icon: User, action: () => navigate('/crm') },
    { label: 'Export Data', icon: Download, action: () => {} },
    { label: 'Refresh', icon: RefreshCw, action: () => window.location.reload() },
  ]

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{
        background: isDark
          ? 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)'
          : 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
      }}
    >
      {/* ── Mobile Overlay ─────────────────────────────────────────────────── */}
      <div
        className={`fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity duration-300 lg:hidden ${
          sidebarOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={closeMobileSidebar}
        aria-hidden="true"
      />

      {/* ── Sidebar ───────────────────────────────────────────────────────── */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 flex flex-col
          transition-all duration-300 ease-in-out
          lg:static lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          ${sidebarCollapsed ? 'lg:w-20' : 'lg:w-72'}
          w-72
        `}
        style={{
          background: isDark
            ? 'rgba(15, 23, 42, 0.85)'
            : 'rgba(255, 255, 255, 0.9)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRight: isDark
            ? '1px solid rgba(148, 163, 184, 0.1)'
            : '1px solid rgba(0, 0, 0, 0.08)',
        }}
      >
        {/* ── Branding ─────────────────────────────────────────────────────── */}
        <div
          className="flex h-16 items-center gap-3 px-4"
          style={{
            borderBottom: isDark
              ? '1px solid rgba(148, 163, 184, 0.1)'
              : '1px solid rgba(0, 0, 0, 0.08)',
          }}
        >
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-lg"
            style={{
              background: 'linear-gradient(135deg, #06b6d4, #a855f7)',
              boxShadow: '0 4px 15px rgba(6, 182, 212, 0.3)',
            }}
          >
            <Zap size={20} className="text-white" />
          </div>
          {!sidebarCollapsed && (
            <div className="min-w-0 flex-1 animate-fadeIn">
              <h1
                className="text-lg font-bold tracking-tight"
                style={{ color: isDark ? '#f1f5f9' : '#1e293b' }}
              >
                APEX-OS
              </h1>
              <p
                className="text-xs"
                style={{ color: isDark ? '#94a3b8' : '#64748b' }}
              >
                Business Platform
              </p>
            </div>
          )}
          {/* Mobile close button */}
          <button
            onClick={closeMobileSidebar}
            className="ml-auto rounded-lg p-1.5 transition-colors hover:bg-white/10 lg:hidden"
            style={{ color: isDark ? '#94a3b8' : '#64748b' }}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
          {/* Desktop collapse button */}
          <button
            onClick={toggleSidebarCollapse}
            className="ml-auto hidden rounded-lg p-1.5 transition-all hover:bg-white/10 lg:block"
            style={{ color: isDark ? '#94a3b8' : '#64748b' }}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronRight
              size={18}
              className={`transition-transform duration-300 ${
                sidebarCollapsed ? '' : 'rotate-180'
              }`}
            />
          </button>
        </div>

        {/* ── Search Bar ───────────────────────────────────────────────────── */}
        <div className="px-4 pt-4">
          <div
            className={`relative flex items-center rounded-xl transition-all duration-200 ${
              searchFocused ? 'ring-2 ring-cyan-500/50' : ''
            }`}
            style={{
              background: isDark
                ? 'rgba(30, 41, 59, 0.6)'
                : 'rgba(241, 245, 249, 0.8)',
              border: isDark
                ? '1px solid rgba(148, 163, 184, 0.15)'
                : '1px solid rgba(0, 0, 0, 0.1)',
            }}
          >
            <Search
              size={16}
              className="absolute left-3"
              style={{ color: isDark ? '#64748b' : '#94a3b8' }}
            />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              className="w-full bg-transparent py-2.5 pl-10 pr-12 text-sm outline-none placeholder:text-slate-500"
              style={{ color: isDark ? '#e2e8f0' : '#334155' }}
            />
            <kbd
              className="absolute right-3 hidden rounded px-1.5 py-0.5 text-xs sm:block"
              style={{
                background: isDark
                  ? 'rgba(51, 65, 85, 0.5)'
                  : 'rgba(226, 232, 240, 0.8)',
                color: isDark ? '#64748b' : '#94a3b8',
              }}
            >
              ⌘K
            </kbd>
          </div>
        </div>

        {/* ── Navigation ───────────────────────────────────────────────────── */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {filteredSections.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Search
                size={32}
                style={{ color: isDark ? '#475569' : '#cbd5e1' }}
              />
              <p
                className="mt-2 text-sm"
                style={{ color: isDark ? '#64748b' : '#94a3b8' }}
              >
                No results found
              </p>
            </div>
          ) : (
            filteredSections.map((section) => (
              <div key={section.title} className="mb-2">
                {/* Section Header */}
                {!sidebarCollapsed && (
                  <button
                    onClick={() => toggleSection(section.title)}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors hover:bg-white/5"
                    style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                  >
                    <span>{section.title}</span>
                    <ChevronDown
                      size={14}
                      className={`transition-transform duration-200 ${
                        expandedSections[section.title] ? '' : '-rotate-90'
                      }`}
                    />
                  </button>
                )}

                {/* Section Items */}
                <div
                  className={`overflow-hidden transition-all duration-300 ease-in-out ${
                    expandedSections[section.title] || sidebarCollapsed
                      ? 'max-h-96 opacity-100'
                      : 'max-h-0 opacity-0'
                  }`}
                >
                  <ul className="space-y-0.5">
                    {section.items.map((item) => {
                      const Icon = item.icon
                      const isActive = location.pathname === item.path
                      return (
                        <li key={item.path}>
                          <NavLink
                            to={item.path}
                            end={item.path === '/'}
                            onClick={closeMobileSidebar}
                            className={`
                              group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium
                              transition-all duration-200
                              ${
                                isActive
                                  ? 'text-white shadow-lg'
                                  : 'hover:bg-white/5 hover:text-white'
                              }
                            `}
                            style={
                              isActive
                                ? {
                                    background:
                                      'linear-gradient(135deg, rgba(6,182,212,0.2), rgba(168,85,247,0.2))',
                                    boxShadow:
                                      '0 4px 15px rgba(6, 182, 212, 0.15)',
                                    border:
                                      '1px solid rgba(6, 182, 212, 0.2)',
                                  }
                                : {
                                    color: isDark ? '#94a3b8' : '#64748b',
                                  }
                            }
                            title={sidebarCollapsed ? item.label : undefined}
                          >
                            <div className="relative shrink-0">
                              <Icon
                                size={18}
                                className={`transition-colors ${
                                  isActive
                                    ? 'text-cyan-400'
                                    : 'group-hover:text-cyan-400'
                                }`}
                              />
                              {item.badge && (
                                <span
                                  className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold text-white"
                                  style={{
                                    background:
                                      'linear-gradient(135deg, #ef4444, #f97316)',
                                  }}
                                >
                                  {item.badge}
                                </span>
                              )}
                            </div>
                            {!sidebarCollapsed && (
                              <>
                                <span className="flex-1 truncate">{item.label}</span>
                                {isActive && (
                                  <ArrowUpRight
                                    size={14}
                                    className="text-cyan-400 opacity-0 transition-opacity group-hover:opacity-100"
                                  />
                                )}
                              </>
                            )}
                          </NavLink>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              </div>
            ))
          )}
        </nav>

        {/* ── User Profile Section ─────────────────────────────────────────── */}
        <div
          className="px-4 py-4"
          style={{
            borderTop: isDark
              ? '1px solid rgba(148, 163, 184, 0.1)'
              : '1px solid rgba(0, 0, 0, 0.08)',
          }}
        >
          <div
            className="flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-white/5"
            style={{
              background: isDark
                ? 'rgba(30, 41, 59, 0.4)'
                : 'rgba(241, 245, 249, 0.6)',
            }}
          >
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
              style={{
                background: 'linear-gradient(135deg, #06b6d4, #a855f7)',
              }}
            >
              AH
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0 flex-1">
                <p
                  className="truncate text-sm font-semibold"
                  style={{ color: isDark ? '#f1f5f9' : '#1e293b' }}
                >
                  Ahmed Hassan
                </p>
                <p
                  className="truncate text-xs"
                  style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                >
                  admin@apex-os.com
                </p>
              </div>
            )}
            {!sidebarCollapsed && (
              <button
                className="rounded-lg p-1.5 transition-colors hover:bg-white/10"
                style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                aria-label="User settings"
              >
                <Settings size={16} />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main Content Area ─────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* ── Top Bar ──────────────────────────────────────────────────────── */}
        <header
          className="flex h-16 items-center justify-between px-4 lg:px-6"
          style={{
            background: isDark
              ? 'rgba(15, 23, 42, 0.7)'
              : 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderBottom: isDark
              ? '1px solid rgba(148, 163, 184, 0.1)'
              : '1px solid rgba(0, 0, 0, 0.08)',
          }}
        >
          {/* Left: Hamburger + Breadcrumbs */}
          <div className="flex items-center gap-4">
            {/* Mobile hamburger */}
            <button
              onClick={toggleMobileSidebar}
              className="rounded-lg p-2 transition-colors hover:bg-white/10 lg:hidden"
              style={{ color: isDark ? '#e2e8f0' : '#334155' }}
              aria-label="Open sidebar"
            >
              <Menu size={24} />
            </button>

            {/* Breadcrumbs */}
            <nav className="hidden items-center gap-1 sm:flex" aria-label="Breadcrumb">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.path || crumb.label} className="flex items-center">
                  {index > 0 && (
                    <ChevronRight
                      size={14}
                      className="mx-1"
                      style={{ color: isDark ? '#475569' : '#cbd5e1' }}
                    />
                  )}
                  {crumb.path && index < breadcrumbs.length - 1 ? (
                    <NavLink
                      to={crumb.path}
                      className="rounded-md px-2 py-1 text-sm transition-colors hover:bg-white/5"
                      style={{ color: isDark ? '#94a3b8' : '#64748b' }}
                    >
                      {crumb.label}
                    </NavLink>
                  ) : (
                    <span
                      className="rounded-md px-2 py-1 text-sm font-medium"
                      style={{
                        color: isDark ? '#f1f5f9' : '#1e293b',
                        background: isDark
                          ? 'rgba(6, 182, 212, 0.1)'
                          : 'rgba(6, 182, 212, 0.08)',
                      }}
                    >
                      {crumb.label}
                    </span>
                  )}
                </div>
              ))}
            </nav>
          </div>

          {/* Right: Date/Time + Actions */}
          <div className="flex items-center gap-2">
            {/* Date/Time Display */}
            <div
              className="hidden items-center gap-3 rounded-xl px-4 py-2 md:flex"
              style={{
                background: isDark
                  ? 'rgba(30, 41, 59, 0.5)'
                  : 'rgba(241, 245, 249, 0.8)',
                border: isDark
                  ? '1px solid rgba(148, 163, 184, 0.1)'
                  : '1px solid rgba(0, 0, 0, 0.08)',
              }}
            >
              <div className="flex items-center gap-2">
                <Calendar
                  size={14}
                  style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                />
                <span
                  className="text-sm"
                  style={{ color: isDark ? '#94a3b8' : '#64748b' }}
                >
                  {formatDate(currentTime)}
                </span>
              </div>
              <div
                className="h-4 w-px"
                style={{
                  background: isDark
                    ? 'rgba(148, 163, 184, 0.2)'
                    : 'rgba(0, 0, 0, 0.1)',
                }}
              />
              <div className="flex items-center gap-2">
                <Clock
                  size={14}
                  style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                />
                <span
                  className="text-sm font-mono tabular-nums"
                  style={{ color: isDark ? '#94a3b8' : '#64748b' }}
                >
                  {formatTime(currentTime)}
                </span>
              </div>
            </div>

            {/* Quick Actions Dropdown */}
            <div ref={quickActionRef} className="relative">
              <button
                onClick={() => setQuickActionOpen((prev) => !prev)}
                className="rounded-xl p-2.5 transition-all hover:bg-white/10"
                style={{
                  color: isDark ? '#94a3b8' : '#64748b',
                  background: quickActionOpen
                    ? isDark
                      ? 'rgba(6, 182, 212, 0.15)'
                      : 'rgba(6, 182, 212, 0.1)'
                    : 'transparent',
                }}
                aria-label="Quick actions"
              >
                <Plus size={20} />
              </button>
              {quickActionOpen && (
                <div
                  className="fixed right-4 top-16 z-[100] w-56 overflow-hidden rounded-xl shadow-2xl animate-slideIn"
                  style={{
                    background: isDark
                      ? 'rgba(15, 23, 42, 0.95)'
                      : 'rgba(255, 255, 255, 0.98)',
                    backdropFilter: 'blur(20px)',
                    border: isDark
                      ? '1px solid rgba(148, 163, 184, 0.15)'
                      : '1px solid rgba(0, 0, 0, 0.1)',
                  }}
                >
                  <div
                    className="px-4 py-3"
                    style={{
                      borderBottom: isDark
                        ? '1px solid rgba(148, 163, 184, 0.1)'
                        : '1px solid rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    <p
                      className="text-xs font-semibold uppercase tracking-wider"
                      style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                    >
                      Quick Actions
                    </p>
                  </div>
                  {quickActions.map((action) => {
                    const Icon = action.icon
                    return (
                      <button
                        key={action.label}
                        onClick={() => {
                          action.action()
                          setQuickActionOpen(false)
                        }}
                        className="flex w-full items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-white/5"
                        style={{ color: isDark ? '#e2e8f0' : '#334155' }}
                      >
                        <Icon
                          size={16}
                          style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                        />
                        {action.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Theme Toggle */}
            <button
              onClick={() => setIsDark((prev) => !prev)}
              className="rounded-xl p-2.5 transition-all hover:bg-white/10"
              style={{ color: isDark ? '#94a3b8' : '#64748b' }}
              aria-label="Toggle theme"
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            {/* Notifications */}
            <div ref={notificationRef} className="relative">
              <button
                onClick={() => setNotificationsOpen((prev) => !prev)}
                className="relative rounded-xl p-2.5 transition-all hover:bg-white/10"
                style={{
                  color: isDark ? '#94a3b8' : '#64748b',
                  background: notificationsOpen
                    ? isDark
                      ? 'rgba(6, 182, 212, 0.15)'
                      : 'rgba(6, 182, 212, 0.1)'
                    : 'transparent',
                }}
                aria-label="Notifications"
              >
                <Bell size={20} />
                {unreadCount > 0 && (
                  <span
                    className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[10px] font-bold text-white shadow-lg"
                    style={{
                      background: 'linear-gradient(135deg, #ef4444, #f97316)',
                      boxShadow: '0 2px 8px rgba(239, 68, 68, 0.4)',
                    }}
                  >
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notifications Dropdown */}
              {notificationsOpen && (
                <div
                  className="fixed right-4 top-16 z-[100] w-80 overflow-hidden rounded-xl shadow-2xl animate-slideIn"
                  style={{
                    background: isDark
                      ? 'rgba(15, 23, 42, 0.95)'
                      : 'rgba(255, 255, 255, 0.98)',
                    backdropFilter: 'blur(20px)',
                    border: isDark
                      ? '1px solid rgba(148, 163, 184, 0.15)'
                      : '1px solid rgba(0, 0, 0, 0.1)',
                  }}
                >
                  {/* Header */}
                  <div
                    className="flex items-center justify-between px-4 py-3"
                    style={{
                      borderBottom: isDark
                        ? '1px solid rgba(148, 163, 184, 0.1)'
                        : '1px solid rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    <p
                      className="text-sm font-semibold"
                      style={{ color: isDark ? '#f1f5f9' : '#1e293b' }}
                    >
                      Notifications
                    </p>
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllAsRead}
                        className="text-xs font-medium text-cyan-400 transition-colors hover:text-cyan-300"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  {/* Notification List */}
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.map((notification) => (
                      <button
                        key={notification.id}
                        onClick={() => markAsRead(notification.id)}
                        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/5"
                        style={{
                          borderBottom: isDark
                            ? '1px solid rgba(148, 163, 184, 0.05)'
                            : '1px solid rgba(0, 0, 0, 0.04)',
                          background: notification.read
                            ? 'transparent'
                            : isDark
                              ? 'rgba(6, 182, 212, 0.03)'
                              : 'rgba(6, 182, 212, 0.02)',
                        }}
                      >
                        <div className="mt-0.5 shrink-0">
                          <NotificationTypeIcon type={notification.type} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p
                            className="text-sm font-medium"
                            style={{
                              color: isDark ? '#e2e8f0' : '#334155',
                            }}
                          >
                            {notification.title}
                          </p>
                          <p
                            className="mt-0.5 truncate text-xs"
                            style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                          >
                            {notification.message}
                          </p>
                          <p
                            className="mt-1 text-xs"
                            style={{ color: isDark ? '#475569' : '#cbd5e1' }}
                          >
                            {notification.time}
                          </p>
                        </div>
                        {!notification.read && (
                          <div
                            className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                            style={{ background: '#06b6d4' }}
                          />
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Footer */}
                  <div
                    className="px-4 py-3 text-center"
                    style={{
                      borderTop: isDark
                        ? '1px solid rgba(148, 163, 184, 0.1)'
                        : '1px solid rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    <button
                      className="text-xs font-medium text-cyan-400 transition-colors hover:text-cyan-300"
                      onClick={() => setNotificationsOpen(false)}
                    >
                      View all notifications
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Profile Dropdown */}
            <div ref={profileRef} className="relative">
              <button
                onClick={() => setProfileOpen((prev) => !prev)}
                className="flex items-center gap-2 rounded-xl p-1.5 transition-all hover:bg-white/10"
                style={{
                  background: profileOpen
                    ? isDark
                      ? 'rgba(6, 182, 212, 0.15)'
                      : 'rgba(6, 182, 212, 0.1)'
                    : 'transparent',
                }}
              >
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white"
                  style={{
                    background: 'linear-gradient(135deg, #06b6d4, #a855f7)',
                  }}
                >
                  AH
                </div>
                <ChevronDown
                  size={14}
                  className="hidden sm:block"
                  style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                />
              </button>

              {profileOpen && (
                <div
                  className="fixed right-4 top-16 z-[100] w-56 overflow-hidden rounded-xl shadow-2xl animate-slideIn"
                  style={{
                    background: isDark
                      ? 'rgba(15, 23, 42, 0.95)'
                      : 'rgba(255, 255, 255, 0.98)',
                    backdropFilter: 'blur(20px)',
                    border: isDark
                      ? '1px solid rgba(148, 163, 184, 0.15)'
                      : '1px solid rgba(0, 0, 0, 0.1)',
                  }}
                >
                  {/* Profile Header */}
                  <div
                    className="px-4 py-4"
                    style={{
                      borderBottom: isDark
                        ? '1px solid rgba(148, 163, 184, 0.1)'
                        : '1px solid rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    <p
                      className="text-sm font-semibold"
                      style={{ color: isDark ? '#f1f5f9' : '#1e293b' }}
                    >
                      Ahmed Hassan
                    </p>
                    <p
                      className="text-xs"
                      style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                    >
                      admin@apex-os.com
                    </p>
                    <div className="mt-2 flex items-center gap-1">
                      <Star
                        size={12}
                        className="text-amber-400"
                        fill="currentColor"
                      />
                      <span
                        className="text-xs"
                        style={{ color: isDark ? '#94a3b8' : '#64748b' }}
                      >
                        Administrator
                      </span>
                    </div>
                  </div>

                  {/* Menu Items */}
                  {[
                    { icon: User, label: 'Profile' },
                    { icon: Settings, label: 'Settings' },
                    { icon: CreditCard, label: 'Billing' },
                    { icon: HelpCircle, label: 'Help & Support' },
                  ].map((item) => {
                    const Icon = item.icon
                    return (
                      <button
                        key={item.label}
                        className="flex w-full items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-white/5"
                        style={{ color: isDark ? '#e2e8f0' : '#334155' }}
                        onClick={() => setProfileOpen(false)}
                      >
                        <Icon
                          size={16}
                          style={{ color: isDark ? '#64748b' : '#94a3b8' }}
                        />
                        {item.label}
                      </button>
                    )
                  })}

                  {/* Logout */}
                  <div
                    style={{
                      borderTop: isDark
                        ? '1px solid rgba(148, 163, 184, 0.1)'
                        : '1px solid rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    <button
                      className="flex w-full items-center gap-3 px-4 py-3 text-sm text-red-400 transition-colors hover:bg-red-500/10"
                      onClick={() => setProfileOpen(false)}
                    >
                      <LogOut size={16} />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* ── Page Content ─────────────────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
