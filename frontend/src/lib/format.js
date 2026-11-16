const IST = 'Asia/Kolkata'

export function formatDate(value) {
  if (!value) return '-'
  const d = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00+05:30`) : new Date(value)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: IST })
}

export function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: IST,
  })
}

export function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatNumber(n) {
  return new Intl.NumberFormat('en-IN').format(n ?? 0)
}

export function monthLabel(ym) {
  const [y, m] = ym.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString('en-IN', { month: 'short', year: '2-digit', timeZone: 'UTC' })
}

export function dayLabel(iso) {
  return new Date(`${iso}T00:00:00+05:30`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: IST })
}

/** Format a tracking code as XXXX-XXXX-XXXX-XXXX while typing. */
export function formatTrackingInput(value) {
  const raw = value.toUpperCase().replace(/[^0-9A-Z]/g, '').slice(0, 16)
  return raw.match(/.{1,4}/g)?.join('-') ?? ''
}

export function formatComplaintIdInput(value) {
  return value.toUpperCase().replace(/[^0-9A-Z-]/g, '').slice(0, 20)
}
