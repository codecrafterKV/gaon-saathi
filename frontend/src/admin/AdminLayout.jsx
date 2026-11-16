import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, ClipboardList, Building2, ScrollText, Settings, LogOut, Menu, X, ExternalLink, UserRound } from 'lucide-react'
import Logo from '../components/Logo'
import { can, useAdmin } from './AdminAuth'

export default function AdminLayout() {
  const { user, logout } = useAdmin()
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  useEffect(() => setOpen(false), [location.pathname])

  const items = [
    { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/admin/complaints', label: 'Complaints', icon: ClipboardList },
    { to: '/admin/authorities', label: 'Authorities', icon: Building2 },
    ...(can(user, 'admin') ? [{ to: '/admin/audit', label: 'Audit Log', icon: ScrollText }] : []),
    { to: '/admin/settings', label: 'Settings', icon: Settings },
  ]

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center justify-between px-5">
        <Link to="/admin"><Logo inverted size="sm" /></Link>
        <button type="button" className="rounded-lg p-1.5 text-navy-200 hover:bg-white/10 lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
      </div>
      <p className="px-5 pb-2 pt-4 text-[11px] font-semibold uppercase tracking-wider text-navy-400">Team dashboard</p>
      <nav className="flex-1 space-y-1 px-3" aria-label="Admin">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}
            className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-white/10 text-white' : 'text-navy-200 hover:bg-white/5 hover:text-white'}`}>
            <item.icon className="h-[18px] w-[18px]" aria-hidden="true" /> {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 rounded-xl bg-white/5 p-3 ring-1 ring-white/10">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-white"><UserRound className="h-4 w-4" /></span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{user?.username}</p>
            <p className="truncate text-xs text-navy-300">{user?.role_label}</p>
          </div>
        </div>
        <button type="button" onClick={async () => { await logout(); navigate('/admin/login') }}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/15">
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>
      <Link to="/" className="mx-3 mb-4 flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-navy-300 hover:text-white">
        <ExternalLink className="h-3.5 w-3.5" /> View public website
      </Link>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-100/70">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 bg-navy-950 lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button type="button" className="absolute inset-0 bg-navy-950/60" onClick={() => setOpen(false)} aria-label="Close menu" />
          <aside className="relative h-full w-72 bg-navy-950">{sidebar}</aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:hidden">
          <button type="button" className="rounded-lg p-2 text-navy-900 hover:bg-slate-100" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <Logo size="sm" />
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export function AdminPageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-[28px]">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

const DATASET_KEY = 'gs-admin-dataset'
export function useDataset() {
  const [dataset, setDataset] = useState(() => {
    try { return localStorage.getItem(DATASET_KEY) || 'all' } catch { return 'all' }
  })
  const update = (value) => {
    setDataset(value)
    try { localStorage.setItem(DATASET_KEY, value) } catch { /* storage unavailable */ }
  }
  return [dataset, update]
}

export function DatasetToggle({ value, onChange }) {
  const options = [['all', 'All data'], ['live', 'Live only'], ['demo', 'Demo only']]
  return (
    <div className="inline-flex rounded-xl bg-white p-1 shadow-sm ring-1 ring-slate-200" role="radiogroup" aria-label="Data set">
      {options.map(([v, label]) => (
        <button key={v} type="button" role="radio" aria-checked={value === v} onClick={() => onChange(v)}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${value === v ? 'bg-navy-900 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>
          {label}
        </button>
      ))}
    </div>
  )
}
