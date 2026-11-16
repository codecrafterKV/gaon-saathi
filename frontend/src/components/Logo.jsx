import { useId } from 'react'

/** The Gaon Saathi mark: a protective shield holding a village home on green
 * fields, with voice waves rising from the roof (speaking up safely). */
export function LogoMark({ className = 'h-10 w-10', title = 'Gaon Saathi' }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg viewBox="0 0 64 64" className={className} role="img" aria-label={title}>
      <defs>
        <clipPath id={`${id}-clip`}>
          <path d="M32 3.5 54.5 11.5V29c0 14.8-9.5 25.8-22.5 31.5C19 54.8 9.5 43.8 9.5 29V11.5Z" />
        </clipPath>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1f3d64" />
          <stop offset="1" stopColor="#0b1f3a" />
        </linearGradient>
      </defs>
      <path d="M32 3.5 54.5 11.5V29c0 14.8-9.5 25.8-22.5 31.5C19 54.8 9.5 43.8 9.5 29V11.5Z" fill={`url(#${id}-bg)`} />
      <g clipPath={`url(#${id}-clip)`}>
        <path d="M4 42.5c13-6 43-6 56 0V64H4Z" fill="#0b8f4a" />
        <path d="M4 47.5c16-5 40 2.5 56-1.5V64H4Z" fill="#14ae5c" />
      </g>
      <path d="M27.76 18.26a6 6 0 0 1 8.48 0M24.22 14.72a11 11 0 0 1 15.56 0" fill="none" stroke="#34cb7b" strokeWidth="2.6" strokeLinecap="round" />
      <rect x="24.5" y="30" width="15" height="13" rx="1.2" fill="#fff" />
      <path d="M20.5 32 32 22.5 43.5 32" fill="none" stroke="#fff" strokeWidth="3.6" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="29.6" y="35" width="4.8" height="8" rx="2.4" fill="#0b1f3a" />
    </svg>
  )
}

export default function Logo({ inverted = false, showTagline = false, size = 'md' }) {
  const mark = size === 'lg' ? 'h-14 w-14' : size === 'sm' ? 'h-8 w-8' : 'h-10 w-10'
  const word = size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-base' : 'text-lg'
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark className={`${mark} shrink-0 drop-shadow-sm`} />
      <span className="flex flex-col leading-none">
        <span className={`font-display font-extrabold tracking-tight ${word} ${inverted ? 'text-white' : 'text-navy-900'}`}>
          GAON <span className={inverted ? 'text-brand-300' : 'text-brand-600'}>SAATHI</span>
        </span>
        {showTagline && (
          <span className={`mt-1 text-[11px] font-medium tracking-wide ${inverted ? 'text-navy-200' : 'text-slate-500'}`}>
            Your Voice, Our Responsibility.
          </span>
        )}
      </span>
    </span>
  )
}
