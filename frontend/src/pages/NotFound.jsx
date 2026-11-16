import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { useDocumentTitle } from '../lib/hooks'

export default function NotFound() {
  useDocumentTitle('Page not found')
  return (
    <div className="container-page flex min-h-[60vh] flex-col items-center justify-center py-20 text-center">
      <span className="rounded-2xl bg-navy-50 p-4 text-navy-600"><Compass className="h-8 w-8" aria-hidden="true" /></span>
      <h1 className="mt-6 text-3xl font-extrabold">Page not found</h1>
      <p className="mt-2 max-w-md text-slate-600">The page you are looking for does not exist or has moved.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link to="/" className="btn-primary">Go to home</Link>
        <Link to="/report" className="btn-secondary">Report a Problem</Link>
      </div>
    </div>
  )
}
