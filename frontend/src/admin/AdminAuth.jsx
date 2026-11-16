import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, setCsrfToken, setUnauthorizedHandler } from '../lib/api'
import { LoadingBlock } from '../components/ui'

const AuthContext = createContext(null)

export function AdminAuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')

  const refresh = useCallback(async () => {
    try {
      const data = await api('/api/admin/auth/me')
      setCsrfToken(data.csrf_token)
      setUser(data.user)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    setUnauthorizedHandler((message) => { setUser(null); setCsrfToken(null); setNotice(message) })
    return () => setUnauthorizedHandler(null)
  }, [refresh])

  const login = useCallback(async (username, password) => {
    const data = await api('/api/admin/auth/login', { method: 'POST', body: { username, password } })
    setCsrfToken(data.csrf_token)
    setUser(data.user)
    setNotice('')
    return data.user
  }, [])

  const logout = useCallback(async () => {
    try { await api('/api/admin/auth/logout', { method: 'POST' }) } catch { /* already signed out */ }
    setCsrfToken(null)
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, setUser, loading, login, logout, notice, setNotice, refresh }),
    [user, loading, login, logout, notice, refresh])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAdmin() {
  return useContext(AuthContext)
}

export function can(user, action) {
  if (!user) return false
  const rules = {
    write: ['admin', 'reviewer'],
    evidence: ['admin', 'reviewer'],
    export: ['admin', 'reviewer'],
    admin: ['admin'],
  }
  return (rules[action] || []).includes(user.role)
}

export function RequireAdmin({ children }) {
  const { user, loading } = useAdmin()
  const location = useLocation()
  if (loading) return <LoadingBlock label="Checking your session..." />
  if (!user) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />
  if (user.must_change_password && location.pathname !== '/admin/change-password') {
    return <Navigate to="/admin/change-password" replace />
  }
  return children
}
