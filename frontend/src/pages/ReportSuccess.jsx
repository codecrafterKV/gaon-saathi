import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Check, CheckCircle2, Copy, Download, KeyRound, Printer, Search, ShieldAlert, Smartphone, FileQuestion } from 'lucide-react'
import { Alert, EmptyState } from '../components/ui'
import { useDocumentTitle } from '../lib/hooks'
import { formatDate } from '../lib/format'

export default function ReportSuccess() {
  useDocumentTitle('Complaint Submitted')
  const location = useLocation()
  const navigate = useNavigate()
  // Keep the codes only in memory for this page view.
  const [result] = useState(() => location.state?.result || null)
  const [saved, setSaved] = useState(false)

  // Remove the codes from the browser history entry once shown, so a refresh
  // or "back" later on a shared phone does not reveal them again.
  useEffect(() => {
    if (location.state?.result) navigate(location.pathname, { replace: true, state: null })
  }, [location, navigate])

  if (!result) {
    return (
      <div className="container-page py-20">
        <div className="card mx-auto max-w-xl">
          <EmptyState icon={FileQuestion} title="Nothing to show here"
            action={<div className="flex flex-wrap justify-center gap-3"><Link to="/report" className="btn-primary">Report a Problem</Link><Link to="/track" className="btn-secondary">Track Complaint</Link></div>}>
            For your privacy, complaint codes are shown only once, right after you submit, and are not saved in this browser.
          </EmptyState>
        </div>
      </div>
    )
  }

  const download = () => {
    const text = [
      'GAON SAATHI - Complaint receipt',
      '',
      `Complaint ID:   ${result.complaint_id}`,
      `Tracking Code:  ${result.tracking_token}`,
      `Submitted on:   ${formatDate(result.submitted_on)}`,
      `Category:       ${result.category_label}`,
      '',
      'Keep this safe. You need BOTH codes to check the status of your complaint.',
      'Anyone who has both codes can see the status, so do not share them.',
    ].join('\r\n')
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `gaon-saathi-${result.complaint_id}.txt`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="bg-slate-50 py-12 sm:py-16">
      <div className="container-page">
        <div className="mx-auto max-w-2xl">
          <div className="text-center">
            <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 text-brand-700 ring-8 ring-brand-50">
              <CheckCircle2 className="h-9 w-9" aria-hidden="true" />
            </span>
            <h1 className="mt-6 text-3xl font-extrabold sm:text-4xl">Your complaint has been successfully submitted.</h1>
            <p className="mt-3 text-slate-600">Thank you for speaking up for your village.</p>
          </div>

          <Alert tone="warning" icon={KeyRound} className="mt-8" title="Save your Complaint ID carefully. You will need it to check your complaint status.">
            You also need the secret Tracking Code below. <strong>Both are shown only once</strong> and we cannot send them to you again, because we do not know who you are.
          </Alert>

          <div className="card mt-6 overflow-hidden">
            <div className="grid divide-y divide-slate-200 sm:grid-cols-2 sm:divide-x sm:divide-y-0">
              <CodeBox label="Complaint ID" value={result.complaint_id} />
              <CodeBox label="Secret Tracking Code" value={result.tracking_token} />
            </div>
            <dl className="grid grid-cols-2 gap-4 border-t border-slate-200 bg-slate-50 px-6 py-4 text-sm sm:grid-cols-3">
              <div><dt className="text-xs text-slate-500">Category</dt><dd className="font-semibold text-navy-900">{result.category_label}</dd></div>
              <div><dt className="text-xs text-slate-500">Submitted on</dt><dd className="font-semibold text-navy-900">{formatDate(result.submitted_on)}</dd></div>
              <div><dt className="text-xs text-slate-500">Status</dt><dd className="font-semibold text-navy-900">{result.status_label}</dd></div>
              <div><dt className="text-xs text-slate-500">Evidence files</dt><dd className="font-semibold text-navy-900">{result.evidence_count}</dd></div>
            </dl>
          </div>

          {result.notices?.length > 0 && (
            <Alert tone="info" className="mt-4">{result.notices.join(' ')}</Alert>
          )}

          <div className="no-print mt-6 grid gap-3 sm:grid-cols-2">
            <button type="button" className="btn-secondary" onClick={download}><Download className="h-4 w-4" /> Download as a text file</button>
            <button type="button" className="btn-secondary" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print</button>
          </div>

          <div className="card card-pad no-print mt-6">
            <h2 className="flex items-center gap-2 text-base font-bold"><ShieldAlert className="h-5 w-5 text-amber-600" /> Safety tips</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              <li className="flex gap-2"><Smartphone className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />If you use a shared phone, write the codes on paper and close this page. You can also clear the browser history.</li>
              <li className="flex gap-2"><KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />Do not share your Tracking Code. Anyone with both codes can see your complaint status.</li>
            </ul>
          </div>

          <label className="no-print mt-6 flex cursor-pointer items-center gap-3 rounded-2xl bg-white p-4 ring-1 ring-slate-200">
            <input type="checkbox" className="h-5 w-5 accent-brand-600" checked={saved} onChange={(e) => setSaved(e.target.checked)} />
            <span className="text-sm font-medium text-navy-900">I have saved my Complaint ID and Tracking Code.</span>
          </label>
          <div className="no-print mt-4 flex flex-col gap-3 sm:flex-row">
            <Link to="/track" className={`btn-primary flex-1 ${saved ? '' : 'pointer-events-none opacity-50'}`} aria-disabled={!saved} tabIndex={saved ? 0 : -1}>
              <Search className="h-4 w-4" /> Track complaint
            </Link>
            <Link to="/" className={`btn-secondary flex-1 ${saved ? '' : 'pointer-events-none opacity-50'}`} aria-disabled={!saved} tabIndex={saved ? 0 : -1}>
              Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function CodeBox({ label, value }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard unavailable: the code is visible to copy by hand */ }
  }
  return (
    <div className="p-6">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 select-all break-all font-mono text-xl font-bold tracking-wider text-navy-900 sm:text-2xl" data-testid={label === 'Complaint ID' ? 'complaint-id' : 'tracking-code'}>{value}</p>
      <button type="button" onClick={copy} className="no-print mt-3 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold text-brand-700 hover:bg-brand-50">
        {copied ? <><Check className="h-4 w-4" /> Copied</> : <><Copy className="h-4 w-4" /> Copy</>}
      </button>
    </div>
  )
}
