import { Link } from 'react-router-dom'
import { ShieldCheck, Lock, EyeOff } from 'lucide-react'
import Logo from './Logo'

export default function SiteFooter() {
  return (
    <footer className="bg-navy-950 text-navy-200">
      <div className="container-page py-14">
        <div className="grid gap-10 md:grid-cols-12">
          <div className="md:col-span-5">
            <Logo inverted showTagline size="lg" />
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-navy-300">
              A safe and simple way for villagers to report local problems without revealing who they are.
            </p>
            <ul className="mt-6 flex flex-wrap gap-2 text-xs">
              {[[EyeOff, 'No registration'], [Lock, 'Encrypted storage'], [ShieldCheck, 'No tracking']].map(([Icon, label]) => (
                <li key={label} className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1.5 ring-1 ring-white/10">
                  <Icon className="h-3.5 w-3.5 text-brand-300" aria-hidden="true" /> {label}
                </li>
              ))}
            </ul>
          </div>
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 md:col-span-7">
            <FooterCol title="Get started" links={[['/report', 'Report a Problem'], ['/track', 'Track Complaint'], ['/how-it-works', 'How It Works']]} />
            <FooterCol title="About" links={[['/about', 'About Us'], ['/contact', 'Contact / Support'], ['/#faq', 'FAQ']]} />
            <FooterCol title="Legal" links={[['/privacy', 'Privacy Policy'], ['/terms', 'Terms and Conditions'], ['/admin/login', 'Team login']]} />
          </div>
        </div>

        <div className="mt-12 rounded-2xl bg-white/5 p-5 text-xs leading-relaxed text-navy-300 ring-1 ring-white/10">
          <strong className="text-white">Disclaimer:</strong> Gaon Saathi is an independent grievance-support platform.
          It is <strong className="text-white">not an official government website</strong> and is not run by any government
          department. Submitting a complaint here is not the same as filing an official complaint with the government.
          Our team reviews complaints and, where appropriate, helps take them to the relevant authority. In an emergency,
          call <strong className="text-white">112</strong>.
        </div>

        <div className="mt-8 flex flex-col gap-2 border-t border-white/10 pt-6 text-xs text-navy-400 sm:flex-row sm:items-center sm:justify-between">
          <p>&copy; {new Date().getFullYear()} Gaon Saathi. Your Voice, Our Responsibility.</p>
          <p>Built for Tata InnoThon. No ads, no trackers, no third-party analytics.</p>
        </div>
      </div>
    </footer>
  )
}

function FooterCol({ title, links }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <ul className="mt-4 space-y-3 text-sm">
        {links.map(([to, label]) => (
          <li key={to}><Link to={to} className="transition hover:text-white">{label}</Link></li>
        ))}
      </ul>
    </div>
  )
}
