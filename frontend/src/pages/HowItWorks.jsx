import { Link } from 'react-router-dom'
import { ArrowRight, Megaphone } from 'lucide-react'
import { PageHero, StatusBadge } from '../components/ui'
import { useDocumentTitle } from '../lib/hooks'
import { HOW_STEPS } from './Home'

const STATUS_HELP = [
  ['received', 'Your complaint has reached us safely and is waiting for review.'],
  ['under_review', 'A team member is reading the complaint and checking that the details are complete.'],
  ['evidence_verification', 'We are checking photos, documents or public records to confirm the problem.'],
  ['action_in_progress', 'We have identified what needs to be done and who is responsible, and are preparing the next step.'],
  ['forwarded', 'We have actually submitted the complaint to a government department or official grievance channel and recorded the acknowledgement.'],
  ['resolved', 'We have a real update showing the problem was addressed. We never mark a complaint resolved without one.'],
  ['rejected', 'We could not take the complaint forward, for example because it was not about a public problem or there was not enough information.'],
  ['closed', 'The complaint is finished, for example because it was a duplicate or no further action is possible.'],
]

export default function HowItWorks() {
  useDocumentTitle('How It Works')
  return (
    <>
      <PageHero eyebrow="How it works" title="From your report to real follow-up"
        lead="Here is exactly what happens when you report a problem on Gaon Saathi." />
      <section className="section">
        <div className="container-page">
          <ol className="mx-auto max-w-3xl space-y-6">
            {HOW_STEPS.map((s, i) => (
              <li key={s.title} className="card card-pad flex gap-5">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-600 text-white"><s.icon className="h-6 w-6" aria-hidden="true" /></span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-brand-700">Step {i + 1}</p>
                  <h2 className="mt-1 text-lg font-bold">{s.title}</h2>
                  <p className="mt-1.5 leading-relaxed text-slate-600">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section bg-slate-50" id="statuses">
        <div className="container-page">
          <div className="mx-auto max-w-3xl">
            <h2 className="section-title">What each status means</h2>
            <p className="section-lead">You will see one of these on the Track Complaint page.</p>
            <dl className="card mt-8 divide-y divide-slate-100">
              {STATUS_HELP.map(([status, text]) => (
                <div key={status} className="grid gap-2 p-5 sm:grid-cols-[230px_1fr] sm:gap-6">
                  <dt><StatusBadge status={status} /></dt>
                  <dd className="text-sm leading-relaxed text-slate-600">{text}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container-page">
          <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-2">
            <div className="card card-pad">
              <h2 className="text-lg font-bold">Tips for a strong complaint</h2>
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-600">
                <li>Say <strong>what</strong> happened, <strong>where</strong> and roughly <strong>when</strong>.</li>
                <li>Mention landmarks (school, pond, temple) instead of people's houses.</li>
                <li>Add a clear photo of the problem, without people's faces, if it is safe to take one.</li>
                <li>Copies of public notices, work boards or ration slips are very helpful.</li>
              </ul>
            </div>
            <div className="card card-pad">
              <h2 className="text-lg font-bold">Keep yourself safe</h2>
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-600">
                <li>Do not write your name, phone number or address.</li>
                <li>Do not take photos if it could put you in danger.</li>
                <li>On a shared phone, write the codes on paper and clear the browser history.</li>
                <li>In an emergency, call <strong>112</strong>. Gaon Saathi is not an emergency service.</li>
              </ul>
            </div>
          </div>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/report" className="btn-primary px-7"><Megaphone className="h-4 w-4" /> Report a Problem</Link>
            <Link to="/track" className="btn-secondary">Track Complaint <ArrowRight className="h-4 w-4" /></Link>
          </div>
        </div>
      </section>
    </>
  )
}
