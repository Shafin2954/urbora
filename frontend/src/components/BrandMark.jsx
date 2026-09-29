import { useMemo } from 'react'
import { seal } from '../lib/seal.js'
import { BRAND_NAME, BRAND_NAME_BN, BRAND_TAGLINE_BN } from '../branding.js'

// The Urbora seal (brand/BRAND-CORE.md §5), drawn from the same master as the logo files
// (lib/seal.js). Below 48px the simple cut (no rays) keeps it legible on a cheap screen.
export default function BrandMark({ size = 36, title }) {
  const inner = useMemo(() => seal({ detail: size >= 48 ? 'full' : 'simple' }), [size])
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" className="brand-mark"
      role={title ? 'img' : undefined} aria-hidden={title ? undefined : 'true'} aria-label={title}
      dangerouslySetInnerHTML={{ __html: inner }} />
  )
}

// Seal + Bangla wordmark (+ tagline). Bangla is always the larger name; Latin is small caps.
export function Lockup({ size = 40, tagline = true, latin = false, tone = 'light' }) {
  return (
    <span className={`lockup lockup-${tone}`}>
      <BrandMark size={size} />
      <span className="lockup-words">
        <b className="lockup-bn">{BRAND_NAME_BN}</b>
        {tagline && <em className="lockup-tag">{BRAND_TAGLINE_BN}</em>}
        {latin && <small className="lockup-en">{BRAND_NAME.toUpperCase()}</small>}
      </span>
    </span>
  )
}
