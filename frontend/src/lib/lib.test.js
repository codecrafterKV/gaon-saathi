import { describe, expect, it } from 'vitest'
import { sha256 } from '@noble/hashes/sha256'
import { detectPersonalInfo } from './privacy'
import { leadingZeroBits, solveChallenge } from './pow'
import { formatTrackingInput, formatComplaintIdInput, formatBytes } from './format'

describe('detectPersonalInfo', () => {
  it('finds phone numbers, emails and Aadhaar-like numbers', () => {
    expect(detectPersonalInfo('Call me on 98765 43210')).toContain('a phone number')
    expect(detectPersonalInfo('write to ram@example.com')).toContain('an email address')
    expect(detectPersonalInfo('aadhaar 1234 5678 9012')).toContain('an Aadhaar-like number')
    expect(detectPersonalInfo('My name is Sunita')).toContain('your name')
  })
  it('does not warn on normal descriptions', () => {
    expect(detectPersonalInfo('The main road near the school has big potholes since 2 months.')).toEqual([])
    expect(detectPersonalInfo('Ration shop gave 4 kg instead of 5 kg.')).toEqual([])
  })
})

describe('proof of work', () => {
  it('counts leading zero bits', () => {
    expect(leadingZeroBits(new Uint8Array([0, 0x0f]))).toBe(12)
    expect(leadingZeroBits(new Uint8Array([0x80]))).toBe(0)
    expect(leadingZeroBits(new Uint8Array([0x01]))).toBe(7)
  })
  it('solves a challenge the same way the server verifies it', async () => {
    const challenge = 'v1.test.challenge'
    const solution = await solveChallenge(challenge, 10)
    const digest = sha256(new TextEncoder().encode(`${challenge}:${solution}`))
    expect(leadingZeroBits(digest)).toBeGreaterThanOrEqual(10)
  })
})

describe('formatting', () => {
  it('formats tracking codes', () => {
    expect(formatTrackingInput('abcd efgh-jkmn pqrs extra')).toBe('ABCD-EFGH-JKMN-PQRS')
    expect(formatComplaintIdInput(' gs-2026-ab12 ')).toBe('GS-2026-AB12')
  })
  it('formats sizes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2 * 1024 * 1024)).toBe('2.0 MB')
  })
})
