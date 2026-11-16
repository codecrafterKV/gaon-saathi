import { Link } from 'react-router-dom'
import { Eye, Scale, ShieldCheck, Sprout, Users, Megaphone, Handshake, Ban } from 'lucide-react'
import { PageHero } from '../components/ui'
import { useDocumentTitle } from '../lib/hooks'

export default function About() {
  useDocumentTitle('About Us')
  const values = [
    { icon: ShieldCheck, title: 'Privacy by design', text: 'We built the platform so that we never need to know who you are. What we do not collect cannot leak.' },
    { icon: Scale, title: 'Honest and factual', text: 'We check evidence before taking a complaint forward. We never invent government responses or results.' },
    { icon: Eye, title: 'Transparent progress', text: 'Every status change is recorded with a date, so you can see where your complaint stands.' },
    { icon: Users, title: 'For every villager', text: 'Simple English, large buttons and a short form that works on basic smartphones and slow networks.' },
  ]
  return (
    <>
      <PageHero eyebrow="About Gaon Saathi" title="We help villagers raise their voice without fear"
        lead="Gaon Saathi is an independent grievance-support platform for rural communities in India." />
      <section className="section">
        <div className="container-page grid gap-12 lg:grid-cols-12">
          <div className="prose-page lg:col-span-7">
            <h2 className="!mt-0">Why we exist</h2>
            <p>
              In many villages, people see public land being taken over, trees being cut, ration being stolen or development
              money disappearing. Most people know about it, but very few report it. The reason is simple: <strong>fear</strong>.
              Fear of powerful people, of threats, of conflict with neighbours.
            </p>
            <p>
              Gaon Saathi (meaning "village companion") gives people a safe way to report these problems. You do not need to
              register, and we never ask for your name, phone number or address.
            </p>
            <h2>What we do</h2>
            <ul>
              <li>Receive complaints about public resources and local governance, anonymously.</li>
              <li>Review each complaint and the evidence shared with it.</li>
              <li>Identify the right government department or official grievance channel.</li>
              <li>Where appropriate, submit the complaint to that authority and record the acknowledgement.</li>
              <li>Follow up and update the complaint status so the reporter can see progress.</li>
            </ul>
            <h2>What we are not</h2>
            <p>
              Gaon Saathi is <strong>not a government website</strong> and not a government authority. We cannot order any
              action, and submitting a complaint here does not automatically create an official government complaint or legal
              case. We do not provide legal representation. We are a support organisation that helps genuine complaints reach
              the people who can act on them.
            </p>
          </div>
          <aside className="lg:col-span-5">
            <div className="card card-pad sticky top-24">
              <h2 className="text-lg font-bold">Our promise to you</h2>
              <ul className="mt-5 space-y-4 text-sm">
                {[
                  [Ban, 'We will never ask who you are.'],
                  [ShieldCheck, 'We will protect the complaint and evidence you share.'],
                  [Handshake, 'We will review every complaint honestly.'],
                  [Megaphone, 'We will only say a complaint was forwarded after we really forwarded it.'],
                  [Sprout, 'We will never mark a complaint resolved without a real update.'],
                ].map(([Icon, text]) => (
                  <li key={text} className="flex gap-3"><Icon className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" /><span className="text-slate-700">{text}</span></li>
                ))}
              </ul>
              <Link to="/report" className="btn-primary mt-6 w-full">Report a Problem</Link>
            </div>
          </aside>
        </div>
      </section>
      <section className="section bg-slate-50 pt-0 sm:pt-0">
        <div className="container-page">
          <h2 className="section-title pt-16 text-center">Our values</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {values.map((v) => (
              <div key={v.title} className="card card-pad">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><v.icon className="h-5 w-5" aria-hidden="true" /></span>
                <h3 className="mt-4 font-bold">{v.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{v.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
