// Small fetch wrapper. All requests are same-origin; no third-party calls.

let csrfToken = null
export function setCsrfToken(token) { csrfToken = token }

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
    this.fields = data?.detail?.fields || {}
    this.code = data?.detail?.code
  }
}

export function errorMessage(data, fallback = 'Something went wrong. Please try again.') {
  const detail = data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (detail.message) return detail.message
  return fallback
}

let onUnauthorized = null
export function setUnauthorizedHandler(fn) { onUnauthorized = fn }

export async function api(path, { method = 'GET', body, headers = {}, signal } = {}) {
  const opts = { method, headers: { Accept: 'application/json', ...headers }, credentials: 'same-origin', signal }
  if (body !== undefined && !(body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  } else if (body instanceof FormData) {
    opts.body = body
  }
  if (method !== 'GET' && path.startsWith('/api/admin') && csrfToken) {
    opts.headers['X-CSRF-Token'] = csrfToken
  }
  let response
  try {
    response = await fetch(path, opts)
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError('Could not connect. Please check your internet connection and try again.', 0, null)
  }
  const isJson = (response.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await response.json().catch(() => null) : null
  if (!response.ok) {
    if (response.status === 401 && path.startsWith('/api/admin') && !path.endsWith('/login') && onUnauthorized) {
      onUnauthorized(errorMessage(data, 'Please sign in.'))
    }
    throw new ApiError(errorMessage(data), response.status, data)
  }
  return data
}

/** Upload with progress (fetch cannot report upload progress). */
export function uploadForm(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', path)
    xhr.setRequestHeader('Accept', 'application/json')
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total) }
    xhr.onload = () => {
      let data = null
      try { data = JSON.parse(xhr.responseText) } catch { /* not JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data)
      else reject(new ApiError(errorMessage(data, xhr.status === 413
        ? 'The upload is too large. Please remove some files and try again.'
        : 'Something went wrong. Please try again.'), xhr.status, data))
    }
    xhr.onerror = () => reject(new ApiError('Upload failed. Please check your internet connection and try again.', 0, null))
    xhr.ontimeout = () => reject(new ApiError('The upload took too long. Please try again with smaller files.', 0, null))
    xhr.timeout = 10 * 60 * 1000
    xhr.send(formData)
  })
}
