import { useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import Logo from '../../components/Logo'
import { Alert } from '../../components/ui'
import { useDocumentTitle } from '../../lib/hooks'
import { useAdmin } from '../AdminAuth'
import ChangePasswordForm from '../ChangePasswordForm'

export default function ForcePasswordChange() {
  useDocumentTitle('Set a new password')
  const { setUser, logout } = useAdmin()
  const navigate = useNavigate()
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6"><Logo /></div>
        <div className="card p-6 sm:p-8">
          <h1 className="text-2xl font-extrabold">Set a new password</h1>
          <Alert tone="warning" icon={ShieldAlert} className="mt-4">
            Your account was created with a temporary password. Choose your own password before continuing.
          </Alert>
          <div className="mt-6">
            <ChangePasswordForm onDone={(user) => { setUser(user); navigate('/admin', { replace: true }) }} />
          </div>
          <button type="button" className="mt-6 text-sm font-medium text-slate-500 hover:text-navy-900" onClick={async () => { await logout(); navigate('/admin/login') }}>
            Sign out instead
          </button>
        </div>
      </div>
    </div>
  )
}
