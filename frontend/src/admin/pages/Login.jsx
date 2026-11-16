import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { LockKeyhole, LogIn, ShieldCheck, Eye, EyeOff } from 'lucide-react'
import Logo from '../../components/Logo'
import { Alert, Spinner } from '../../components/ui'
import { useDocumentTitle } from '../../lib/hooks'
import { useAdmin } from '../AdminAuth'

export default function Login() {
  useDocumentTitle('Team Login')
  const { user, login, notice } = useAdmin()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={user.must_change_password ? '/admin/change-password' : (location.state?.from || '/admin')} replace />

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!username || !password) { setError('Please enter your username and password.'); return }
    setBusy(true)
    try {
      const u = await login(username.trim(), password)
      navigate(u.must_change_password ? '/admin/change-password' : (location.state?.from || '/admin'), { replace: true })
    } catch (err) {
      setError(err.message)
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-navy-900 lg:block">
        <div className="absolute inset-0 bg-grid" aria-hidden="true" />
        <div className="absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-brand-500/25 blur-3xl" aria-hidden="true" />
        <div className="relative flex h-full flex-col justify-between p-12">
          <Logo inverted showTagline size="lg" />
          <div>
            <h2 className="text-4xl font-extrabold leading-tight text-white text-balance">Every complaint is a person who trusted us.</h2>
            <p className="mt-4 max-w-md text-navy-200">Handle each one with care: verify facts, record every step, and never share more than needed.</p>
          </div>
          <p className="flex items-center gap-2 text-sm text-navy-300"><ShieldCheck className="h-4 w-4 text-brand-300" /> All actions in this dashboard are recorded in the audit log.</p>
        </div>
      </div>
      <div className="flex items-center justify-center bg-slate-50 px-4 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden"><Logo showTagline /></div>
          <div className="card p-6 sm:p-8">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-navy-900 text-brand-300"><LockKeyhole className="h-6 w-6" /></span>
            <h1 className="mt-5 text-2xl font-extrabold">Team login</h1>
            <p className="mt-1 text-sm text-slate-500">For authorised Gaon Saathi administrators only. There is no public registration.</p>
            {notice && !error && <Alert tone="info" className="mt-5">{notice}</Alert>}
            <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
              <div>
                <label htmlFor="username" className="label">Username</label>
                <input id="username" className="input" autoComplete="username" autoCapitalize="none" spellCheck={false}
                  value={username} onChange={(e) => setUsername(e.target.value)} maxLength={50} />
              </div>
              <div>
                <label htmlFor="password" className="label">Password</label>
                <div className="relative">
                  <input id="password" type={show ? 'text' : 'password'} className="input pr-11" autoComplete="current-password"
                    value={password} onChange={(e) => setPassword(e.target.value)} maxLength={128} />
                  <button type="button" onClick={() => setShow((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 hover:text-navy-900"
                    aria-label={show ? 'Hide password' : 'Show password'}>
                    {show ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              {error && <Alert tone="error">{error}</Alert>}
              <button type="submit" className="btn-navy w-full" disabled={busy}>
                {busy ? <><Spinner className="h-4 w-4" /> Signing in...</> : <><LogIn className="h-4 w-4" /> Sign in</>}
              </button>
            </form>
            <p className="mt-6 text-xs text-slate-500">After 5 failed attempts the account is locked for 15 minutes. Sessions end after 30 minutes of inactivity.</p>
          </div>
          <p className="mt-6 text-center text-sm"><Link to="/" className="font-medium text-brand-700 hover:underline">Back to the public website</Link></p>
        </div>
      </div>
    </div>
  )
}
