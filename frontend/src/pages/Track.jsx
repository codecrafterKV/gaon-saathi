import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, KeyRound, MessageSquarePlus, Paperclip, Search, Send, ShieldAlert, Trash2, CircleAlert, Hash } from 'lucide-react'
import { api, uploadForm } from '../lib/api'
import { STATUSES } from '../lib/constants'
import { formatBytes, formatComplaintIdInput, formatDate, formatTrackingInput } from '../lib/format'
import { getSolvedChallenge } from '../lib/pow'
import { cleanImage, detectPersonalInfo, genericName } from '../lib/privacy'
import { useDocumentTitle, usePublicConfig } from '../lib/hooks'
import { Alert, DemoBadge, PageHero, Spinner, StatusBadge } from '../components/ui'

export default function Track() {
  useDocumentTitle('Track Complaint')
  const [complaintId, setComplaintId] = useState('')
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function lookup(e) {
    e?.preventDefault()
    setError('')
    if (!complaintId.trim() || token.replace(/-/g, '').length < 16) {
      setError('Please enter your Complaint ID and the full 16-character Tracking Code.')
      return
    }
    setLoading(true)
    try {
      setResult(await api('/api/public/track', { method: 'POST', body: { complaint_id: complaintId.trim(), tracking_token: token } }))
    } catch (err) {
      setResult(null)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-slate-50 pb-20">
      <PageHero eyebrow="Track complaint" title="Check the status of your complaint"
        lead="Enter your Complaint ID and secret Tracking Code. You do not need an account." />
      <div className="container-page -mt-8">
        <div className="mx-auto max-w-3xl">
          <form onSubmit={lookup} className="card card-pad relative" noValidate>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="complaint-id" className="label">Complaint ID</label>
                <div className="relative">
                  <Hash className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                  <input id="complaint-id" className="input pl-10 font-mono uppercase tracking-wide" placeholder="GS-2026-XXXXXXXX"
                    value={complaintId} onChange={(e) => setComplaintId(formatComplaintIdInput(e.target.value))} autoComplete="off" spellCheck={false} />
                </div>
              </div>
              <div>
                <label htmlFor="tracking-token" className="label">Secret Tracking Code</label>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                  <input id="tracking-token" className="input pl-10 font-mono uppercase tracking-wide" placeholder="XXXX-XXXX-XXXX-XXXX"
                    value={token} onChange={(e) => setToken(formatTrackingInput(e.target.value))} autoComplete="off" spellCheck={false} />
                </div>
              </div>
            </div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-slate-500">Both codes were shown once when you submitted your complaint.</p>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? <><Spinner className="h-4 w-4" /> Checking...</> : <><Search className="h-4 w-4" /> Check status</>}
              </button>
            </div>
            {error && <Alert tone="error" className="mt-5">{error}</Alert>}
          </form>

          {result && <TrackResult data={result} complaintId={complaintId} token={token} onRefresh={lookup} />}

          {!result && (
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="card card-pad">
                <h2 className="text-base font-bold">Lost your codes?</h2>
                <p className="mt-1.5 text-sm text-slate-600">
                  We cannot recover them because we do not know who you are. You can <Link to="/report" className="font-medium text-brand-700 underline">report the problem again</Link> and mention it was reported before.
                </p>
              </div>
              <div className="card card-pad">
                <h2 className="text-base font-bold">What do the statuses mean?</h2>
                <p className="mt-1.5 text-sm text-slate-600">See <Link to="/how-it-works#statuses" className="font-medium text-brand-700 underline">How It Works</Link> for an explanation of every status.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TrackResult({ data, complaintId, token, onRefresh }) {
  const offPath = ['rejected', 'closed'].includes(data.status)
  const stepIndex = data.progress_steps.findIndex((s) => s.status === data.status)
  const reached = new Set(data.timeline.map((t) => t.status))
  return (
    <div className="mt-6 space-y-6" aria-live="polite">
      <section className="card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-slate-200 p-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Complaint ID {data.is_demo && <DemoBadge />}</p>
            <p className="mt-1 font-mono text-xl font-bold tracking-wide text-navy-900">{data.complaint_id}</p>
            <p className="mt-1 text-sm text-slate-600">{data.category_label}</p>
          </div>
          <StatusBadge status={data.status} size="lg" />
        </div>
        <dl className="grid grid-cols-2 gap-4 px-6 py-4 text-sm sm:grid-cols-3">
          <div><dt className="text-xs text-slate-500">Submitted on</dt><dd className="font-semibold text-navy-900">{formatDate(data.submitted_on)}</dd></div>
          <div><dt className="text-xs text-slate-500">Last updated</dt><dd className="font-semibold text-navy-900">{formatDate(data.last_updated)}</dd></div>
          <div className="col-span-2 sm:col-span-1"><dt className="text-xs text-slate-500">Current status</dt><dd className="font-semibold text-navy-900">{data.status_label}</dd></div>
        </dl>
        <div className="mx-6 mb-6 rounded-2xl bg-navy-50 p-4 ring-1 ring-navy-100">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-600">Progress update</p>
          <p className="mt-1 text-navy-900">{data.progress_message}</p>
        </div>
      </section>

      <section className="card card-pad">
        <h2 className="text-lg font-bold">Progress</h2>
        {offPath && (
          <Alert tone={data.status === 'rejected' ? 'error' : 'info'} className="mt-4">
            This complaint is <strong>{data.status_label.toLowerCase()}</strong>. {data.status === 'rejected' && 'It could not be taken forward. You may submit a new complaint with more details or evidence.'}
          </Alert>
        )}
        <ol className="mt-5 space-y-0">
          {data.progress_steps.map((s, i) => {
            const meta = STATUSES[s.status]
            const done = reached.has(s.status) && (i < stepIndex || data.status === 'resolved' || offPath)
            const current = s.status === data.status
            const entry = [...data.timeline].reverse().find((t) => t.status === s.status)
            return (
              <li key={s.status} className="relative flex gap-4 pb-6 last:pb-0">
                {i < data.progress_steps.length - 1 && <span className={`absolute left-[17px] top-9 h-[calc(100%-2.25rem)] w-0.5 ${done ? 'bg-brand-500' : 'bg-slate-200'}`} aria-hidden="true" />}
                <span className={`relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${current ? 'bg-navy-900 text-white ring-4 ring-navy-100' : done ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-400'}`}>
                  {done && !current ? <Check className="h-4 w-4" /> : <meta.icon className="h-4 w-4" aria-hidden="true" />}
                </span>
                <div className="pt-1.5">
                  <p className={`font-semibold ${current || done ? 'text-navy-900' : 'text-slate-400'}`}>
                    {s.label} {current && <span className="ml-1 rounded-full bg-navy-100 px-2 py-0.5 text-[11px] font-semibold text-navy-700">Current</span>}
                  </p>
                  {entry && <p className="text-xs text-slate-500">{formatDate(entry.date)}</p>}
                  {entry?.message && <p className="mt-1 text-sm text-slate-600">{entry.message}</p>}
                  {!entry && !done && !current && s.status === 'forwarded' && (
                    <p className="text-xs text-slate-400">Shown only after our team actually submits the complaint to an authority.</p>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      </section>

      {data.can_add_information && (
        <AddInformation complaintId={complaintId} token={token} requested={data.info_requested} onDone={onRefresh} />
      )}
    </div>
  )
}

function AddInformation({ complaintId, token, requested, onDone }) {
  const config = usePublicConfig()
  const [open, setOpen] = useState(requested)
  const [message, setMessage] = useState('')
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState('')
  const inputRef = useRef(null)
  const warnings = detectPersonalInfo(message)
  const limits = config.uploads

  async function add(list) {
    setError('')
    const next = [...files]
    for (const file of Array.from(list)) {
      if (next.length >= limits.max_files) { setError(`You can add at most ${limits.max_files} files at a time.`); break }
      const { file: cleaned } = await cleanImage(file)
      next.push(cleaned)
    }
    setFiles(next)
  }

  async function send(e) {
    e.preventDefault()
    if (!message.trim() && files.length === 0) { setError('Please write a message or attach a file.'); return }
    setBusy(true)
    setError('')
    try {
      const pow = await getSolvedChallenge()
      const data = new FormData()
      data.append('complaint_id', complaintId.trim())
      data.append('tracking_token', token)
      data.append('message', message.trim())
      data.append('pow_challenge', pow.pow_challenge)
      data.append('pow_solution', pow.pow_solution)
      data.append('website', '')
      files.forEach((f, i) => data.append('files', f, genericName(f, i)))
      const res = await uploadForm('/api/public/complaints/supplement', data)
      setDone(res.message)
      setMessage('')
      setFiles([])
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={`card card-pad ${requested ? 'ring-2 ring-amber-300' : ''}`}>
      {requested && (
        <Alert tone="warning" icon={CircleAlert} className="mb-4" title="Our team has asked for more information">
          Please read the progress update above. Add details only if it is safe for you to do so.
        </Alert>
      )}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold"><MessageSquarePlus className="h-5 w-5 text-brand-600" /> Add more information</h2>
          <p className="mt-1 text-sm text-slate-600">Add new details or evidence to this complaint. You stay anonymous.</p>
        </div>
        {!open && <button type="button" className="btn-secondary btn-sm" onClick={() => setOpen(true)}>Add</button>}
      </div>
      {done && <Alert tone="success" className="mt-4">{done}</Alert>}
      {open && (
        <form onSubmit={send} className="mt-5 space-y-4" noValidate>
          <div>
            <label htmlFor="extra-message" className="label">Message <span className="font-normal text-slate-400">(optional if you attach files)</span></label>
            <textarea id="extra-message" rows={4} className="input" maxLength={3000} value={message} onChange={(e) => setMessage(e.target.value)} />
            {warnings.length > 0 && <p className="mt-1.5 flex items-center gap-1 text-xs font-medium text-amber-700"><ShieldAlert className="h-3.5 w-3.5" /> This may contain {warnings.join(', ')}. Please remove personal information.</p>}
          </div>
          <div>
            <button type="button" className="btn-secondary btn-sm" onClick={() => inputRef.current?.click()}><Paperclip className="h-4 w-4" /> Attach files</button>
            <input ref={inputRef} type="file" multiple accept={limits.accept} className="sr-only" aria-label="Attach files"
              onChange={(e) => { if (e.target.files?.length) add(e.target.files); e.target.value = '' }} />
            {files.length > 0 && (
              <ul className="mt-3 space-y-2">
                {files.map((f, i) => (
                  <li key={`${f.name}-${i}`} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                    <span className="truncate">{genericName(f, i)} &middot; {formatBytes(f.size)}</span>
                    <button type="button" className="text-slate-400 hover:text-red-600" aria-label="Remove file" onClick={() => setFiles(files.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="text-xs text-slate-500">Please do not upload photographs, videos, or documents containing your personal identity or information that could reveal who you are.</p>
          {error && <Alert tone="error">{error}</Alert>}
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? <><Spinner className="h-4 w-4" /> Sending...</> : <><Send className="h-4 w-4" /> Send information</>}
          </button>
        </form>
      )}
    </section>
  )
}
