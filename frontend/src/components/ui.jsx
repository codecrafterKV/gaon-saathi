import { useEffect } from 'react'
import { AlertTriangle, CheckCircle2, Info, LoaderCircle, X, XCircle } from 'lucide-react'
import { STATUSES, VERIFICATION } from '../lib/constants'

const ALERT_TONES = {
  info: { box: 'bg-navy-50 text-navy-800 ring-navy-200', icon: Info },
  success: { box: 'bg-brand-50 text-brand-900 ring-brand-200', icon: CheckCircle2 },
  warning: { box: 'bg-amber-50 text-amber-900 ring-amber-200', icon: AlertTriangle },
  error: { box: 'bg-red-50 text-red-800 ring-red-200', icon: XCircle },
}

export function Alert({ tone = 'info', title, children, className = '', icon }) {
  const t = ALERT_TONES[tone]
  const Icon = icon || t.icon
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`flex gap-3 rounded-xl p-4 text-sm ring-1 ${t.box} ${className}`}>
      <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 space-y-1 leading-relaxed">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div>{children}</div>}
      </div>
    </div>
  )
}

export function Spinner({ className = 'h-5 w-5' }) {
  return <LoaderCircle className={`animate-spin ${className}`} aria-hidden="true" />
}

export function LoadingBlock({ label = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500" role="status">
      <Spinner /> <span>{label}</span>
    </div>
  )
}

export function StatusBadge({ status, size = 'md', short = false }) {
  const s = STATUSES[status]
  if (!s) return null
  const Icon = s.icon
  const pad = size === 'lg' ? 'px-3.5 py-1.5 text-sm' : 'px-2.5 py-1 text-xs'
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full font-semibold ring-1 ring-inset ${pad} ${s.tone}`}>
      <Icon className={size === 'lg' ? 'h-4 w-4' : 'h-3.5 w-3.5'} aria-hidden="true" />
      {short && s.short ? s.short : s.label}
    </span>
  )
}

export function VerificationBadge({ status }) {
  const v = VERIFICATION[status]
  if (!v) return null
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${v.tone}`}>{v.label}</span>
}

export function DemoBadge() {
  return (
    <span className="inline-flex items-center rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-900 ring-1 ring-inset ring-amber-300">
      Demo
    </span>
  )
}

export function Modal({ open, onClose, title, children, footer, wide = false }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = prev }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="absolute inset-0 bg-navy-950/50 backdrop-blur-[2px]" aria-label="Close dialog" onClick={onClose} />
      <div className={`relative flex max-h-[92vh] w-full flex-col overflow-hidden rounded-t-2xl bg-white shadow-lift sm:rounded-2xl ${wide ? 'sm:max-w-3xl' : 'sm:max-w-lg'}`}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-5">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3">{footer}</div>}
      </div>
    </div>
  )
}

export function PageHero({ eyebrow, title, lead, children }) {
  return (
    <section className="relative overflow-hidden bg-navy-900">
      <div className="absolute inset-0 bg-grid opacity-60" aria-hidden="true" />
      <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand-500/20 blur-3xl" aria-hidden="true" />
      <div className="container-page relative py-14 sm:py-20">
        {eyebrow && <p className="text-sm font-semibold uppercase tracking-wider text-brand-300">{eyebrow}</p>}
        <h1 className="mt-3 max-w-3xl text-3xl font-extrabold tracking-tight text-white text-balance sm:text-5xl">{title}</h1>
        {lead && <p className="mt-4 max-w-2xl text-base leading-relaxed text-navy-100 sm:text-lg">{lead}</p>}
        {children}
      </div>
    </section>
  )
}

export function Field({ label, htmlFor, hint, error, optional, children }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="label">
        {label} {optional ? <span className="font-normal text-slate-400">(optional)</span> : <span className="text-red-600" aria-hidden="true">*</span>}
      </label>
      {children}
      {error ? (
        <p className="field-error" id={`${htmlFor}-error`}><XCircle className="h-3.5 w-3.5" aria-hidden="true" />{error}</p>
      ) : hint ? <p className="hint" id={`${htmlFor}-hint`}>{hint}</p> : null}
    </div>
  )
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {Icon && <div className="mb-4 rounded-2xl bg-navy-50 p-4 text-navy-500"><Icon className="h-7 w-7" aria-hidden="true" /></div>}
      <h3 className="text-base font-bold text-navy-900">{title}</h3>
      {children && <p className="mt-1.5 max-w-sm text-sm text-slate-500">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
