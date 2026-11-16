import { Navigate, Route, Routes } from 'react-router-dom'
import { AdminAuthProvider, RequireAdmin, can, useAdmin } from './AdminAuth'
import AdminLayout from './AdminLayout'
import Login from './pages/Login'
import ForcePasswordChange from './pages/ForcePasswordChange'
import Dashboard from './pages/Dashboard'
import Complaints from './pages/Complaints'
import ComplaintDetail from './pages/ComplaintDetail'
import Authorities from './pages/Authorities'
import AuditLog from './pages/AuditLog'
import Settings from './pages/Settings'

function AdminOnly({ children }) {
  const { user } = useAdmin()
  return can(user, 'admin') ? children : <Navigate to="/admin" replace />
}

export default function AdminApp() {
  return (
    <AdminAuthProvider>
      <Routes>
        <Route path="login" element={<Login />} />
        <Route path="change-password" element={<RequireAdmin><ForcePasswordChange /></RequireAdmin>} />
        <Route element={<RequireAdmin><AdminLayout /></RequireAdmin>}>
          <Route index element={<Dashboard />} />
          <Route path="complaints" element={<Complaints />} />
          <Route path="complaints/:publicId" element={<ComplaintDetail />} />
          <Route path="authorities" element={<Authorities />} />
          <Route path="audit" element={<AdminOnly><AuditLog /></AdminOnly>} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
      </Routes>
    </AdminAuthProvider>
  )
}
