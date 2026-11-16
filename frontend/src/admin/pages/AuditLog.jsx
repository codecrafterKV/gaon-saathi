import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, ScrollText } from 'lucide-react'
import { api } from '../../lib/api'
import { formatDateTime, formatNumber } from '../../lib/format'
import { useDocumentTitle } from '../../lib/hooks'
import { Alert, EmptyState, LoadingBlock } from '../../components/ui'
import { AdminPageHeader } from '../AdminLayout'

export default function AuditLog() {
  useDocumentTitle('Audit Log')
  const [data, setData] = useState(null)
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => {
    const q = new URLSearchParams({ page: String(page) })
    if (action) q.set('action', action)
    api(`/api/admin/audit-logs?${q}`).then(setData).catch((err) => setError(err.message))
  }, [action, page])

  return (
    <div>
      <AdminPageHeader title="Audit log" description="Every important administrator action, newest first. Complaint text and evidence are never recorded here."
        actions={data && (
          <select className="input !w-auto text-sm" value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} aria-label="Filter by action">
            <option value="">All actions</option>
            {data.actions.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        )} />
      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      <div className="card overflow-hidden">
        {!data ? <LoadingBlock /> : data.items.length === 0 ? <EmptyState icon={ScrollText} title="No audit entries" /> : (
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Target</th><th>Details</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((r) => (
                  <tr key={r.id}>
                    <td className="text-slate-500">{formatDateTime(r.created_at)}</td>
                    <td className="font-medium text-navy-900">{r.actor || <span className="text-slate-400">-</span>}</td>
                    <td><code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-navy-800">{r.action}</code></td>
                    <td>{r.target_ref ? (r.target_type === 'complaint'
                      ? <Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={`/admin/complaints/${r.target_ref}`}>{r.target_ref}</Link>
                      : <span className="text-xs">{r.target_type}: {r.target_ref}</span>) : '-'}</td>
                    <td className="max-w-xs truncate text-xs text-slate-500" title={r.details ? JSON.stringify(r.details) : ''}>
                      {r.details ? Object.entries(r.details).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' -> ') : v}`).join(', ') : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm">
            <span className="text-slate-500">{formatNumber(data.total)} entries &middot; page {data.page} of {data.pages}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft className="h-4 w-4" /> Newer</button>
              <button type="button" className="btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Older <ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
