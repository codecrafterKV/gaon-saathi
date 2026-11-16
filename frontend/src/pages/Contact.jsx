import { Link } from 'react-router-dom'
import { Mail, Phone, MessageSquarePlus, Siren, Baby, ShieldAlert, HeartHandshake, Search, BookOpen } from 'lucide-react'
import { PageHero } from '../components/ui'
import { useDocumentTitle, usePublicConfig } from '../lib/hooks'

const HELPLINES = [
  { icon: Siren, number: '112', label: 'National emergency number', text: 'Police, fire or ambulance when someone is in danger.' },
  { icon: HeartHandshake, number: '181', label: 'Women helpline', text: 'Support for women facing violence or harassment (available in most states).' },
  { icon: Baby, number: '1098', label: 'Child helpline', text: 'For children in need of care and protection.' },
  { icon: ShieldAlert, number: '1930', label: 'Cyber crime helpline', text: 'To report online fraud. You can also use cybercrime.gov.in.' },
]

export default function Contact() {
  useDocumentTitle('Contact / Support')
  const { support } = usePublicConfig()
  const hasContact = support?.email || support?.phone
  return (
    <>
      <PageHero eyebrow="Contact / Support" title="How can we help?"
        lead="We do not run a contact form, because a contact form would collect information about you. Here is how to get help safely." />
      <section className="section">
        <div className="container-page grid gap-6 lg:grid-cols-3">
          <div className="card card-pad">
            <MessageSquarePlus className="h-7 w-7 text-brand-600" aria-hidden="true" />
            <h2 className="mt-4 text-lg font-bold">Add to an existing complaint</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Open your complaint with your Complaint ID and Tracking Code and choose "Add more information". This keeps you anonymous.
            </p>
            <Link to="/track" className="btn-secondary mt-5"><Search className="h-4 w-4" /> Track Complaint</Link>
          </div>
          <div className="card card-pad">
            <BookOpen className="h-7 w-7 text-brand-600" aria-hidden="true" />
            <h2 className="mt-4 text-lg font-bold">Questions about the platform</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">Most questions are answered in our FAQ and on the How It Works page.</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link to="/#faq" className="btn-secondary">Read the FAQ</Link>
              <Link to="/how-it-works" className="btn-ghost">How It Works</Link>
            </div>
          </div>
          <div className="card card-pad">
            <Mail className="h-7 w-7 text-brand-600" aria-hidden="true" />
            <h2 className="mt-4 text-lg font-bold">Contact the team</h2>
            {hasContact ? (
              <ul className="mt-3 space-y-2 text-sm">
                {support.email && <li className="flex items-center gap-2"><Mail className="h-4 w-4 text-slate-400" /><a className="font-medium text-brand-700 underline" href={`mailto:${support.email}`}>{support.email}</a></li>}
                {support.phone && <li className="flex items-center gap-2"><Phone className="h-4 w-4 text-slate-400" /><a className="font-medium text-brand-700 underline" href={`tel:${support.phone.replace(/\s/g, '')}`}>{support.phone}</a></li>}
              </ul>
            ) : (
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                We do not publish a direct email or phone line for complaints, because using one would reveal who you are.
                Everything the team needs can be shared through the anonymous complaint form and the Track Complaint page.
              </p>
            )}
            {hasContact && <p className="mt-3 text-xs text-slate-500">Emailing or calling us reveals your email address or phone number. To stay anonymous, use the complaint form.</p>}
          </div>
        </div>
      </section>
      <section className="section bg-slate-50">
        <div className="container-page">
          <h2 className="section-title">Urgent help</h2>
          <p className="section-lead">Gaon Saathi is not an emergency service. For urgent help, call these free official helplines.</p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {HELPLINES.map((h) => (
              <a key={h.number} href={`tel:${h.number}`} className="card card-pad block transition hover:border-brand-300 hover:shadow-lift">
                <h.icon className="h-6 w-6 text-red-600" aria-hidden="true" />
                <p className="mt-3 font-display text-3xl font-extrabold text-navy-900">{h.number}</p>
                <p className="mt-1 font-semibold text-navy-900">{h.label}</p>
                <p className="mt-1 text-sm text-slate-600">{h.text}</p>
              </a>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
