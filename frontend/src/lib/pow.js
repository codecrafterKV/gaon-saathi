// Privacy-friendly anti-spam check (no third-party CAPTCHA).
// The browser finds a number so that SHA-256("<challenge>:<number>") starts
// with `difficulty` zero bits. Work is done in small slices so the page stays
// responsive on low-end phones.
import { sha256 } from '@noble/hashes/sha256'
import { api } from './api'

const encoder = new TextEncoder()

export function leadingZeroBits(bytes) {
  let bits = 0
  for (const byte of bytes) {
    if (byte === 0) { bits += 8; continue }
    bits += Math.clz32(byte) - 24
    break
  }
  return bits
}

export function solveChallenge(challenge, difficulty, { signal, sliceMs = 30 } = {}) {
  return new Promise((resolve, reject) => {
    let counter = 0
    const step = () => {
      if (signal?.aborted) { reject(new DOMException('Aborted', 'AbortError')); return }
      const until = performance.now() + sliceMs
      while (performance.now() < until) {
        for (let i = 0; i < 500; i += 1) {
          const digest = sha256(encoder.encode(`${challenge}:${counter}`))
          if (leadingZeroBits(digest) >= difficulty) { resolve(String(counter)); return }
          counter += 1
        }
      }
      setTimeout(step, 0)
    }
    step()
  })
}

// The server rejects challenges used within a few seconds of being issued
// (real people take longer than bots); wait out that minimum if needed.
const MIN_CHALLENGE_AGE_MS = 3500

/** Fetch a fresh challenge and solve it. Resolves to form fields. */
export async function getSolvedChallenge(signal) {
  const issuedAt = Date.now()
  const { challenge, difficulty } = await api('/api/public/challenge', { signal })
  const solution = await solveChallenge(challenge, difficulty, { signal })
  const wait = MIN_CHALLENGE_AGE_MS - (Date.now() - issuedAt)
  if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait))
  return { pow_challenge: challenge, pow_solution: solution }
}
