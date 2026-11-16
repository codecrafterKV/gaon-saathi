import { useCallback, useEffect, useState } from 'react'
import { Database, KeyRound, ShieldCheck, Trash2, UserPlus, Users, Clock, FlaskConical, UserRound, Lock, Unlock } from 'lucide-react'
import { api } from '../../lib/api'
import { formatDateTime, formatNumber } from '../../lib/format'
import { useDocumentTitle } from '../../lib/hooks'
import { Alert, Modal, Spinner } from '../../components/ui'
import { AdminPageHeader } from '../AdminLayout'
import { can, useAdmin } from '../AdminAuth'
import ChangePasswordForm from '../ChangePasswordForm'

export default function Settings() {
  useDocumentTitle('Settings')
  const { user, setUser } = useAdmin()
  const isAdmin = can(user, 'admin')
  const [info, setInfo] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(() => {
    if (isAdmin) api('/api/admin/settings').then(setInfo).catch((err) => setError(err.message))
  }, [isAdmin])
  useEffect(() => { load() }, [load])

  return (
    <div>
      <AdminPageHeader title="Settings" description="Your account, team members, data retention and system security." />
      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      <div className="grid gap-6 xl:grid-cols-2">
        <Section icon={UserRound} title="My account">
          <dl className="mb-5 grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-xs text-slate-500">Username</dt><dd className="font-semibold text-navy-900">{user.username}</dd></div>
            <div><dt className="text-xs text-slate-500">Role</dt><dd className="font-semibold text-navy-900">{user.role_label}</dd></div>
          </dl>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold"><KeyRound className="h-4 w-4" /> Change password</h3>
          <ChangePasswordForm onDone={setUser} />
        </Section>
        {isAdmin && info && <SystemSection info={info} />}
        {isAdmin && <UsersSection currentId={user.id} />}
        {isAdmin && info && <RetentionSection info={info} onChange={load} />}
        {isAdmin && info && <DemoSection info={info} onChange={load} />}
        {!isAdmin && <Alert tone="info">Team management, data retention and demo data settings are available to administrators only.</Alert>}
      </div>
    </div>
  )
}

function Section({ icon: Icon, title, children, description }) {
  return (
    <section className="card card-pad">
      <h2 className="flex items-center gap-2 text-base font-bold"><Icon className="h-5 w-5 text-brand-600" /> {title}</h2>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      <div className="mt-5">{children}</div>
    </section>
  )
}

function SystemSection({ info }) {
  const s = info.system
  const rows = [
    ['Environment', s.environment],
    ['Database', s.database],
    ['Evidence storage', s.storage_backend],
    ['Evidence encryption', s.evidence_encryption],
    ['Text encryption', s.field_encryption],
    ['Malware scanning', s.malware_scanner],
    ['Video metadata removal', s.video_metadata_removal],
    ['Secure cookies (HTTPS)', s.secure_cookies ? 'On' : 'Off (development)'],
    ['HSTS', s.hsts ? 'On' : 'Off'],
    ['Session timeout', `${s.session_idle_minutes} min idle / ${s.session_max_hours} h max`],
    ['Upload limits', `${s.upload_limits.files} files, photos ${s.upload_limits.image_mb} MB, videos ${s.upload_limits.video_mb} MB, PDF ${s.upload_limits.pdf_mb} MB`],
  ]
  const warnings = []
  if (s.environment !== 'production') warnings.push('Running in development mode.')
  if (!s.secure_cookies) warnings.push('Secure cookies are off. Enable HTTPS and COOKIE_SECURE in production.')
  if (s.malware_scanner === 'Not configured') warnings.push('No malware scanner is configured. Evidence files are not virus scanned.')
  return (
    <Section icon={ShieldCheck} title="Security status" description="Read-only. Configured through environment variables on the server.">
      <dl className="divide-y divide-slate-100 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-slate-500">{k}</dt><dd className="text-right font-medium text-navy-900">{v}</dd></div>
        ))}
      </dl>
      {warnings.length > 0 && <Alert tone="warning" className="mt-4"><ul className="list-disc space-y-1 pl-4">{warnings.map((w) => <li key={w}>{w}</li>)}</ul></Alert>}
    </Section>
  )
}

function UsersSection({ currentId }) {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const load = useCallback(() => api('/api/admin/users').then((d) => { setUsers(d.items); setRoles(d.roles) }).catch((err) => setError(err.message)), [])
  useEffect(() => { load() }, [load])

  const patch = async (id, body) => {
    setError('')
    try { await api(`/api/admin/users/${id}`, { method: 'PATCH', body }); load() } catch (err) { setError(err.message) }
  }

  return (
    <Section icon={Users} title="Team members" description="Only administrators can add team members. New members must change their temporary password at first login.">
      <div className="mb-4"><button type="button" className="btn-primary btn-sm" onClick={() => setModal({ mode: 'create' })}><UserPlus className="h-4 w-4" /> Add team member</button></div>
      {error && <Alert tone="error" className="mb-3">{error}</Alert>}
      <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200">
        {users.map((u) => (
          <li key={u.id} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="flex items-center gap-2 font-semibold text-navy-900">
                {u.username} {u.id === currentId && <span className="text-xs font-normal text-slate-400">(you)</span>}
                {!u.is_active && <span className="rounded bg-slate-100 px-1.5 text-[11px] font-medium text-slate-600">Inactive</span>}
                {u.locked && <span className="rounded bg-red-50 px-1.5 text-[11px] font-medium text-red-700">Locked</span>}
                {u.must_change_password && <span className="rounded bg-amber-50 px-1.5 text-[11px] font-medium text-amber-800">Temporary password</span>}
              </p>
              <p className="text-xs text-slate-500">Last login: {u.last_login_at ? formatDateTime(u.last_login_at) : 'never'}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select className="input !w-auto py-1.5 text-xs" value={u.role} disabled={u.id === currentId} onChange={(e) => patch(u.id, { role: e.target.value })} aria-label={`Role of ${u.username}`}>
                {roles.map((r) => <option key={r.value} value={r.value}>{r.value}</option>)}
              </select>
              {u.id !== currentId && (
                <>
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setModal({ mode: 'reset', user: u })}><KeyRound className="h-3.5 w-3.5" /> Reset</button>
                  <button type="button" className="btn-secondary btn-sm" onClick={() => patch(u.id, { is_active: !u.is_active })}>
                    {u.is_active ? <><Lock className="h-3.5 w-3.5" /> Deactivate</> : <><Unlock className="h-3.5 w-3.5" /> Activate</>}
                  </button>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
      {modal && <UserModal modal={modal} roles={roles} onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />}
    </Section>
  )
}

function UserModal({ modal, roles, onClose, onSaved }) {
  const creating = modal.mode === 'create'
  const [username, setUsername] = useState('')
  const [role, setRole] = useState('reviewer')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const save = async () => {
    setBusy(true); setError('')
    try {
      if (creating) await api('/api/admin/users', { method: 'POST', body: { username, role, temporary_password: password } })
      else await api(`/api/admin/users/${modal.user.id}`, { method: 'PATCH', body: { temporary_password: password } })
      onSaved()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return (
    <Modal open onClose={onClose} title={creating ? 'Add team member' : `Reset password for ${modal.user.username}`}
      footer={<><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button type="button" className="btn-primary" onClick={save} disabled={busy}>{busy && <Spinner className="h-4 w-4" />} Save</button></>}>
      <div className="space-y-4">
        {creating && (
          <>
            <div><label htmlFor="u-name" className="label">Username</label><input id="u-name" className="input" value={username} onChange={(e) => setUsername(e.target.value.toLowerCase())} autoComplete="off" />
              <p className="hint">Lowercase letters, numbers, dot, dash or underscore. Do not use real names if not needed.</p></div>
            <div><label htmlFor="u-role" className="label">Role</label>
              <select id="u-role" className="input" value={role} onChange={(e) => setRole(e.target.value)}>{roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select></div>
          </>
        )}
        <div><label htmlFor="u-pass" className="label">Temporary password</label><input id="u-pass" type="text" className="input font-mono" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
          <p className="hint">At least 12 characters. Share it privately; the member must change it at first login.</p></div>
        {!creating && <Alert tone="info">This signs the member out everywhere and unlocks the account.</Alert>}
        {error && <Alert tone="error">{error}</Alert>}
      </div>
    </Modal>
  )
}

function RetentionSection({ info, onChange }) {
  const [days, setDays] = useState(info.settings.retention_days)
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const save = async () => {
    setBusy(true); setMsg(null)
    try { await api('/api/admin/settings', { method: 'PUT', body: { retention_days: Number(days) } }); setMsg({ tone: 'success', text: 'Retention period saved.' }); onChange() } catch (err) { setMsg({ tone: 'error', text: err.message }) } finally { setBusy(false) }
  }
  const purge = async () => {
    setBusy(true); setMsg(null); setConfirm(false)
    try { const r = await api('/api/admin/maintenance/purge', { method: 'POST' }); setMsg({ tone: 'success', text: `${r.removed} expired complaint(s) deleted.` }); onChange() } catch (err) { setMsg({ tone: 'error', text: err.message }) } finally { setBusy(false) }
  }
  return (
    <Section icon={Clock} title="Data retention" description="Resolved, rejected and closed complaints are permanently deleted (with their evidence) after this period.">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="ret" className="label">Keep finished complaints for (days)</label>
          <input id="ret" type="number" min={30} max={3650} className="input w-40" value={days} onChange={(e) => setDays(e.target.value)} />
        </div>
        <button type="button" className="btn-navy" onClick={save} disabled={busy}>Save</button>
        <button type="button" className="btn-secondary" onClick={() => setConfirm(true)} disabled={busy}><Trash2 className="h-4 w-4" /> Run purge now</button>
      </div>
      <p className="hint mt-3">Schedule <code className="rounded bg-slate-100 px-1">python -m app.cli purge-expired</code> daily on the server to apply this automatically.</p>
      {msg && <Alert tone={msg.tone} className="mt-4">{msg.text}</Alert>}
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Run retention purge?"
        footer={<><button type="button" className="btn-secondary" onClick={() => setConfirm(false)}>Cancel</button><button type="button" className="btn-danger" onClick={purge}>Delete expired complaints</button></>}>
        <p className="text-sm text-slate-600">Finished complaints older than {info.settings.retention_days} days will be permanently deleted, including evidence. This cannot be undone.</p>
      </Modal>
    </Section>
  )
}

function DemoSection({ info, onChange }) {
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const run = async (kind) => {
    setBusy(kind); setMsg(null); setConfirm(null)
    try {
      const r = await api(`/api/admin/maintenance/${kind}`, { method: 'POST' })
      setMsg(kind === 'seed-demo'
        ? { tone: 'success', text: `Loaded ${r.complaints} demo complaints. Example to track: ${r.sample_tracking[0]?.complaint_id} / ${r.sample_tracking[0]?.tracking_token}` }
        : { tone: 'success', text: `Removed ${r.complaints} demo complaints and ${r.authorities} demo authorities.` })
      onChange()
    } catch (err) { setMsg({ tone: 'error', text: err.message }) } finally { setBusy('') }
  }
  return (
    <Section icon={FlaskConical} title="Demo data" description="Fictional sample complaints for demonstrations. Always marked DEMO and kept separate from real complaints.">
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div className="rounded-xl bg-slate-50 p-3"><dt className="flex items-center gap-1.5 text-xs text-slate-500"><Database className="h-3.5 w-3.5" /> Live complaints</dt><dd className="text-xl font-extrabold text-navy-900">{formatNumber(info.data.live_complaints)}</dd></div>
        <div className="rounded-xl bg-amber-50 p-3"><dt className="flex items-center gap-1.5 text-xs text-amber-800"><FlaskConical className="h-3.5 w-3.5" /> Demo complaints</dt><dd className="text-xl font-extrabold text-navy-900">{formatNumber(info.data.demo_complaints)}</dd></div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" className="btn-secondary" disabled={!!busy} onClick={() => setConfirm('seed-demo')}>{busy === 'seed-demo' && <Spinner className="h-4 w-4" />} {info.data.demo_complaints ? 'Reload demo data' : 'Load demo data'}</button>
        <button type="button" className="btn-secondary text-red-700" disabled={!!busy || !info.data.demo_complaints} onClick={() => setConfirm('clear-demo')}>{busy === 'clear-demo' && <Spinner className="h-4 w-4" />} Remove all demo data</button>
      </div>
      {msg && <Alert tone={msg.tone} className="mt-4">{msg.text}</Alert>}
      <Modal open={!!confirm} onClose={() => setConfirm(null)} title={confirm === 'seed-demo' ? 'Load demo data?' : 'Remove demo data?'}
        footer={<><button type="button" className="btn-secondary" onClick={() => setConfirm(null)}>Cancel</button><button type="button" className="btn-primary" onClick={() => run(confirm)}>Continue</button></>}>
        <p className="text-sm text-slate-600">{confirm === 'seed-demo'
          ? 'Existing demo data will be replaced with fresh sample complaints. Real complaints are not affected.'
          : 'All demo complaints and demo authority records will be deleted. Real complaints are not affected.'}</p>
      </Modal>
    </Section>
  )
}
