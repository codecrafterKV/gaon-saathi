import { useState } from 'react'
import { KeyRound } from 'lucide-react'
import { api } from '../lib/api'
import { Alert, Spinner } from '../components/ui'

export default function ChangePasswordForm({ onDone }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (next.length < 12) { setError('The new password must be at least 12 characters long.'); return }
    if (next !== repeat) { setError('The new passwords do not match.'); return }
    setBusy(true)
    try {
      const data = await api('/api/admin/auth/change-password', { method: 'POST', body: { current_password: current, new_password: next } })
      setSuccess('Your password was changed. Other sessions were signed out.')
      setCurrent(''); setNext(''); setRepeat('')
      onDone?.(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div>
        <label htmlFor="cp-current" className="label">Current password</label>
        <input id="cp-current" type="password" className="input" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
      </div>
      <div>
        <label htmlFor="cp-new" className="label">New password</label>
        <input id="cp-new" type="password" className="input" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        <p className="hint">At least 12 characters. A long phrase of several words is strong and easy to remember.</p>
      </div>
      <div>
        <label htmlFor="cp-repeat" className="label">Repeat new password</label>
        <input id="cp-repeat" type="password" className="input" autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} />
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {success && <Alert tone="success">{success}</Alert>}
      <button type="submit" className="btn-navy" disabled={busy}>
        {busy ? <Spinner className="h-4 w-4" /> : <KeyRound className="h-4 w-4" />} Change password
      </button>
    </form>
  )
}
