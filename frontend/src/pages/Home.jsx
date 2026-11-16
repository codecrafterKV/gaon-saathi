import { Link } from 'react-router-dom'
import {
  ArrowRight, Megaphone, Search, ShieldCheck, EyeOff, Lock, UserX, Phone, Mail, Fingerprint, MapPin,
  Camera, ClipboardList, KeyRound, FileSearch, Send, HeartHandshake, Scale, Sprout, ChevronDown, Check,
  Inbox, Hourglass,
} from 'lucide-react'
import { CATEGORIES } from '../lib/constants'
import { useDocumentTitle, useReveal } from '../lib/hooks'
import { LogoMark } from '../components/Logo'

export default function Home() {
  useDocumentTitle(null)
  return (
    <>
      <Hero />
      <WhatIs />
      <Problems />
      <Steps />
      <WhyAnonymous />
      <Mission />
      <Faq />
      <FinalCta />
    </>
  )
}

function Reveal({ as: Tag = 'div', className = '', children, delay = 0 }) {
  const ref = useReveal()
  return <Tag ref={ref} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>{children}</Tag>
}

/* ------------------------------------------------------------------ */
function Hero() {
  return (
    <section className="relative overflow-hidden bg-navy-900">
      <div className="absolute inset-0 bg-grid" aria-hidden="true" />
      <div className="absolute -left-40 top-10 h-96 w-96 rounded-full bg-brand-500/25 blur-3xl" aria-hidden="true" />
      <div className="absolute -right-32 bottom-0 h-80 w-80 rounded-full bg-sky-400/10 blur-3xl" aria-hidden="true" />
      <div className="container-page relative grid items-center gap-12 py-16 sm:py-20 lg:grid-cols-12 lg:py-28">
        <div className="lg:col-span-7">
          <p className="inline-flex animate-fade-up items-center gap-2 rounded-full bg-white/10 px-3.5 py-1.5 text-xs font-semibold text-brand-200 ring-1 ring-white/15">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Safe and anonymous village reporting
          </p>
          <h1 className="mt-6 animate-fade-up text-4xl font-extrabold leading-[1.08] tracking-tight text-white text-balance sm:text-6xl" style={{ animationDelay: '80ms' }}>
            Your Village. <span className="text-brand-300">Your Voice.</span> Your Right.
          </h1>
          <p className="mt-6 max-w-xl animate-fade-up text-lg leading-relaxed text-navy-100 sm:text-xl" style={{ animationDelay: '160ms' }}>
            Report problems in your village safely. No registration. No personal information required.
          </p>
          <div className="mt-9 flex animate-fade-up flex-col gap-3 sm:flex-row" style={{ animationDelay: '240ms' }}>
            <Link to="/report" className="btn-primary px-7 py-3.5 text-base">
              <Megaphone className="h-5 w-5" aria-hidden="true" /> Report a Problem
            </Link>
            <Link to="/track" className="btn-outline-light px-7 py-3.5 text-base">
              <Search className="h-5 w-5" aria-hidden="true" /> Track Your Complaint
            </Link>
          </div>
          <ul className="mt-10 grid max-w-xl animate-fade-up grid-cols-1 gap-3 text-sm text-navy-100 sm:grid-cols-3" style={{ animationDelay: '320ms' }}>
            {[[UserX, 'No name or phone'], [EyeOff, 'No login needed'], [Lock, 'Encrypted & private']].map(([Icon, text]) => (
              <li key={text} className="flex items-center gap-2">
                <span className="rounded-lg bg-brand-500/20 p-1.5"><Icon className="h-4 w-4 text-brand-300" aria-hidden="true" /></span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <div className="lg:col-span-5">
          <HeroVisual />
        </div>
      </div>
    </section>
  )
}

function HeroVisual() {
  const steps = [
    { icon: Inbox, label: 'Received', done: true },
    { icon: Search, label: 'Under Review', done: true },
    { icon: FileSearch, label: 'Evidence Verification', current: true },
    { icon: Send, label: 'Forwarded to Authority' },
  ]
  return (
    <div className="relative mx-auto max-w-md animate-fade-up" style={{ animationDelay: '200ms' }} aria-hidden="true">
      <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-brand-400/30 to-sky-400/10 blur-2xl" />
      <div className="relative rounded-3xl bg-white p-6 pb-14 shadow-lift">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <LogoMark className="h-10 w-10" />
            <div>
              <p className="text-xs font-medium text-slate-500">Complaint ID</p>
              <p className="font-mono text-sm font-bold tracking-wide text-navy-900">GS-2026-K7QM4XRT</p>
            </div>
          </div>
          <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[11px] font-semibold text-violet-800 ring-1 ring-violet-200">In progress</span>
        </div>
        <div className="mt-5 rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Illegal Tree Cutting</p>
          <p className="mt-1 text-sm text-slate-600">Our team is checking the information and evidence provided.</p>
        </div>
        <ol className="mt-5 space-y-3.5">
          {steps.map((s) => (
            <li key={s.label} className="flex items-center gap-3">
              <span className={`flex h-8 w-8 items-center justify-center rounded-full ${s.done ? 'bg-brand-600 text-white' : s.current ? 'bg-violet-100 text-violet-700 ring-2 ring-violet-300' : 'bg-slate-100 text-slate-400'}`}>
                {s.done ? <Check className="h-4 w-4" /> : <s.icon className="h-4 w-4" />}
              </span>
              <span className={`text-sm ${s.done || s.current ? 'font-semibold text-navy-900' : 'text-slate-400'}`}>{s.label}</span>
              {s.current && <Hourglass className="ml-auto h-4 w-4 text-violet-500" />}
            </li>
          ))}
        </ol>
      </div>
      <div className="absolute -bottom-6 -left-4 flex items-center gap-2.5 rounded-2xl bg-navy-950 px-4 py-3 text-white shadow-lift ring-1 ring-white/10 sm:-left-10">
        <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-brand-500">
          <span className="absolute inset-0 animate-pulse-ring rounded-full bg-brand-400" />
          <ShieldCheck className="relative h-5 w-5" />
        </span>
        <div>
          <p className="text-xs font-semibold">Reporter identity</p>
          <p className="text-[11px] text-navy-200">Never asked. Never stored.</p>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
function WhatIs() {
  const points = [
    { icon: Megaphone, title: 'Speak up safely', text: 'Report a problem in a few minutes from any phone. You do not need an account.' },
    { icon: FileSearch, title: 'We check the facts', text: 'Our team reviews every complaint and the evidence you choose to share.' },
    { icon: Send, title: 'We help take it forward', text: 'Where it is right to do so, we take the issue to the relevant authority and follow up.' },
  ]
  return (
    <section className="section bg-white">
      <div className="container-page grid gap-12 lg:grid-cols-2 lg:items-center">
        <Reveal>
          <span className="eyebrow">What is Gaon Saathi?</span>
          <h2 className="section-title mt-4 text-balance">A trusted bridge between villagers and the people who can fix problems</h2>
          <p className="section-lead">
            Gaon Saathi ("village companion") is an independent platform where anyone can report problems they see in their
            village: encroachment, illegal tree cutting, misuse of development funds, ration irregularities and more.
          </p>
          <p className="mt-4 leading-relaxed text-slate-600">
            Many people stay silent because they fear powerful people or conflict in the village. Gaon Saathi lets you raise
            your voice <strong className="text-navy-900">without telling us who you are</strong>.
          </p>
          <Link to="/about" className="mt-7 inline-flex items-center gap-1.5 font-semibold text-brand-700 hover:text-brand-800">
            Learn more about us <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Reveal>
        <div className="grid gap-4">
          {points.map((p, i) => (
            <Reveal key={p.title} delay={i * 90} className="card card-pad flex gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 ring-1 ring-brand-100">
                <p.icon className="h-6 w-6" aria-hidden="true" />
              </span>
              <div>
                <h3 className="text-lg font-bold">{p.title}</h3>
                <p className="mt-1 text-slate-600">{p.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
function Problems() {
  return (
    <section className="section bg-slate-50 bg-dots" id="problems">
      <div className="container-page">
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">Problems we address</span>
          <h2 className="section-title mt-4">What can you report?</h2>
          <p className="section-lead">Problems with public land, public money and public services in your village.</p>
        </Reveal>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CATEGORIES.map((c, i) => (
            <Reveal key={c.value} delay={(i % 4) * 70}>
              <Link to={`/report?category=${c.value}`} className="group card card-pad flex h-full flex-col transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lift">
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-navy-900 text-brand-300 transition group-hover:bg-brand-600 group-hover:text-white">
                  <c.icon className="h-6 w-6" aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-base font-bold">{c.label}</h3>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-slate-600">{c.hint}</p>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-700">
                  Report this <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </Link>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
export const HOW_STEPS = [
  { icon: ClipboardList, title: 'Choose the problem', text: 'Pick the type of problem and tell us the village, district and state where it is happening.' },
  { icon: Camera, title: 'Describe it and add evidence', text: 'Explain what you saw. You can add photos, videos or PDF documents if you have them (optional).' },
  { icon: KeyRound, title: 'Save your two codes', text: 'You get a Complaint ID and a secret Tracking Code. Write them down. Nobody else can see your complaint status without both.' },
  { icon: HeartHandshake, title: 'We review and follow up', text: 'Our team checks the details, finds the right authority and records every step. Check progress any time.' },
]

function Steps() {
  return (
    <section className="section bg-white">
      <div className="container-page">
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">How Gaon Saathi works</span>
          <h2 className="section-title mt-4">Four simple steps</h2>
          <p className="section-lead">No forms to sign. No office to visit. No account to create.</p>
        </Reveal>
        <ol className="relative mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="absolute left-0 right-0 top-7 hidden h-0.5 bg-gradient-to-r from-brand-200 via-brand-400 to-brand-200 lg:block" aria-hidden="true" />
          {HOW_STEPS.map((s, i) => (
            <Reveal as="li" key={s.title} delay={i * 90} className="relative">
              <span className="relative z-10 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/30 ring-4 ring-white">
                <s.icon className="h-6 w-6" aria-hidden="true" />
              </span>
              <p className="mt-5 text-xs font-bold uppercase tracking-wider text-brand-700">Step {i + 1}</p>
              <h3 className="mt-1 text-lg font-bold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.text}</p>
            </Reveal>
          ))}
        </ol>
        <div className="mt-12 text-center">
          <Link to="/how-it-works" className="btn-secondary">See the full process <ArrowRight className="h-4 w-4" /></Link>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
function WhyAnonymous() {
  const never = [
    [UserX, 'Your name'], [Phone, 'Mobile number'], [Mail, 'Email address'],
    [Fingerprint, 'Aadhaar number'], [MapPin, 'Home address'], [Camera, 'Your photograph'],
  ]
  return (
    <section className="section relative overflow-hidden bg-navy-950">
      <div className="absolute inset-0 bg-grid opacity-70" aria-hidden="true" />
      <div className="container-page relative grid gap-12 lg:grid-cols-2 lg:items-center">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-300">Why anonymous reporting matters</p>
          <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-white sm:text-4xl text-balance">
            People should not have to choose between their safety and their village's future.
          </h2>
          <p className="mt-5 leading-relaxed text-navy-200">
            In a small village, everyone knows everyone. Raising a complaint openly can lead to threats, pressure or
            conflict. When people stay silent, encroachments grow, trees disappear and public money is wasted.
          </p>
          <p className="mt-4 leading-relaxed text-navy-200">
            Anonymous reporting makes it safer to speak up. The facts of a problem matter, not the identity of the person who noticed it.
          </p>
          <p className="mt-6 rounded-xl bg-white/5 p-4 text-sm leading-relaxed text-navy-200 ring-1 ring-white/10">
            <strong className="text-white">Honest note:</strong> no website can promise complete anonymity. What you write
            or upload could reveal who you are, so describe the problem, not yourself.{' '}
            <Link to="/privacy" className="font-semibold text-brand-300 underline underline-offset-2">Read how we protect you</Link>.
          </p>
        </Reveal>
        <Reveal delay={120} className="rounded-3xl bg-white/[0.04] p-6 ring-1 ring-white/10 sm:p-8">
          <h3 className="text-lg font-bold text-white">What we never ask for</h3>
          <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {never.map(([Icon, label]) => (
              <li key={label} className="flex flex-col items-center gap-2 rounded-2xl bg-white/5 p-4 text-center ring-1 ring-white/10">
                <span className="relative">
                  <Icon className="h-6 w-6 text-navy-300" aria-hidden="true" />
                  <span className="absolute left-1/2 top-1/2 h-0.5 w-8 -translate-x-1/2 -translate-y-1/2 -rotate-45 rounded bg-red-400" aria-hidden="true" />
                </span>
                <span className="text-xs font-medium text-navy-100">{label}</span>
              </li>
            ))}
          </ul>
          <ul className="mt-6 space-y-2.5 text-sm text-navy-100">
            {['No account or login', 'IP addresses are not stored', 'No advertising or tracking cookies',
              'Hidden location data is removed from photos', 'Complaints and evidence are encrypted'].map((t) => (
              <li key={t} className="flex items-center gap-2.5"><Check className="h-4 w-4 shrink-0 text-brand-300" aria-hidden="true" />{t}</li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
function Mission() {
  const values = [
    { icon: ShieldCheck, title: 'Safety first', text: 'We collect as little as possible and protect what we hold.' },
    { icon: Scale, title: 'Fair and factual', text: 'We check evidence before taking any complaint forward.' },
    { icon: Sprout, title: 'Stronger villages', text: 'Protecting public land, trees and funds helps everyone.' },
  ]
  return (
    <section className="section bg-white">
      <div className="container-page">
        <Reveal className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 to-brand-800 px-6 py-12 text-center sm:px-12 sm:py-16">
          <div className="absolute inset-0 bg-grid opacity-40" aria-hidden="true" />
          <p className="relative text-sm font-semibold uppercase tracking-wider text-brand-100">Our mission</p>
          <p className="relative mx-auto mt-4 max-w-3xl font-display text-2xl font-bold leading-snug text-white text-balance sm:text-3xl">
            "To make sure every villager can report misuse of public resources safely, and that every genuine complaint
            reaches someone who can act on it."
          </p>
        </Reveal>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {values.map((v, i) => (
            <Reveal key={v.title} delay={i * 80} className="card card-pad text-center">
              <v.icon className="mx-auto h-7 w-7 text-brand-600" aria-hidden="true" />
              <h3 className="mt-3 font-bold">{v.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{v.text}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
export const FAQS = [
  ['Do I need to register or give my phone number?',
    'No. You do not need an account, a phone number, an email address or Aadhaar. We never ask for your name.'],
  ['Is my identity completely hidden?',
    'We do not ask for or store your identity, and we do not store IP addresses. But no website can guarantee complete anonymity: the words you write, the photos you upload, or someone seeing you use your phone could reveal you. Describe the problem, not yourself, and avoid showing faces or your house in photos.'],
  ['Is Gaon Saathi a government website?',
    'No. Gaon Saathi is an independent support platform. It is not run by the government. Submitting here is not the same as filing an official government complaint, but our team can help take genuine complaints to the right authority.'],
  ['What happens after I submit a complaint?',
    'Our team reviews it, checks the evidence, identifies the right department or official grievance channel and, where appropriate, submits it there and follows up. Every step is recorded and you can see the progress on the Track Complaint page.'],
  ['How do I check the status of my complaint?',
    'Go to Track Complaint and enter your Complaint ID and your secret Tracking Code. You need both.'],
  ['What if I lose my Complaint ID or Tracking Code?',
    'Because we do not know who you are, we cannot send them to you again or recover them. Please write them down or save them safely. If you lose them, you can submit the complaint again and mention that it was reported before.'],
  ['Can I add more information later?',
    'Yes. Open your complaint on the Track Complaint page and use "Add more information" to add details or files while the complaint is open.'],
  ['Will my problem definitely be solved?',
    'We cannot promise a result. We will review your complaint honestly and follow up with authorities where it is appropriate. We never mark a complaint as resolved without a real update.'],
  ['What should I do in an emergency?',
    'Gaon Saathi is not an emergency service. If someone is in danger, call 112 (national emergency number) immediately.'],
]

function Faq() {
  return (
    <section className="section bg-slate-50" id="faq">
      <div className="container-page grid gap-12 lg:grid-cols-12">
        <Reveal className="lg:col-span-4">
          <span className="eyebrow">FAQ</span>
          <h2 className="section-title mt-4">Frequently asked questions</h2>
          <p className="section-lead">Still have a question? Visit our <Link to="/contact" className="font-semibold text-brand-700 underline underline-offset-2">support page</Link>.</p>
        </Reveal>
        <div className="space-y-3 lg:col-span-8">
          {FAQS.map(([q, a]) => (
            <details key={q} className="group card overflow-hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-left font-semibold text-navy-900 marker:hidden hover:bg-slate-50 [&::-webkit-details-marker]:hidden">
                {q}
                <ChevronDown className="h-5 w-5 shrink-0 text-slate-400 transition group-open:rotate-180" aria-hidden="true" />
              </summary>
              <p className="px-5 pb-5 leading-relaxed text-slate-600">{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="bg-white pb-20">
      <div className="container-page">
        <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-navy-900 p-8 sm:p-12 lg:flex-row lg:items-center">
          <div>
            <h2 className="text-2xl font-extrabold text-white sm:text-3xl">Seen a problem in your village?</h2>
            <p className="mt-2 text-navy-200">It takes about 5 minutes. No registration. No personal information.</p>
          </div>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
            <Link to="/report" className="btn-primary px-7 py-3.5 text-base"><Megaphone className="h-5 w-5" /> Report a Problem</Link>
            <Link to="/track" className="btn-outline-light px-7 py-3.5 text-base"><Search className="h-5 w-5" /> Track Complaint</Link>
          </div>
        </div>
      </div>
    </section>
  )
}
