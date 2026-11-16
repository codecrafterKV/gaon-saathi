import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Scroll to top on navigation, or to an #anchor if present. */
export default function ScrollManager() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1))
      if (el) { setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50); return }
    }
    window.scrollTo(0, 0)
  }, [pathname, hash])
  return null
}
