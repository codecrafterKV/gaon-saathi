import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, FileText, Film, ImageIcon, LockKeyhole, MapPin, Paperclip,
  ShieldAlert, ShieldCheck, Trash2, UploadCloud, Send, Info,
} from 'lucide-react'
import { CATEGORIES, CATEGORY_MAP, STATES } from '../lib/constants'
import { usePublicConfig, useDocumentTitle } from '../lib/hooks'
import { getSolvedChallenge } from '../lib/pow'
import { uploadForm } from '../lib/api'
import { cleanImage, detectPersonalInfo, genericName } from '../lib/privacy'
import { formatBytes } from '../lib/format'
import { Alert, Field, Spinner } from '../components/ui'

const STEPS = ['Problem type', 'Details', 'Evidence', 'Review & submit']
const EMPTY = { category: '', village: '', district: '', state: '', description: '', approximate_location: '' }
const KINDS = {
  image: { exts: ['jpg', 'jpeg', 'png', 'webp'], icon: ImageIcon },
  video: { exts: ['mp4', 'm4v', 'mov', '3gp', 'webm'], icon: Film },
  pdf: { exts: ['pdf'], icon: FileText },
}
const kindOf = (name) => {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return Object.keys(KINDS).find((k) => KINDS[k].exts.includes(ext)) || null
}

export default function Report() {
  useDocumentTitle('Report a Problem')
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const config = usePublicConfig()
  const limits = config.uploads
  const initialCategory = CATEGORY_MAP[params.get('category')] ? params.get('category') : ''

  const [step, setStep] = useState(0)
  const [form, setForm] = useState({ ...EMPTY, category: initialCategory })
  const [errors, setErrors] = useState({})
  const [files, setFiles] = useState([])
  const [fileError, setFileError] = useState('')
  const [processingFiles, setProcessingFiles] = useState(false)
  const [consent, setConsent] = useState(false)
  const [honeypot, setHoneypot] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [submitError, setSubmitError] = useState('')
  const [pow, setPow] = useState({ state: 'solving', fields: null })
  const powAbort = useRef(null)
  const topRef = useRef(null)

  // Solve the anti-spam check in the background while the form is filled.
  const startPow = useCallback(() => {
    powAbort.current?.abort()
    const controller = new AbortController()
    powAbort.current = controller
    setPow({ state: 'solving', fields: null })
    getSolvedChallenge(controller.signal)
      .then((fields) => setPow({ state: 'ready', fields }))
      .catch((err) => { if (err.name !== 'AbortError') setPow({ state: 'error', fields: null }) })
  }, [])
  useEffect(() => { startPow(); return () => powAbort.current?.abort() }, [startPow])

  // Release preview URLs.
  const filesRef = useRef(files)
  filesRef.current = files
  useEffect(() => () => filesRef.current.forEach((f) => f.preview && URL.revokeObjectURL(f.preview)), [])

  // Warn before leaving with unsent data.
  const dirty = useMemo(() => Object.entries(form).some(([k, v]) => v && v !== initialCategory) || files.length > 0, [form, files, initialCategory])
  useEffect(() => {
    if (!dirty || submitting) return undefined
    const handler = (e) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty, submitting])

  const update = (key, value) => {
    setForm((f) => ({ ...f, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
  }

  const piiWarnings = useMemo(
    () => detectPersonalInfo(`${form.description} ${form.approximate_location}`),
    [form.description, form.approximate_location],
  )

  function validate(currentStep) {
    const e = {}
    if (currentStep === 0 && !form.category) e.category = 'Please choose the type of problem.'
    if (currentStep === 1) {
      if (form.village.trim().length < 2) e.village = 'Please enter the village name.'
      if (form.district.trim().length < 2) e.district = 'Please enter the district.'
      if (!form.state) e.state = 'Please choose the state.'
      const len = form.description.trim().length
      if (len < 20) e.description = 'Please describe the problem in at least 20 characters.'
      if (len > 5000) e.description = 'Please keep the description under 5000 characters.'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const go = (next) => {
    if (next > step && !validate(step)) return
    setStep(next)
    setSubmitError('')
    topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function addFiles(list) {
    setFileError('')
    const incoming = Array.from(list)
    if (files.length + incoming.length > limits.max_files) {
      setFileError(`You can add at most ${limits.max_files} files.`)
      return
    }
    setProcessingFiles(true)
    const added = []
    for (const file of incoming) {
      const kind = kindOf(file.name)
      if (!kind) { setFileError(`"${file.name}" is not an accepted file type. Use photos, videos or PDF files.`); continue }
      const maxMb = kind === 'image' ? limits.max_image_mb : kind === 'video' ? limits.max_video_mb : limits.max_pdf_mb
      if (file.size > maxMb * 1024 * 1024) { setFileError(`"${file.name}" is larger than ${maxMb} MB.`); continue }
      let finalFile = file
      let cleaned = false
      if (kind === 'image') ({ file: finalFile, cleaned } = await cleanImage(file))
      added.push({
        id: crypto.randomUUID?.() || String(Math.random()),
        file: finalFile, kind, cleaned, originalName: file.name,
        preview: kind === 'image' || kind === 'video' ? URL.createObjectURL(finalFile) : null,
      })
    }
    const total = [...files, ...added].reduce((s, f) => s + f.file.size, 0)
    if (total > limits.max_total_mb * 1024 * 1024) {
      added.forEach((f) => f.preview && URL.revokeObjectURL(f.preview))
      setFileError(`All files together must be under ${limits.max_total_mb} MB.`)
    } else {
      setFiles((prev) => [...prev, ...added])
    }
    setProcessingFiles(false)
  }

  function removeFile(id) {
    setFiles((prev) => {
      const target = prev.find((f) => f.id === id)
      if (target?.preview) URL.revokeObjectURL(target.preview)
      return prev.filter((f) => f.id !== id)
    })
  }

  async function submit() {
    if (!consent) { setSubmitError('Please tick the box to confirm you understand how your complaint will be reviewed.'); return }
    for (const s of [0, 1]) if (!validate(s)) { setStep(s); return }
    setSubmitting(true)
    setSubmitError('')
    setProgress(0)
    try {
      let powFields = pow.fields
      if (!powFields) {
        powFields = await getSolvedChallenge()
      }
      const data = new FormData()
      Object.entries(form).forEach(([k, v]) => data.append(k, v.trim()))
      data.append('consent', 'true')
      data.append('website', honeypot)
      data.append('pow_challenge', powFields.pow_challenge)
      data.append('pow_solution', powFields.pow_solution)
      files.forEach((f, i) => data.append('files', f.file, genericName(f.file, i)))
      const result = await uploadForm('/api/public/complaints', data, setProgress)
      navigate('/report/success', { replace: true, state: { result } })
    } catch (err) {
      setSubmitError(err.message)
      if (err.fields && Object.keys(err.fields).length) {
        setErrors(err.fields)
        if (['category'].some((k) => err.fields[k])) setStep(0)
        else if (['village', 'district', 'state', 'description', 'approximate_location'].some((k) => err.fields[k])) setStep(1)
      }
      startPow() // challenges are single-use; prepare a new one
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-slate-50 pb-20">
      <div className="bg-navy-900">
        <div className="container-page py-10 sm:py-12">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-300">Report a problem</p>
          <h1 className="mt-2 text-3xl font-extrabold text-white sm:text-4xl">Tell us what is happening in your village</h1>
          <p className="mt-3 max-w-2xl text-navy-100">
            No registration. No personal information. Please describe the <strong className="text-white">problem</strong>, not yourself.
          </p>
        </div>
      </div>

      <div ref={topRef} className="container-page -mt-6 scroll-mt-24">
        <div className="mx-auto max-w-3xl">
          <Stepper step={step} />
          <div className="card mt-6 overflow-hidden">
            <form onSubmit={(e) => { e.preventDefault(); step < 3 ? go(step + 1) : submit() }} noValidate>
              {/* Honeypot: hidden from people and screen readers; bots tend to fill it. */}
              <div className="absolute -left-[9999px] h-px w-px overflow-hidden" aria-hidden="true">
                <label htmlFor="website">Leave this empty</label>
                <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" value={honeypot} onChange={(e) => setHoneypot(e.target.value)} />
              </div>

              <div className="p-5 sm:p-8">
                {step === 0 && <StepCategory value={form.category} onChange={(v) => update('category', v)} error={errors.category} />}
                {step === 1 && <StepDetails form={form} update={update} errors={errors} piiWarnings={piiWarnings} />}
                {step === 2 && (
                  <StepEvidence files={files} limits={limits} onAdd={addFiles} onRemove={removeFile}
                    error={fileError} processing={processingFiles} />
                )}
                {step === 3 && (
                  <StepReview form={form} files={files} consent={consent} setConsent={setConsent} goTo={go} pow={pow} />
                )}
                {submitError && <Alert tone="error" className="mt-6">{submitError}</Alert>}
                {submitting && (
                  <div className="mt-6" aria-live="polite">
                    <div className="flex justify-between text-xs font-medium text-slate-600">
                      <span>{progress < 1 ? 'Sending your complaint securely...' : 'Processing and encrypting...'}</span>
                      <span>{Math.round(progress * 100)}%</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                      <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${Math.max(5, progress * 100)}%` }} />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex flex-col-reverse gap-3 border-t border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
                {step > 0 ? (
                  <button type="button" className="btn-secondary" onClick={() => go(step - 1)} disabled={submitting}>
                    <ArrowLeft className="h-4 w-4" /> Back
                  </button>
                ) : <span className="hidden sm:block" />}
                {step < 3 ? (
                  <button type="submit" className="btn-primary" disabled={processingFiles}>
                    {step === 2 && files.length === 0 ? 'Skip - no evidence' : 'Continue'} <ArrowRight className="h-4 w-4" />
                  </button>
                ) : (
                  <button type="submit" className="btn-primary px-7" disabled={submitting || !consent}>
                    {submitting ? <><Spinner className="h-4 w-4" /> Submitting...</> : <><Send className="h-4 w-4" /> Submit Complaint</>}
                  </button>
                )}
              </div>
            </form>
          </div>
          <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
            <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            Your complaint is sent over an encrypted connection and stored encrypted. We do not store your IP address.
            In an emergency, call 112. <Link to="/privacy" className="font-medium text-brand-700 underline">Privacy Policy</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

function Stepper({ step }) {
  return (
    <ol className="card grid grid-cols-4 gap-1 p-2 sm:p-3" aria-label="Progress">
      {STEPS.map((label, i) => {
        const done = i < step
        const current = i === step
        return (
          <li key={label} className={`flex flex-col items-center gap-1.5 rounded-xl px-1 py-2 text-center sm:flex-row sm:gap-2.5 sm:px-3 sm:text-left ${current ? 'bg-brand-50' : ''}`}
            aria-current={current ? 'step' : undefined}>
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${done ? 'bg-brand-600 text-white' : current ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-500'}`}>
              {done ? <Check className="h-4 w-4" aria-hidden="true" /> : i + 1}
            </span>
            <span className={`text-[11px] font-semibold leading-tight sm:text-sm ${current ? 'text-navy-900' : 'text-slate-500'}`}>{label}</span>
          </li>
        )
      })}
    </ol>
  )
}

function StepHeading({ title, text }) {
  return (
    <div className="mb-6">
      <h2 className="text-xl font-bold sm:text-2xl">{title}</h2>
      {text && <p className="mt-1.5 text-slate-600">{text}</p>}
    </div>
  )
}

function StepCategory({ value, onChange, error }) {
  return (
    <fieldset>
      <legend className="sr-only">Type of problem</legend>
      <StepHeading title="What kind of problem is it?" text="Choose the option that fits best. If you are not sure, choose 'Other Village Problems'." />
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup">
        {CATEGORIES.map((c) => {
          const selected = value === c.value
          return (
            <label key={c.value}
              className={`relative flex cursor-pointer gap-3.5 rounded-2xl border-2 p-4 transition ${selected ? 'border-brand-600 bg-brand-50/60 shadow-sm' : 'border-slate-200 hover:border-navy-200 hover:bg-slate-50'}`}>
              <input type="radio" name="category" value={c.value} checked={selected} onChange={() => onChange(c.value)} className="sr-only" />
              <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${selected ? 'bg-brand-600 text-white' : 'bg-navy-50 text-navy-700'}`}>
                <c.icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block font-semibold text-navy-900">{c.label}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-slate-500">{c.hint}</span>
              </span>
              {selected && <CheckCircle2 className="absolute right-3 top-3 h-5 w-5 text-brand-600" aria-hidden="true" />}
            </label>
          )
        })}
      </div>
      {error && <Alert tone="error" className="mt-4">{error}</Alert>}
    </fieldset>
  )
}

function StepDetails({ form, update, errors, piiWarnings }) {
  const describedBy = (k) => (errors[k] ? `${k}-error` : `${k}-hint`)
  return (
    <div>
      <StepHeading title="Where is the problem, and what is happening?" />
      <Alert tone="info" icon={MapPin} className="mb-6">
        These questions are about <strong>where the problem is</strong>, not where you live. Do not write your own address.
      </Alert>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Village name" htmlFor="village" error={errors.village}>
          <input id="village" className={`input ${errors.village ? 'input-error' : ''}`} value={form.village} maxLength={100}
            onChange={(e) => update('village', e.target.value)} aria-invalid={!!errors.village} aria-describedby={describedBy('village')} autoComplete="off" />
        </Field>
        <Field label="District" htmlFor="district" error={errors.district}>
          <input id="district" className={`input ${errors.district ? 'input-error' : ''}`} value={form.district} maxLength={100}
            onChange={(e) => update('district', e.target.value)} aria-invalid={!!errors.district} aria-describedby={describedBy('district')} autoComplete="off" />
        </Field>
        <Field label="State" htmlFor="state" error={errors.state}>
          <select id="state" className={`input ${errors.state ? 'input-error' : ''}`} value={form.state}
            onChange={(e) => update('state', e.target.value)} aria-invalid={!!errors.state}>
            <option value="">Choose state / union territory</option>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Approximate location of the problem" htmlFor="approximate_location" optional error={errors.approximate_location}
          hint="For example: near the pond, ward 3, behind the school.">
          <input id="approximate_location" className="input" value={form.approximate_location} maxLength={200}
            onChange={(e) => update('approximate_location', e.target.value)} aria-describedby={describedBy('approximate_location')} autoComplete="off" />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Describe the problem" htmlFor="description" error={errors.description}
            hint="What did you see? When did it start? Who is affected? Write in simple words.">
            <textarea id="description" rows={7} className={`input resize-y ${errors.description ? 'input-error' : ''}`} value={form.description}
              maxLength={5000} onChange={(e) => update('description', e.target.value)} aria-invalid={!!errors.description}
              aria-describedby={describedBy('description')}
              placeholder="Example: Six big neem trees on panchayat land near the canal road were cut at night last week. The wood was taken away on a tractor." />
          </Field>
          <p className={`mt-1 text-right text-xs ${form.description.length > 4800 ? 'text-amber-700' : 'text-slate-400'}`}>
            {form.description.length} / 5000
          </p>
        </div>
      </div>
      {piiWarnings.length > 0 ? (
        <Alert tone="warning" title="Your text may contain personal information" className="mt-4">
          It looks like you may have written {piiWarnings.join(', ')}. To stay safe, please remove anything that could identify you.
        </Alert>
      ) : (
        <Alert tone="warning" icon={ShieldAlert} className="mt-4">
          Please do not write your name, phone number, address or anything that could reveal who you are.
        </Alert>
      )}
    </div>
  )
}

function StepEvidence({ files, limits, onAdd, onRemove, error, processing }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const totalSize = files.reduce((s, f) => s + f.file.size, 0)
  return (
    <div>
      <StepHeading title="Add evidence (optional)" text="Photos, videos or documents can help our team verify the problem. You can skip this step." />
      <Alert tone="warning" icon={ShieldAlert} className="mb-5" title="Protect your identity">
        Please do not upload photographs, videos, or documents containing your personal identity or information that could reveal who you are.
      </Alert>

      <div
        className={`flex flex-col items-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${dragging ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-slate-50/60'}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files?.length) onAdd(e.dataTransfer.files) }}
      >
        <span className="rounded-2xl bg-white p-3 text-brand-600 shadow-sm ring-1 ring-slate-200"><UploadCloud className="h-7 w-7" aria-hidden="true" /></span>
        <p className="mt-4 font-semibold text-navy-900">Choose files or drag them here</p>
        <p className="mt-1 text-xs text-slate-500">
          Photos (JPG, PNG, WebP) up to {limits.max_image_mb} MB, videos (MP4, MOV, 3GP, WebM) up to {limits.max_video_mb} MB,
          PDF up to {limits.max_pdf_mb} MB. Maximum {limits.max_files} files.
        </p>
        <button type="button" className="btn-navy mt-5" onClick={() => inputRef.current?.click()} disabled={processing || files.length >= limits.max_files}>
          {processing ? <><Spinner className="h-4 w-4" /> Preparing files...</> : <><Paperclip className="h-4 w-4" /> Choose files</>}
        </button>
        <input ref={inputRef} type="file" multiple accept={limits.accept} className="sr-only" aria-label="Choose evidence files"
          onChange={(e) => { if (e.target.files?.length) onAdd(e.target.files); e.target.value = '' }} />
      </div>
      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      {files.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center justify-between text-sm">
            <p className="font-semibold text-navy-900">{files.length} file{files.length > 1 ? 's' : ''} added</p>
            <p className="text-slate-500">{formatBytes(totalSize)} total</p>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {files.map((f, i) => {
              const Icon = KINDS[f.kind].icon
              return (
                <li key={f.id} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-100">
                    {f.kind === 'image' ? <img src={f.preview} alt={`Preview of evidence ${i + 1}`} className="h-full w-full object-cover" />
                      : f.kind === 'video' ? <video src={f.preview} className="h-full w-full object-cover" muted preload="metadata" />
                        : <Icon className="h-7 w-7 text-slate-500" aria-hidden="true" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-navy-900" title={f.originalName}>{f.originalName}</p>
                    <p className="text-xs text-slate-500">{formatBytes(f.file.size)} &middot; will be saved as {genericName(f.file, i)}</p>
                    {f.cleaned && <p className="mt-0.5 flex items-center gap-1 text-xs font-medium text-brand-700"><ShieldCheck className="h-3.5 w-3.5" /> Hidden location data removed</p>}
                    {f.kind === 'video' && <p className="mt-0.5 text-xs text-slate-500">Hidden data will be removed on our server</p>}
                  </div>
                  <button type="button" onClick={() => onRemove(f.id)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label={`Remove ${f.originalName}`}>
                    <Trash2 className="h-5 w-5" />
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
      <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        File names are replaced with generic names, and hidden information such as GPS location is removed from photos, videos and
        PDFs where technically possible. Evidence is encrypted and only authorised team members can view it.
      </p>
    </div>
  )
}

function StepReview({ form, files, consent, setConsent, goTo, pow }) {
  const category = CATEGORY_MAP[form.category]
  const rows = [
    ['Problem type', category?.label, 0],
    ['Village', form.village, 1],
    ['District', form.district, 1],
    ['State', form.state, 1],
    ['Approximate location', form.approximate_location || 'Not given', 1],
    ['Evidence', files.length ? `${files.length} file(s)` : 'None', 2],
  ]
  return (
    <div>
      <StepHeading title="Check and submit" text="Please check your complaint before sending it." />
      <dl className="divide-y divide-slate-100 rounded-2xl border border-slate-200">
        {rows.map(([label, value, s]) => (
          <div key={label} className="flex items-start justify-between gap-4 px-4 py-3">
            <div className="min-w-0">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
              <dd className="mt-0.5 break-words font-medium text-navy-900">{value}</dd>
            </div>
            <button type="button" className="shrink-0 text-xs font-semibold text-brand-700 hover:underline" onClick={() => goTo(s)}>Edit</button>
          </div>
        ))}
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Description</dt>
            <button type="button" className="text-xs font-semibold text-brand-700 hover:underline" onClick={() => goTo(1)}>Edit</button>
          </div>
          <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-700">{form.description}</dd>
        </div>
      </dl>

      <label className={`mt-6 flex cursor-pointer gap-3 rounded-2xl border-2 p-4 transition ${consent ? 'border-brand-600 bg-brand-50/50' : 'border-slate-200'}`}>
        <input type="checkbox" className="mt-0.5 h-5 w-5 shrink-0 rounded border-slate-300 accent-brand-600" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span className="text-sm leading-relaxed text-navy-900">
          I understand that my complaint and supporting evidence may be reviewed by the Gaon Saathi team for verification and appropriate follow-up.
        </span>
      </label>
      <p className="mt-3 text-xs leading-relaxed text-slate-500">
        Gaon Saathi is an independent platform, not a government office. Submitting here does not create an official
        government complaint or legal representation. See our <Link to="/terms" className="font-medium text-brand-700 underline">Terms</Link>.
      </p>
      <p className="mt-3 flex items-center gap-2 text-xs text-slate-500" aria-live="polite">
        {pow.state === 'ready' ? <><ShieldCheck className="h-4 w-4 text-brand-600" /> Security check complete</>
          : pow.state === 'error' ? <><ShieldAlert className="h-4 w-4 text-amber-600" /> Security check will run when you submit</>
            : <><Spinner className="h-4 w-4" /> Running a quick security check...</>}
      </p>
    </div>
  )
}
