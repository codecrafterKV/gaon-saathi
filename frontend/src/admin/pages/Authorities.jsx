import { useCallback, useEffect, useState } from 'react'
import { Building2, ExternalLink, Pencil, Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { STATES } from '../../lib/constants'
import { useDocumentTitle } from '../../lib/hooks'
import { Alert, DemoBadge, EmptyState, LoadingBlock, Modal, Spinner } from '../../components/ui'
import { AdminPageHeader } from '../AdminLayout'
import { can, useAdmin } from '../AdminAuth'

const EMPTY = { name: '', department: '', level: 'district', state: '', district: '', grievance_channel: '', website: '', office_contact: '', notes: '', is_active: true }

export default function Authorities() {
  useDocumentTitle('Authorities')
  const { user } = useAdmin()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)

  const load = useCallback(() => {
    api('/api/admin/authorities').then(setData).catch((err) => setError(err.message))
  }, [])
  useEffect(() => { load() }, [load])

  return (
    <div>
      <AdminPageHeader title="Authorities and departments"
        description="Government offices and official grievance channels that complaints can be forwarded to."
        actions={can(user, 'write') && <button type="button" className="btn-primary btn-sm" onClick={() => setEditing({ ...EMPTY })}><Plus className="h-4 w-4" /> Add authority</button>} />
      <Alert tone="info" className="mb-5">Keep these records accurate. Always confirm the current procedure on the official website before forwarding a complaint.</Alert>
      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      {!data ? <LoadingBlock /> : data.items.length === 0 ? (
        <div className="card"><EmptyState icon={Building2} title="No authorities yet">Add the offices and grievance channels your team works with.</EmptyState></div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((a) => (
            <article key={a.id} className={`card card-pad flex flex-col ${a.is_active ? '' : 'opacity-60'}`}>
              <div className="flex items-start justify-between gap-2">
                <span className="rounded-lg bg-navy-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-navy-700">{a.level_label}</span>
                <div className="flex items-center gap-1.5">
                  {a.is_demo && <DemoBadge />}
                  {!a.is_active && <span className="text-xs text-slate-500">Inactive</span>}
                </div>
              </div>
              <h2 className="mt-3 text-base font-bold leading-snug">{a.name}</h2>
              {a.department && <p className="text-sm text-slate-500">{a.department}</p>}
              <dl className="mt-3 flex-1 space-y-1 text-sm text-slate-600">
                {(a.district || a.state) && <div><dt className="inline text-slate-400">Area: </dt><dd className="inline">{[a.district, a.state].filter(Boolean).join(', ')}</dd></div>}
                {a.grievance_channel && <div><dt className="inline text-slate-400">Channel: </dt><dd className="inline">{a.grievance_channel}</dd></div>}
                {a.office_contact && <div><dt className="inline text-slate-400">Office: </dt><dd className="inline">{a.office_contact}</dd></div>}
                {a.notes && <p className="pt-1 text-xs text-slate-500">{a.notes}</p>}
              </dl>
              <div className="mt-4 flex items-center justify-between">
                {a.website ? <a href={a.website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">Website <ExternalLink className="h-3.5 w-3.5" /></a> : <span />}
                {can(user, 'write') && <button type="button" className="btn-ghost btn-sm" onClick={() => setEditing({ ...EMPTY, ...Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v ?? ''])) })}><Pencil className="h-3.5 w-3.5" /> Edit</button>}
              </div>
            </article>
          ))}
        </div>
      )}
      {editing && <AuthorityModal initial={editing} levels={data?.levels || []} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load() }} />}
    </div>
  )
}

function AuthorityModal({ initial, levels, onClose, onSaved }) {
  const [form, setForm] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  const save = async () => {
    setBusy(true); setError('')
    const body = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, typeof form[k] === 'string' ? (form[k].trim() || null) : form[k]]))
    body.name = form.name.trim()
    body.level = form.level
    try {
      await api(initial.id ? `/api/admin/authorities/${initial.id}` : '/api/admin/authorities', { method: initial.id ? 'PUT' : 'POST', body })
      onSaved()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return (
    <Modal open onClose={onClose} title={initial.id ? 'Edit authority' : 'Add authority'} wide
      footer={<><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button type="button" className="btn-primary" onClick={save} disabled={busy || form.name.trim().length < 2}>{busy && <Spinner className="h-4 w-4" />} Save</button></>}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><label htmlFor="a-name" className="label">Name *</label><input id="a-name" className="input" value={form.name} onChange={set('name')} /></div>
        <div><label htmlFor="a-dept" className="label">Department</label><input id="a-dept" className="input" value={form.department} onChange={set('department')} /></div>
        <div><label htmlFor="a-level" className="label">Level</label>
          <select id="a-level" className="input" value={form.level} onChange={set('level')}>{levels.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select></div>
        <div><label htmlFor="a-state" className="label">State</label>
          <select id="a-state" className="input" value={form.state} onChange={set('state')}><option value="">Any / national</option>{STATES.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
        <div><label htmlFor="a-district" className="label">District</label><input id="a-district" className="input" value={form.district} onChange={set('district')} /></div>
        <div><label htmlFor="a-channel" className="label">Grievance channel</label><input id="a-channel" className="input" value={form.grievance_channel} onChange={set('grievance_channel')} placeholder="e.g. Online portal, written application" /></div>
        <div><label htmlFor="a-web" className="label">Official website</label><input id="a-web" className="input" value={form.website} onChange={set('website')} placeholder="https://" /></div>
        <div className="sm:col-span-2"><label htmlFor="a-contact" className="label">Office address / public contact</label><input id="a-contact" className="input" value={form.office_contact} onChange={set('office_contact')} /></div>
        <div className="sm:col-span-2"><label htmlFor="a-notes" className="label">Notes</label><textarea id="a-notes" rows={3} className="input" value={form.notes} onChange={set('notes')} /></div>
        <label className="flex items-center gap-2 text-sm font-medium text-navy-900"><input type="checkbox" className="h-4 w-4 accent-brand-600" checked={form.is_active} onChange={set('is_active')} /> Active</label>
      </div>
      {error && <Alert tone="error" className="mt-4">{error}</Alert>}
    </Modal>
  )
}
