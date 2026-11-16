import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { UPLOAD_DEFAULTS } from './constants'

/** Adds the `is-visible` class when an element scrolls into view. */
export function useReveal() {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    if (!('IntersectionObserver' in window)) { el.classList.add('is-visible'); return undefined }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target) }
      })
    }, { threshold: 0.12 })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return ref
}

let configPromise = null
export function usePublicConfig() {
  const [config, setConfig] = useState({ uploads: UPLOAD_DEFAULTS, support: {} })
  useEffect(() => {
    let active = true
    configPromise = configPromise || api('/api/public/config').catch(() => null)
    configPromise.then((data) => { if (active && data) setConfig(data) })
    return () => { active = false }
  }, [])
  return config
}

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} | Gaon Saathi` : 'Gaon Saathi - Your Voice, Our Responsibility'
  }, [title])
}
