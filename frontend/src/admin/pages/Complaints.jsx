import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Download, Eye, FilterX, Inbox, Search, MessageSquareDot, CircleHelp } from 'lucide-react'
import { api } from '../../lib/api'
import { CATEGORIES, STATUSES } from '../../lib/constants'
import { formatDate, formatNumber } from '../../lib/format'
import { useDocumentTitle } from '../../lib/hooks'
import { Alert, DemoBadge, EmptyState, LoadingBlock, StatusBadge } from '../../components/ui'
import { AdminPageHeader, DatasetToggle, useDataset } from '../AdminLayout'
import { can, useAdmin } from '../AdminAuth'

const FILTER_KEYS = ['search', 'category', 'status', 'district', 'village', 'date_from', 'date_to', 'has_evidence', 'sort', 'page']

export default function Complaints() {
  useDocumentTitle('Complaints')
  const { user } = useAdmin()
  const [params, setParams] = useSearchParams()
  const [dataset, setDataset] = useDataset()
  const [data, setData] = useState(null)
  const [filters, setFilters] = useState({ districts: [], villages: [] })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [searchInput, setSearchInput] = useState(params.get('search') || '')

  const query = useMemo(() => {
    const q = new URLSearchParams({ dataset, page_size: '20' })
    FILTER_KEYS.forEach((k) => { if (params.get(k)) q.set(k, params.get(k)) })
    return q.toString()
  }, [params, dataset])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    api(`/api/admin/complaints?${query}`, { signal: controller.signal })
      .then((d) => { setData(d); setError('') })
      .catch((err) => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [query])

  useEffect(() => {
    api(`/api/admin/complaints/filters?dataset=${dataset}`).then(setFilters).catch(() => {})
  }, [dataset])

  // Debounced search box.
  useEffect(() => {
    const t = setTimeout(() => {
      if ((params.get('search') || '') !== searchInput) setParam('search', searchInput)
    }, 350)
    return () => clearTimeout(t)
  }, [searchInput]) // eslint-disable-line react-hooks/exhaustive-deps

  function setParam(key, value) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value); else next.delete(key)
    if (key !== 'page') next.delete('page')
    setParams(next, { replace: true })
  }

  const district = params.get('district') || ''
  const villages = filters.villages.filter((v) => !district || v.district === district)
  const activeFilters = FILTER_KEYS.filter((k) => !['page', 'sort'].includes(k) && params.get(k)).length
  const page = Number(params.get('page') || 1)

  return (
    <div>
      <AdminPageHeader title="Complaint management" description="Search, filter and open complaints."
        actions={<>
          <DatasetToggle value={dataset} onChange={(v) => { setDataset(v); setParam('page', '') }} />
          {can(user, 'export') && <a className="btn-secondary btn-sm" href={`/api/admin/export/complaints.csv?dataset=${dataset}`}><Download className="h-4 w-4" /> Register CSV</a>}
        </>} />

      <div className="card p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative sm:col-span-2">
            <label htmlFor="search" className="sr-only">Search</label>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="search" className="input pl-9" placeholder="Search complaint ID, village or district" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} />
          </div>
          <Select label="Category" value={params.get('category') || ''} onChange={(v) => setParam('category', v)}
            options={CATEGORIES.map((c) => [c.value, c.label])} />
          <Select label="Status" value={params.get('status') || ''} onChange={(v) => setParam('status', v)}
            options={[['open', 'All open complaints'], ...Object.entries(STATUSES).map(([k, s]) => [k, s.label])]} />
          <Select label="District" value={district} onChange={(v) => { const n = new URLSearchParams(params); if (v) n.set('district', v); else n.delete('district'); n.delete('village'); n.delete('page'); setParams(n, { replace: true }) }}
            options={filters.districts.map((d) => [d.district, `${d.district} (${d.state})`])} />
          <Select label="Village" value={params.get('village') || ''} onChange={(v) => setParam('village', v)}
            options={villages.map((v) => [v.village, district ? v.village : `${v.village} (${v.district})`])} />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="date_from" className="sr-only">From date</label>
              <input id="date_from" type="date" className="input text-sm" value={params.get('date_from') || ''} onChange={(e) => setParam('date_from', e.target.value)} title="Submitted from" />
            </div>
            <div>
              <label htmlFor="date_to" className="sr-only">To date</label>
              <input id="date_to" type="date" className="input text-sm" value={params.get('date_to') || ''} onChange={(e) => setParam('date_to', e.target.value)} title="Submitted until" />
            </div>
          </div>
          <Select label="Evidence" value={params.get('has_evidence') || ''} onChange={(v) => setParam('has_evidence', v)}
            options={[['true', 'With evidence'], ['false', 'Without evidence']]} placeholder="Evidence: any" />
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
          <p className="text-sm text-slate-500" aria-live="polite">
            {data ? <><strong className="text-navy-900">{formatNumber(data.total)}</strong> complaint{data.total === 1 ? '' : 's'} found</> : ' '}
          </p>
          <div className="flex items-center gap-2">
            <label htmlFor="sort" className="text-xs text-slate-500">Sort</label>
            <select id="sort" className="input !w-auto py-1.5 text-sm" value={params.get('sort') || 'newest'} onChange={(e) => setParam('sort', e.target.value)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="updated">Recently updated</option>
              <option value="status">Status</option>
              <option value="category">Category</option>
              <option value="village">Village</option>
            </select>
            {activeFilters > 0 && (
              <button type="button" className="btn-ghost btn-sm" onClick={() => { setSearchInput(''); setParams({}, { replace: true }) }}>
                <FilterX className="h-4 w-4" /> Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      <div className="card mt-4 overflow-hidden">
        {loading && !data ? <LoadingBlock /> : data && data.items.length === 0 ? (
          <EmptyState icon={Inbox} title={activeFilters ? 'No complaints match these filters' : 'No complaints yet'}>
            {activeFilters ? 'Try removing some filters.' : 'Complaints submitted through the public website will appear here.'}
          </EmptyState>
        ) : data && (
          <div className={`overflow-x-auto ${loading ? 'opacity-60' : ''}`}>
            <table className="table-base">
              <thead>
                <tr>
                  <th>Complaint ID</th><th>Category</th><th>Village</th><th>District</th><th>Submitted</th><th>Status</th><th>Evidence</th><th><span className="sr-only">Action</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {data.items.map((c) => (
                  <tr key={c.complaint_id} className="hover:bg-slate-50">
                    <td>
                      <div className="flex items-center gap-2">
                        <Link to={`/admin/complaints/${c.complaint_id}`} className="font-mono text-[13px] font-semibold text-navy-900 hover:text-brand-700">{c.complaint_id}</Link>
                        {c.is_demo && <DemoBadge />}
                        {c.has_unread_update && <MessageSquareDot className="h-4 w-4 text-brand-600" aria-label="New information from reporter" />}
                        {c.info_requested && <CircleHelp className="h-4 w-4 text-amber-600" aria-label="Waiting for reporter" />}
                      </div>
                    </td>
                    <td className="max-w-[220px] truncate" title={c.category_label}>{c.category_label}</td>
                    <td>{c.village}</td>
                    <td>{c.district}</td>
                    <td>{formatDate(c.submitted_at)}</td>
                    <td><StatusBadge status={c.status} short /></td>
                    <td>{c.has_evidence ? <span className="font-medium text-brand-700">Yes</span> : <span className="text-slate-400">No</span>}</td>
                    <td className="text-right">
                      <Link to={`/admin/complaints/${c.complaint_id}`} className="btn-secondary btn-sm"><Eye className="h-4 w-4" /> Open</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm">
            <span className="text-slate-500">Page {data.page} of {data.pages}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => setParam('page', String(page - 1))}><ChevronLeft className="h-4 w-4" /> Previous</button>
              <button type="button" className="btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => setParam('page', String(page + 1))}>Next <ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Select({ label, value, onChange, options, placeholder }) {
  const id = `f-${label.toLowerCase()}`
  return (
    <div>
      <label htmlFor={id} className="sr-only">{label}</label>
      <select id={id} className="input text-sm" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{placeholder || `${label}: all`}</option>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  )
}
