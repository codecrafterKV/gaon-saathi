import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Menu, X, Megaphone } from 'lucide-react'
import Logo from './Logo'

export const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/report', label: 'Report a Problem' },
  { to: '/track', label: 'Track Complaint' },
  { to: '/about', label: 'About Us' },
  { to: '/how-it-works', label: 'How It Works' },
  { to: '/contact', label: 'Contact / Support' },
]

export default function SiteHeader() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()

  useEffect(() => { setOpen(false) }, [location.pathname])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const linkClass = ({ isActive }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'text-brand-700 bg-brand-50' : 'text-slate-600 hover:text-navy-900 hover:bg-slate-50'}`

  return (
    <header className={`sticky top-0 z-40 border-b bg-white/90 backdrop-blur transition ${scrolled ? 'border-slate-200 shadow-sm' : 'border-transparent'}`}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:shadow">
        Skip to content
      </a>
      <div className="container-page flex h-16 items-center justify-between gap-4 lg:h-[72px]">
        <Link to="/" className="shrink-0" aria-label="Gaon Saathi home"><Logo /></Link>
        <nav className="hidden items-center gap-0.5 xl:flex" aria-label="Main">
          {NAV.slice(0, 1).concat(NAV.slice(2)).map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>{item.label}</NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/report" className="btn-primary hidden sm:inline-flex">
            <Megaphone className="h-4 w-4" aria-hidden="true" /> Report a Problem
          </Link>
          <button
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl text-navy-900 hover:bg-slate-100 xl:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? 'Close menu' : 'Open menu'}
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>
      {open && (
        <nav id="mobile-menu" className="border-t border-slate-200 bg-white xl:hidden" aria-label="Mobile">
          <div className="container-page flex flex-col gap-1 py-3">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}
                className={({ isActive }) => `rounded-xl px-4 py-3 text-base font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-navy-900 hover:bg-slate-50'}`}>
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </header>
  )
}
