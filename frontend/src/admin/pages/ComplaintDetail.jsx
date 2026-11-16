import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, CalendarDays, MapPin, FileText, Film, Download, ShieldCheck, ShieldAlert, Trash2, History,
  StickyNote, Send, CircleHelp, BadgeCheck, RefreshCw, Eye, MessageSquareDot, Lock, Image as ImageIcon, Building2,
} from 'lucide-react'
import { api } from '../../lib/api'
import { CATEGORY_MAP, STATUSES } from '../../lib/constants'
import { formatBytes, formatDate, formatDateTime } from '../../lib/format'
import { useDocumentTitle } from '../../lib/hooks'
import { Alert, DemoBadge, LoadingBlock, Modal, Spinner, StatusBadge, VerificationBadge } from '../../components/ui'
import { can, useAdmin } from '../AdminAuth'

export default function ComplaintDetail() {
  const { publicId } = useParams()
  useDocumentTitle(publicId)
  const { user } = useAdmin()
  const navigate = useNavigate()
  const [c, setC] = useState(null)
  const [authorities, setAuthorities] = useState([])
  const [channels, setChannels] = useState([])
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    setError('')
    api(`/api/admin/complaints/${encodeURIComponent(publicId)}`).then(setC).catch((err) => setError(err.message))
  }, [publicId])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    api('/api/admin/authorities?include_inactive=false').then((d) => { setAuthorities(d.items); setChannels(d.channels) }).catch(() => {})
  }, [])

  if (error && !c) return <div><BackLink /><Alert tone="error" className="mt-4">{error}</Alert></div>
  if (!c) return <LoadingBlock label="Loading complaint..." />
  const Category = CATEGORY_MAP[c.category]

  return (
    <div>
      <BackLink />
      <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-mono text-2xl font-extrabold tracking-tight">{c.complaint_id}</h1>
            {c.is_demo && <DemoBadge />}
            <StatusBadge status={c.status} size="lg" />
          </div>
          <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
            <span className="inline-flex items-center gap-1.5">{Category && <Category.icon className="h-4 w-4" />} {c.category_label}</span>
            <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-4 w-4" /> Submitted {formatDateTime(c.submitted_at)}</span>
            <span className="inline-flex items-center gap-1.5"><RefreshCw className="h-4 w-4" /> Updated {formatDateTime(c.updated_at)}</span>
          </p>
        </div>
        {can(user, 'admin') && (
          <button type="button" className="btn-secondary btn-sm self-start text-red-700 hover:border-red-300 hover:bg-red-50" onClick={() => setDeleting(true)}>
            <Trash2 className="h-4 w-4" /> Delete
          </button>
        )}
      </div>

      {c.info_requested && <Alert tone="warning" icon={CircleHelp} className="mt-5">More information was requested from the reporter. They will see the request on the tracking page.</Alert>}

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section className="card card-pad">
            <h2 className="text-base font-bold">Complaint details</h2>
            <dl className="mt-4 grid gap-4 sm:grid-cols-3">
              <Info label="Village" value={c.village} />
              <Info label="District" value={c.district} />
              <Info label="State" value={c.state} />
              <div className="sm:col-span-3"><Info label="Approximate location of the problem" value={c.approximate_location || 'Not provided'} icon={MapPin} /></div>
            </dl>
            <div className="mt-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Problem description</p>
              <p className="mt-2 whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-4 text-[15px] leading-relaxed text-navy-900 ring-1 ring-slate-200">{c.description}</p>
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400"><Lock className="h-3.5 w-3.5" /> Stored encrypted. Reporter identity was never collected.</p>
          </section>

          <section className="card card-pad">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold">Evidence ({c.evidence_count})</h2>
              {!can(user, 'evidence') && c.evidence_count > 0 && <span className="text-xs text-slate-500">Your role cannot open evidence.</span>}
            </div>
            {c.evidence_count === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No evidence was uploaded with this complaint.</p>
            ) : can(user, 'evidence') && (
              <ul className="mt-4 grid gap-4 sm:grid-cols-2">
                {c.evidence.map((e) => <EvidenceItem key={e.id} e={e} onOpen={() => setPreview(e)} />)}
              </ul>
            )}
          </section>

          <ActivityTimeline c={c} />
        </div>

        <div className="space-y-6">
          <PublicPreview c={c} />
          {can(user, 'write') ? (
            <ActionsPanel c={c} authorities={authorities} channels={channels} onUpdated={setC} />
          ) : (
            <Alert tone="info">Your role is read-only. Ask an administrator if you need to update complaints.</Alert>
          )}
          <VerificationSummary c={c} />
        </div>
      </div>

      <Modal open={!!preview} onClose={() => setPreview(null)} title={preview?.display_name || ''} wide>
        {preview?.media_kind === 'image' && <img src={`/api/admin/evidence/${preview.id}`} alt="Evidence" className="mx-auto max-h-[70vh] rounded-lg" />}
        {preview?.media_kind === 'video' && <video src={`/api/admin/evidence/${preview.id}`} controls className="mx-auto max-h-[70vh] w-full rounded-lg bg-black" />}
      </Modal>
      <DeleteModal open={deleting} onClose={() => setDeleting(false)} c={c} onDeleted={() => navigate('/admin/complaints', { replace: true })} />
    </div>
  )
}

function BackLink() {
  return <Link to="/admin/complaints" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-navy-900"><ArrowLeft className="h-4 w-4" /> All complaints</Link>
}

function Info({ label, value, icon: Icon }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 flex items-center gap-1.5 font-medium text-navy-900">{Icon && <Icon className="h-4 w-4 text-slate-400" />}{value}</dd>
    </div>
  )
}

function EvidenceItem({ e, onOpen }) {
  const src = `/api/admin/evidence/${e.id}`
  return (
    <li className="overflow-hidden rounded-xl border border-slate-200">
      <div className="flex h-40 items-center justify-center bg-slate-100">
        {e.media_kind === 'image' ? (
          <button type="button" onClick={onOpen} className="h-full w-full" aria-label={`View ${e.display_name}`}>
            <img src={src} alt={e.display_name} loading="lazy" className="h-full w-full object-cover" />
          </button>
        ) : e.media_kind === 'video' ? (
          <button type="button" onClick={onOpen} className="flex h-full w-full flex-col items-center justify-center gap-2 text-slate-500 hover:text-navy-900">
            <Film className="h-8 w-8" /><span className="text-xs font-medium">Play video</span>
          </button>
        ) : (
          <a href={`${src}?download=true`} className="flex h-full w-full flex-col items-center justify-center gap-2 text-slate-500 hover:text-navy-900">
            <FileText className="h-8 w-8" /><span className="text-xs font-medium">Download PDF</span>
          </a>
        )}
      </div>
      <div className="space-y-1.5 p-3 text-xs">
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 font-semibold text-navy-900">
            {e.media_kind === 'image' ? <ImageIcon className="h-3.5 w-3.5" /> : e.media_kind === 'video' ? <Film className="h-3.5 w-3.5" /> : <FileText className="h-3.5 w-3.5" />}
            {e.display_name}
          </span>
          <span className="text-slate-500">{formatBytes(e.size_bytes)}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {e.metadata_stripped
            ? <span className="inline-flex items-center gap-1 rounded bg-brand-50 px-1.5 py-0.5 font-medium text-brand-800"><ShieldCheck className="h-3 w-3" /> Metadata removed</span>
            : <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 font-medium text-amber-800"><ShieldAlert className="h-3 w-3" /> Metadata may remain</span>}
          <span className={`rounded px-1.5 py-0.5 font-medium ${e.scan_status === 'clean' ? 'bg-brand-50 text-brand-800' : e.scan_status === 'error' ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
            {e.scan_status === 'clean' ? 'Virus scan: clean' : e.scan_status === 'error' ? 'Virus scan failed' : 'Not virus scanned'}
          </span>
          {e.source === 'supplement' && <span className="rounded bg-sky-50 px-1.5 py-0.5 font-medium text-sky-800">Added later</span>}
        </div>
        <p className="truncate font-mono text-[10px] text-slate-400" title={`SHA-256 ${e.sha256}`}>SHA-256 {e.sha256.slice(0, 16)}...</p>
        <a href={`${src}?download=true`} className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"><Download className="h-3.5 w-3.5" /> Download</a>
      </div>
    </li>
  )
}

function ActivityTimeline({ c }) {
  const items = useMemo(() => {
    const list = [
      ...c.history.map((h) => ({ type: 'status', at: h.changed_at, key: `h${h.id}`, h })),
      ...c.notes.map((n) => ({ type: 'note', at: n.created_at, key: `n${n.id}`, n })),
      ...c.forwardings.map((f) => ({ type: 'forward', at: f.created_at, key: `f${f.id}`, f })),
    ]
    return list.sort((a, b) => new Date(b.at) - new Date(a.at))
  }, [c])
  const fallback = c.is_demo ? 'Demo data' : 'Former team member'
  return (
    <section className="card card-pad">
      <h2 className="flex items-center gap-2 text-base font-bold"><History className="h-5 w-5 text-slate-400" /> Activity and internal notes</h2>
      <p className="mt-1 text-xs text-slate-500">Internal only. The reporter sees only status names, dates and public messages.</p>
      <ol className="mt-5 space-y-5">
        {items.map((item) => (
          <li key={item.key} className="flex gap-3">
            <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${item.type === 'status' ? 'bg-navy-100 text-navy-700' : item.type === 'forward' ? 'bg-cyan-100 text-cyan-800' : item.n?.kind === 'reporter_update' ? 'bg-brand-100 text-brand-700' : 'bg-slate-100 text-slate-600'}`}>
              {item.type === 'status' ? <RefreshCw className="h-4 w-4" /> : item.type === 'forward' ? <Send className="h-4 w-4" /> : item.n.kind === 'reporter_update' ? <MessageSquareDot className="h-4 w-4" /> : <StickyNote className="h-4 w-4" />}
            </span>
            <div className="min-w-0 flex-1">
              {item.type === 'status' && (
                <>
                  <p className="text-sm font-semibold text-navy-900">
                    {item.h.from_status ? <>Status: {STATUSES[item.h.from_status]?.label} &rarr; {item.h.to_label}</> : 'Complaint received'}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-600">{item.h.internal_note}</p>
                  {item.h.public_message && <p className="mt-1.5 rounded-lg bg-navy-50 px-3 py-2 text-xs text-navy-800"><Eye className="mr-1 inline h-3.5 w-3.5" />Public message: {item.h.public_message}</p>}
                </>
              )}
              {item.type === 'note' && (
                <>
                  <p className="text-sm font-semibold text-navy-900">{item.n.kind_label}</p>
                  <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-600">{item.n.body}</p>
                </>
              )}
              {item.type === 'forward' && (
                <>
                  <p className="text-sm font-semibold text-navy-900">Forwarded to {item.f.authority_name}</p>
                  <dl className="mt-1 grid gap-x-4 gap-y-1 text-xs text-slate-600 sm:grid-cols-2">
                    <div><dt className="inline text-slate-400">Channel: </dt><dd className="inline">{item.f.channel_label}</dd></div>
                    <div><dt className="inline text-slate-400">Submitted on: </dt><dd className="inline">{formatDate(item.f.submitted_on)}</dd></div>
                    {item.f.reference_number && <div><dt className="inline text-slate-400">Reference / acknowledgement: </dt><dd className="inline font-mono">{item.f.reference_number}</dd></div>}
                  </dl>
                  {item.f.acknowledgement_details && <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600">{item.f.acknowledgement_details}</p>}
                </>
              )}
              <p className="mt-1 text-xs text-slate-400">
                {formatDateTime(item.at)} &middot; {item.type === 'status' ? (item.h.changed_by || (item.h.from_status ? fallback : 'Public form'))
                  : item.type === 'forward' ? (item.f.recorded_by || fallback) : (item.n.author || fallback)}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

function PublicPreview({ c }) {
  return (
    <section className="card card-pad">
      <h2 className="flex items-center gap-2 text-base font-bold"><Eye className="h-5 w-5 text-slate-400" /> What the reporter sees</h2>
      <div className="mt-3 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
        <StatusBadge status={c.status} />
        <p className="mt-2 text-sm text-navy-900">{c.public_message_effective}</p>
      </div>
      <p className="mt-2 text-xs text-slate-500">No description, evidence, notes or team names are ever shown publicly.</p>
    </section>
  )
}

function VerificationSummary({ c }) {
  return (
    <section className="card card-pad">
      <h2 className="flex items-center gap-2 text-base font-bold"><BadgeCheck className="h-5 w-5 text-slate-400" /> Verification</h2>
      <div className="mt-3"><VerificationBadge status={c.verification_status} /></div>
      {c.verification_findings && <p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">{c.verification_findings}</p>}
      {c.authority && (
        <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm ring-1 ring-slate-200">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500"><Building2 className="h-3.5 w-3.5" /> Responsible authority</p>
          <p className="mt-1 font-semibold text-navy-900">{c.authority.name}</p>
          {c.authority.grievance_channel && <p className="text-xs text-slate-500">{c.authority.grievance_channel}</p>}
        </div>
      )}
      {c.resolution_summary && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resolution summary</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600">{c.resolution_summary}</p>
        </div>
      )}
    </section>
  )
}

/* -------------------------------------------------------------------------- */
const TABS = [
  ['status', 'Status', RefreshCw],
  ['verify', 'Verify', BadgeCheck],
  ['forward', 'Forward', Send],
  ['info', 'Ask', CircleHelp],
  ['note', 'Note', StickyNote],
]

function ActionsPanel({ c, authorities, channels, onUpdated }) {
  const [tab, setTab] = useState('status')
  const terminal = ['resolved', 'rejected', 'closed'].includes(c.status)
  return (
    <section className="card overflow-hidden">
      <div className="grid grid-cols-5 border-b border-slate-200 bg-slate-50" role="tablist" aria-label="Complaint actions">
        {TABS.map(([key, label, Icon]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
            title={key === 'info' ? 'Ask the reporter for more information' : label}
            className={`flex flex-col items-center gap-1 border-b-2 px-1 py-2.5 text-[11px] font-semibold ${tab === key ? 'border-brand-600 bg-white text-navy-900' : 'border-transparent text-slate-500 hover:text-navy-900'}`}>
            <Icon className="h-4 w-4" aria-hidden="true" /> {label}
          </button>
        ))}
      </div>
      <div className="p-5" role="tabpanel">
        {tab === 'status' && <StatusForm c={c} onUpdated={onUpdated} />}
        {tab === 'verify' && <VerifyForm c={c} authorities={authorities} onUpdated={onUpdated} />}
        {tab === 'forward' && <ForwardForm c={c} authorities={authorities} channels={channels} onUpdated={onUpdated} />}
        {tab === 'info' && (terminal ? <Alert tone="info">Re-open the complaint (Status tab) before asking the reporter for more information.</Alert> : <InfoForm c={c} onUpdated={onUpdated} />)}
        {tab === 'note' && <NoteForm c={c} onUpdated={onUpdated} />}
      </div>
    </section>
  )
}

function useAction(c, onUpdated) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const run = async (path, body, method = 'POST', success = 'Saved.') => {
    setBusy(true); setError(''); setOk('')
    try {
      const updated = await api(`/api/admin/complaints/${c.complaint_id}/${path}`, { method, body })
      onUpdated(updated)
      setOk(success)
      return true
    } catch (err) {
      setError(err.message)
      return false
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, ok, run }
}

function Feedback({ error, ok }) {
  return <>{error && <Alert tone="error">{error}</Alert>}{ok && <Alert tone="success">{ok}</Alert>}</>
}

function SubmitButton({ busy, children }) {
  return <button type="submit" className="btn-primary w-full" disabled={busy}>{busy && <Spinner className="h-4 w-4" />}{children}</button>
}

function StatusForm({ c, onUpdated }) {
  const options = c.allowed_transitions
  const [to, setTo] = useState('')
  const [note, setNote] = useState('')
  const [message, setMessage] = useState('')
  const [summary, setSummary] = useState('')
  const { busy, error, ok, run } = useAction(c, onUpdated)
  const selected = options.find((o) => o.status === to)
  const submit = async (e) => {
    e.preventDefault()
    if (await run('status', { to_status: to, internal_note: note, public_message: message || null, resolution_summary: to === 'resolved' ? summary : null }, 'POST', 'Status updated.')) {
      setTo(''); setNote(''); setMessage(''); setSummary('')
    }
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <label htmlFor="to-status" className="label">New status</label>
        <select id="to-status" className="input" value={to} onChange={(e) => setTo(e.target.value)} required>
          <option value="">Choose...</option>
          {options.map((o) => <option key={o.status} value={o.status} disabled={o.requires_forwarding_record}>{o.label}{o.requires_forwarding_record ? ' (use Forward tab)' : ''}</option>)}
        </select>
      </div>
      {selected?.status === 'resolved' && (
        <div>
          <label htmlFor="resolution" className="label">Resolution summary *</label>
          <textarea id="resolution" rows={3} className="input" value={summary} onChange={(e) => setSummary(e.target.value)} minLength={20} required
            placeholder="What was done, by whom, and how was it confirmed?" />
          <p className="hint">Required. Only mark as resolved when you have a real, recorded update.</p>
        </div>
      )}
      <div>
        <label htmlFor="status-note" className="label">Internal explanation *</label>
        <textarea id="status-note" rows={3} className="input" value={note} onChange={(e) => setNote(e.target.value)} required minLength={5} placeholder="Why is the status changing? (team only)" />
      </div>
      <div>
        <label htmlFor="status-public" className="label">Public progress message <span className="font-normal text-slate-400">(optional)</span></label>
        <textarea id="status-public" rows={2} className="input" value={message} onChange={(e) => setMessage(e.target.value)} maxLength={500}
          placeholder="Shown to the reporter. Leave empty to use the standard message." />
        <p className="hint">Never include names, internal details or anything that could identify anyone.</p>
      </div>
      <Feedback error={error} ok={ok} />
      <SubmitButton busy={busy}>Update status</SubmitButton>
    </form>
  )
}

function VerifyForm({ c, authorities, onUpdated }) {
  const [status, setStatus] = useState(c.verification_status)
  const [findings, setFindings] = useState('')
  const [authority, setAuthority] = useState(c.authority?.id ? String(c.authority.id) : '')
  const { busy, error, ok, run } = useAction(c, onUpdated)
  const submit = async (e) => {
    e.preventDefault()
    if (await run('verification', { verification_status: status, findings: findings || null, authority_id: authority ? Number(authority) : null }, 'PUT', 'Verification saved.')) setFindings('')
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <label htmlFor="vs" className="label">Verification result</label>
        <select id="vs" className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="pending">Not yet verified</option>
          <option value="verified">Verified</option>
          <option value="unverified">Could not be verified</option>
          <option value="needs_more_info">Needs more information</option>
        </select>
      </div>
      <div>
        <label htmlFor="findings" className="label">Findings <span className="font-normal text-slate-400">(team only)</span></label>
        <textarea id="findings" rows={4} className="input" value={findings} onChange={(e) => setFindings(e.target.value)} placeholder="What did you check? What is missing?" />
      </div>
      <div>
        <label htmlFor="auth" className="label">Responsible department / authority</label>
        <select id="auth" className="input" value={authority} onChange={(e) => setAuthority(e.target.value)}>
          <option value="">Not identified yet</option>
          {authorities.map((a) => <option key={a.id} value={a.id}>{a.name}{a.is_demo ? ' [demo]' : ''}</option>)}
        </select>
        <p className="hint">Manage the list on the <Link to="/admin/authorities" className="underline">Authorities</Link> page.</p>
      </div>
      <Feedback error={error} ok={ok} />
      <SubmitButton busy={busy}>Save verification</SubmitButton>
    </form>
  )
}

function ForwardForm({ c, authorities, channels, onUpdated }) {
  const today = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState({ authority_id: c.authority?.id ? String(c.authority.id) : '', authority_name: '', channel: 'online_portal', submitted_on: today, reference_number: '', acknowledgement_details: '', internal_note: '', public_message: '' })
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const { busy, error, ok, run } = useAction(c, onUpdated)
  const canForward = c.status === 'forwarded' || c.allowed_transitions.some((t) => t.status === 'forwarded')
  if (!canForward) return <Alert tone="info">A complaint must be reviewed first (Under Review, Evidence Verification or Action in Progress) before it can be forwarded.</Alert>
  const submit = async (e) => {
    e.preventDefault()
    const body = { ...form, authority_id: form.authority_id ? Number(form.authority_id) : null }
    Object.keys(body).forEach((k) => { if (body[k] === '') body[k] = null })
    if (await run('forwardings', body, 'POST', 'Forwarding recorded.')) setForm((f) => ({ ...f, reference_number: '', acknowledgement_details: '', internal_note: '', public_message: '' }))
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <Alert tone="warning">Record this only <strong>after</strong> the complaint was actually submitted to the authority.</Alert>
      <div>
        <label htmlFor="fw-auth" className="label">Authority</label>
        <select id="fw-auth" className="input" value={form.authority_id} onChange={set('authority_id')}>
          <option value="">Other (type the name below)</option>
          {authorities.map((a) => <option key={a.id} value={a.id}>{a.name}{a.is_demo ? ' [demo]' : ''}</option>)}
        </select>
      </div>
      {!form.authority_id && <input className="input" placeholder="Authority / office name" value={form.authority_name} onChange={set('authority_name')} aria-label="Authority name" />}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="fw-channel" className="label">Channel</label>
          <select id="fw-channel" className="input" value={form.channel} onChange={set('channel')}>
            {channels.map((ch) => <option key={ch.value} value={ch.value}>{ch.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="fw-date" className="label">Submitted on</label>
          <input id="fw-date" type="date" className="input" max={today} value={form.submitted_on} onChange={set('submitted_on')} required />
        </div>
      </div>
      <div>
        <label htmlFor="fw-ref" className="label">Acknowledgement / reference number</label>
        <input id="fw-ref" className="input font-mono" value={form.reference_number} onChange={set('reference_number')} />
      </div>
      <div>
        <label htmlFor="fw-ack" className="label">Submission details</label>
        <textarea id="fw-ack" rows={2} className="input" value={form.acknowledgement_details} onChange={set('acknowledgement_details')} placeholder="Required if there is no reference number" />
      </div>
      <div>
        <label htmlFor="fw-note" className="label">Internal explanation *</label>
        <textarea id="fw-note" rows={2} className="input" value={form.internal_note} onChange={set('internal_note')} required minLength={5} />
      </div>
      <div>
        <label htmlFor="fw-public" className="label">Public message <span className="font-normal text-slate-400">(optional)</span></label>
        <textarea id="fw-public" rows={2} className="input" value={form.public_message} onChange={set('public_message')} maxLength={500} />
      </div>
      <Feedback error={error} ok={ok} />
      <SubmitButton busy={busy}>Record forwarding</SubmitButton>
    </form>
  )
}

function InfoForm({ c, onUpdated }) {
  const [message, setMessage] = useState('Please add more details or a photo of the problem, if it is safe for you to do so.')
  const [note, setNote] = useState('')
  const { busy, error, ok, run } = useAction(c, onUpdated)
  const submit = async (e) => {
    e.preventDefault()
    if (await run('request-info', { public_message: message, internal_note: note }, 'POST', 'Request sent. The reporter will see it when they track the complaint.')) setNote('')
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <p className="text-sm text-slate-600">We cannot contact the reporter. They will see this message on the tracking page and can add information anonymously.</p>
      <div>
        <label htmlFor="info-msg" className="label">Message to the reporter (public)</label>
        <textarea id="info-msg" rows={3} className="input" value={message} onChange={(e) => setMessage(e.target.value)} minLength={10} maxLength={500} required />
      </div>
      <div>
        <label htmlFor="info-note" className="label">Internal reason *</label>
        <textarea id="info-note" rows={2} className="input" value={note} onChange={(e) => setNote(e.target.value)} minLength={5} required />
      </div>
      <Feedback error={error} ok={ok} />
      <SubmitButton busy={busy}>Request more information</SubmitButton>
    </form>
  )
}

function NoteForm({ c, onUpdated }) {
  const [kind, setKind] = useState('internal_note')
  const [body, setBody] = useState('')
  const { busy, error, ok, run } = useAction(c, onUpdated)
  const submit = async (e) => {
    e.preventDefault()
    if (await run('notes', { kind, body }, 'POST', 'Note added.')) setBody('')
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <label htmlFor="note-kind" className="label">Type</label>
        <select id="note-kind" className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="internal_note">Internal note</option>
          <option value="follow_up">Follow-up update</option>
        </select>
      </div>
      <div>
        <label htmlFor="note-body" className="label">Note (team only)</label>
        <textarea id="note-body" rows={4} className="input" value={body} onChange={(e) => setBody(e.target.value)} required minLength={2} />
      </div>
      <Feedback error={error} ok={ok} />
      <SubmitButton busy={busy}>Add note</SubmitButton>
    </form>
  )
}

function DeleteModal({ open, onClose, c, onDeleted }) {
  const [reason, setReason] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async () => {
    setBusy(true); setError('')
    try {
      await api(`/api/admin/complaints/${c.complaint_id}/delete`, { method: 'POST', body: { reason, confirm_id: confirm } })
      onDeleted()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Delete complaint permanently"
      footer={<><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="button" className="btn-danger" disabled={busy || confirm.trim().toUpperCase() !== c.complaint_id || reason.trim().length < 5} onClick={submit}>
          {busy && <Spinner className="h-4 w-4" />} Delete forever</button></>}>
      <div className="space-y-4">
        <Alert tone="error">This permanently deletes the complaint, its history, notes and all evidence files. It cannot be undone. The deletion is recorded in the audit log.</Alert>
        <div>
          <label htmlFor="del-reason" className="label">Reason</label>
          <input id="del-reason" className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="For example: spam, duplicate, abusive content" />
        </div>
        <div>
          <label htmlFor="del-confirm" className="label">Type <span className="font-mono">{c.complaint_id}</span> to confirm</label>
          <input id="del-confirm" className="input font-mono" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" />
        </div>
        {error && <Alert tone="error">{error}</Alert>}
      </div>
    </Modal>
  )
}
