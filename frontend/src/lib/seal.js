// The Urbora seal (logo mark), vector master: a thin outer ring, a turmeric sun with fine rays,
// a two-leaf seedling on the horizon, ploughed furrows converging on it (brand/BRAND-CORE.md §5).
// seal({ detail }) returns SVG markup on a 200-unit grid; detail 'full' from 48px up, 'simple' below.
// Pure function: used by BrandMark.jsx and by brand/scripts/seal.mjs to write the logo files.

const f = (v) => +v.toFixed(2)

export function seal({ detail = 'full', ink = '#0D3B2E', sun = '#F2A231', ground = '#FAF5EA', ring = true, sprout } = {}) {
  sprout = sprout || ink
  const C = 100, HZ = 114, R = ring ? 86 : 96
  const parts = []
  const clip = `seal-clip-${detail}-${ring ? 'r' : 'n'}`
  parts.push(`<defs><clipPath id="${clip}"><circle cx="${C}" cy="${C}" r="${R}"/></clipPath></defs>`)
  if (ring) {
    parts.push(`<circle cx="${C}" cy="${C}" r="97" fill="${ground}" stroke="${ink}" stroke-width="${detail === 'full' ? 3.2 : 6}"/>`)
    if (detail === 'full') parts.push(`<circle cx="${C}" cy="${C}" r="${R + 3}" fill="none" stroke="${ink}" stroke-width="1.2"/>`)
  } else {
    parts.push(`<circle cx="${C}" cy="${C}" r="${R}" fill="${ground}"/>`)
  }
  const g = []
  // sun rays: fine lines fanning over the upper half
  if (detail === 'full') {
    for (let i = 0; i <= 44; i++) {
      const a = Math.PI + (i / 44) * Math.PI
      const r1 = 49, r2 = 49 + (i % 2 ? 22 : 34)
      g.push(`<path d="M${f(C + Math.cos(a) * r1)} ${f(HZ + Math.sin(a) * r1)}L${f(C + Math.cos(a) * r2)} ${f(HZ + Math.sin(a) * r2)}" stroke="${sun}" stroke-width="1.1" stroke-linecap="round"/>`)
    }
  }
  // the sun
  g.push(`<path d="M${C - 44} ${HZ}A44 44 0 0 1 ${C + 44} ${HZ}Z" fill="${sun}"/>`)
  if (detail === 'full') { // engraved arcs inside the sun, lower half only, for depth
    for (const rr of [30, 36, 41]) g.push(`<path d="M${C - rr} ${HZ - 2}A${rr} ${rr} 0 0 1 ${C + rr} ${HZ - 2}" fill="none" stroke="${ink}" stroke-opacity="0.18" stroke-width="0.9"/>`)
  }
  // furrows: 9 dark stripes, symmetric about the centre, fanning from the vanishing point
  const VP = [C, HZ + 1], bottom = 200, w = 21
  for (let j = -4; j <= 4; j++) {
    const x1 = C + (2 * j - 0.5) * w, x2 = C + (2 * j + 0.5) * w
    g.push(`<path d="M${VP[0]} ${VP[1]}L${x1} ${bottom}L${x2} ${bottom}Z" fill="${ink}"/>`)
  }
  // horizon line
  g.push(`<rect x="0" y="${HZ - 1.5}" width="200" height="${detail === 'full' ? 3 : 4}" fill="${ink}"/>`)
  // seedling: stem and two leaves, standing on the horizon in front of the sun
  const L = (d) => `<path d="${d}" fill="${sprout}"/>`
  g.push(L(`M${C - 2.3} ${HZ}V${HZ - 24}a2.3 2.3 0 0 1 4.6 0V${HZ}Z`))
  g.push(L(`M${C} ${HZ - 14}C${C - 1.2} ${HZ - 26} ${C - 9} ${HZ - 32} ${C - 21} ${HZ - 31}C${C - 20} ${HZ - 19} ${C - 11.5} ${HZ - 13} ${C} ${HZ - 14}Z`))
  g.push(L(`M${C} ${HZ - 19}C${C + 1.2} ${HZ - 32} ${C + 10} ${HZ - 39} ${C + 23.5} ${HZ - 38}C${C + 22.5} ${HZ - 25} ${C + 12.5} ${HZ - 18} ${C} ${HZ - 19}Z`))
  if (detail === 'full') { // leaf midribs
    g.push(`<path d="M${C - 2} ${HZ - 16}Q${C - 9} ${HZ - 23} ${C - 18} ${HZ - 29}" fill="none" stroke="${sun}" stroke-width="0.9" stroke-linecap="round"/>`)
    g.push(`<path d="M${C + 2} ${HZ - 21}Q${C + 11} ${HZ - 29} ${C + 21} ${HZ - 36}" fill="none" stroke="${sun}" stroke-width="0.9" stroke-linecap="round"/>`)
  }
  parts.push(`<g clip-path="url(#${clip})">${g.join('')}</g>`)
  return parts.join('')
}

export const svgDoc = (inner, size = 200) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 200 200">${inner}</svg>`
