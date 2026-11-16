import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Inbox, Search, FileSearch, Hourglass, Send, CircleCheckBig, Archive, Layers, Download, RefreshCw,
  MessageSquareDot, CircleHelp, Paperclip, ArrowRight, Clock,
} from 'lucide-react'
import { api } from '../../lib/api'
import { formatDate, formatNumber } from '../../lib/format'
import { useDocumentTitle } from '../../lib/hooks'
import { Alert, DemoBadge, LoadingBlock, StatusBadge } from '../../components/ui'
import { AdminPageHeader, DatasetToggle, useDataset } from '../AdminLayout'
import { can, useAdmin } from '../AdminAuth'
import { CategoryChart, StatusChart, TimelineChart, VillageChart } from '../charts'

export default function Dashboard() {
  useDocumentTitle('Dashboard')
  const { user } = useAdmin()
  const [dataset, setDataset] = useDataset()
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    Promise.all([
      api(`/api/admin/stats?dataset=${dataset}`, { signal: controller.signal }),
      api(`/api/admin/complaints?dataset=${dataset}&page_size=6&sort=newest`, { signal: controller.signal }),
    ]).then(([s, list]) => { setStats(s); setRecent(list.items) })
      .catch((err) => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [dataset, reload])

  const count = (status) => stats?.by_status.find((s) => s.status === status)?.count ?? 0
  const tiles = stats ? [
    { label: 'Total complaints received', value: stats.total, icon: Layers, tone: 'bg-navy-900 text-white', to: '' },
    { label: 'New complaints', value: count('received'), icon: Inbox, tone: 'bg-sky-50 text-sky-700', to: 'status=received' },
    { label: 'Under review', value: count('under_review'), icon: Search, tone: 'bg-indigo-50 text-indigo-700', to: 'status=under_review' },
    { label: 'Evidence verification', value: count('evidence_verification'), icon: FileSearch, tone: 'bg-violet-50 text-violet-700', to: 'status=evidence_verification' },
    { label: 'Action in progress', value: count('action_in_progress'), icon: Hourglass, tone: 'bg-amber-50 text-amber-700', to: 'status=action_in_progress' },
    { label: 'Forwarded to authorities', value: count('forwarded'), icon: Send, tone: 'bg-cyan-50 text-cyan-700', to: 'status=forwarded' },
    { label: 'Resolved complaints', value: count('resolved'), icon: CircleCheckBig, tone: 'bg-brand-50 text-brand-700', to: 'status=resolved' },
    { label: 'Rejected / closed', value: count('rejected') + count('closed'), icon: Archive, tone: 'bg-slate-100 text-slate-600', to: 'status=rejected' },
  ] : []

  return (
    <div>
      <AdminPageHeader
        title={`Welcome, ${user?.username}`}
        description="Overview of complaints, calculated live from the database."
        actions={<>
          <DatasetToggle value={dataset} onChange={setDataset} />
          <button type="button" className="btn-secondary btn-sm" onClick={() => setReload((n) => n + 1)} aria-label="Refresh"><RefreshCw className="h-4 w-4" /></button>
          {can(user, 'export') && (
            <a className="btn-secondary btn-sm" href={`/api/admin/export/statistics.csv?dataset=${dataset}`}><Download className="h-4 w-4" /> Statistics CSV</a>
          )}
        </>}
      />
      {dataset !== 'live' && stats && (
        <p className="-mt-3 mb-5 text-xs text-slate-500">
          {dataset === 'demo' ? 'Showing DEMO DATA only.' : 'Showing live complaints together with any DEMO DATA (marked with a Demo badge).'}
        </p>
      )}
      {error && <Alert tone="error" className="mb-6">{error}</Alert>}
      {loading && !stats ? <LoadingBlock label="Loading dashboard..." /> : stats && (
        <div className={loading ? 'opacity-60 transition' : 'transition'}>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {tiles.map((t) => (
              <Link key={t.label} to={`/admin/complaints${t.to ? `?${t.to}` : ''}`}
                className={`group rounded-2xl p-4 shadow-card ring-1 transition hover:-translate-y-0.5 hover:shadow-lift sm:p-5 ${t.tone.includes('navy-900') ? 'bg-navy-900 ring-navy-900' : 'bg-white ring-slate-200/80'}`}>
                <div className="flex items-start justify-between gap-2">
                  <p className={`text-xs font-medium leading-snug sm:text-sm ${t.tone.includes('navy-900') ? 'text-navy-200' : 'text-slate-500'}`}>{t.label}</p>
                  <span className={`rounded-lg p-1.5 ${t.tone.includes('navy-900') ? 'bg-white/10 text-brand-300' : t.tone}`}><t.icon className="h-4 w-4" aria-hidden="true" /></span>
                </div>
                <p className={`mt-3 font-display text-3xl font-extrabold tabular-nums ${t.tone.includes('navy-900') ? 'text-white' : 'text-navy-900'}`}>{formatNumber(t.value)}</p>
              </Link>
            ))}
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <MiniStat icon={MessageSquareDot} label="New info from reporters" value={stats.unread_updates} hint="Unread reporter updates" />
            <MiniStat icon={CircleHelp} label="Waiting for reporter" value={stats.info_requested} hint="More information requested" />
            <MiniStat icon={Clock} label="Median days to resolve" value={stats.median_days_to_resolve ?? '-'} hint={`${formatNumber(stats.with_evidence)} complaints have evidence`} />
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <TimelineChart daily={stats.daily} monthly={stats.monthly} />
            <CategoryChart data={stats.by_category} />
            <StatusChart data={stats.by_status} />
            <VillageChart data={stats.top_villages} distinct={stats.distinct_villages} />
          </div>

          <section className="card mt-6 overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <h2 className="text-base font-bold">Latest complaints</h2>
              <Link to="/admin/complaints" className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">View all <ArrowRight className="h-4 w-4" /></Link>
            </div>
            {recent.length === 0 ? (
              <p className="px-5 py-10 text-center text-sm text-slate-500">No complaints yet. New complaints will appear here.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {recent.map((c) => (
                  <li key={c.complaint_id}>
                    <Link to={`/admin/complaints/${c.complaint_id}`} className="flex flex-col gap-2 px-5 py-3.5 hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="flex flex-wrap items-center gap-2 font-mono text-sm font-semibold text-navy-900">
                          {c.complaint_id} {c.is_demo && <DemoBadge />}
                          {c.has_evidence && <Paperclip className="h-3.5 w-3.5 text-slate-400" aria-label="Has evidence" />}
                        </p>
                        <p className="truncate text-sm text-slate-500">{c.category_label} &middot; {c.village}, {c.district}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-slate-400">{formatDate(c.submitted_at)}</span>
                        <StatusBadge status={c.status} short />
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

function MiniStat({ icon: Icon, label, value, hint }) {
  return (
    <div className="card flex items-center gap-4 p-4">
      <span className="rounded-xl bg-slate-100 p-2.5 text-navy-700"><Icon className="h-5 w-5" aria-hidden="true" /></span>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="font-display text-xl font-extrabold tabular-nums text-navy-900">{typeof value === 'number' ? formatNumber(value) : value}</p>
        <p className="text-[11px] text-slate-400">{hint}</p>
      </div>
    </div>
  )
}
