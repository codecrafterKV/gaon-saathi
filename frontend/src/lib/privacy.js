// Client-side privacy helpers.

/**
 * Warn (never block) when text looks like it contains personal information.
 * Returns a list of human-readable warnings.
 */
export function detectPersonalInfo(text) {
  if (!text) return []
  const warnings = []
  const compact = text.replace(/[\s-]/g, '')
  if (/(?:\+?91|0)?[6-9]\d{9}(?!\d)/.test(compact)) warnings.push('a phone number')
  if (/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(text)) warnings.push('an email address')
  if (/(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)/.test(text)) warnings.push('an Aadhaar-like number')
  if (/\b(my name is|my name's|mera naam|mera nam)\b/i.test(text)) warnings.push('your name')
  if (/\b(my house|my home|mera ghar|i live at|i live in|my address)\b/i.test(text)) warnings.push('where you live')
  return warnings
}

/**
 * Re-draw a photo on a canvas before upload. This removes EXIF data such as
 * GPS location and phone model on the device itself, and makes large photos
 * smaller for slow networks. The server cleans photos again as a second layer.
 * Falls back to the original file if the browser cannot process it.
 */
export async function cleanImage(file, maxEdge = 2560) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return { file, cleaned: false }
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
    const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height))
    const width = Math.round(bitmap.width * scale)
    const height = Math.round(bitmap.height * scale)
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    ctx.drawImage(bitmap, 0, 0, width, height)
    bitmap.close?.()
    const type = file.type === 'image/png' ? 'image/png' : 'image/jpeg'
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, type, 0.88))
    if (!blob) return { file, cleaned: false }
    const ext = type === 'image/png' ? 'png' : 'jpg'
    // Generic name: the original phone file name can identify a person.
    return { file: new File([blob], `photo.${ext}`, { type, lastModified: 0 }), cleaned: true }
  } catch {
    return { file, cleaned: false }
  }
}

export function genericName(file, index) {
  const ext = (file.name.split('.').pop() || 'bin').toLowerCase().replace(/[^a-z0-9]/g, '')
  return `evidence-${index + 1}.${ext}`
}
