// Builds the three Urbor logo-mark concepts as SVG symbols (64-unit grid).
// Usage: node brand/scripts/marks.mjs <outdir>
// Colours: currentColor = primary ink, .acc = turmeric accent, .on = the ground colour behind the mark.
import { writeFileSync, mkdirSync } from 'node:fs'

const out = process.argv[2] || 'marks'
mkdirSync(out, { recursive: true })
const f = (v) => +v.toFixed(2)

// a filled grain (almond) pointing along angle a, base at (x, y)
function grain(x, y, a, len, w, cls = '') {
  const c = Math.cos(a), s = Math.sin(a)
  const P = (u, v) => [f(x + u * c - v * s), f(y + u * s + v * c)]
  const t = P(len, 0), l = P(len * 0.42, -w), r = P(len * 0.42, w), l2 = P(len * 0.88, -w * 0.55), r2 = P(len * 0.88, w * 0.55)
  return `<path${cls ? ` class="${cls}"` : ' fill="currentColor"'} d="M${x} ${y}C${l} ${l2} ${t}C${r2} ${r} ${x} ${y}Z"/>`
}

// A · the bowing ear: a stem that rises and bows under a full head of grain
function bowingEar() {
  const parts = []
  // stem rises from the ground and bows over to the right
  parts.push(`<path d="M20 61C19 45 21 28 29 18C35 11 43 9 48 13" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>`)
  // the heavy head: a rachis hanging from (48,13) down to (52,52), grains in two rows along it
  const rach = (t) => [48 + Math.sin(t * 2.2) * 5.5, 13 + t * 40]
  const n = 7
  for (let i = 0; i < n; i++) {
    const t = 0.06 + i / n * 0.86, [x, y] = rach(t)
    const len = 10.5 - i * 0.55
    parts.push(grain(f(x), f(y), Math.PI / 2 - 0.75, len, 3.1))
    parts.push(grain(f(x), f(y), Math.PI / 2 + 0.75, len, 3.1))
  }
  const [tx, ty] = rach(0.94)
  parts.push(grain(f(tx), f(ty), Math.PI / 2, 10, 3.3, 'acc'))
  // a long leaf from the base
  parts.push(`<path fill="currentColor" d="M20.2 52C11 47 5.5 38 5 26C14 32 19.8 40 20.2 52Z"/>`)
  return parts.join('')
}

// B · fertile land: a round seal, sun above, furrows running to the horizon, a sprout at the centre
function fertileLand() {
  return [
    `<circle cx="32" cy="32" r="29" fill="currentColor"/>`,
    `<path class="acc" d="M17 33a15 15 0 0 1 30 0z"/>`,
    // furrows converge on the vanishing point (32,33)
    `<path class="on" d="M32 33L6.5 45.5A29 29 0 0 0 9 50.5ZM32 33L13.5 56A29 29 0 0 0 20 59.3ZM32 33L27 61A29 29 0 0 0 37 61ZM32 33L44 59.3A29 29 0 0 0 50.5 56ZM32 33L55 50.5A29 29 0 0 0 57.5 45.5Z"/>`,
    `<rect class="on" x="3" y="32.2" width="58" height="2" />`,
    // sprout on the horizon, cut out of the sun
    `<path fill="currentColor" d="M31 33V25.5a1 1 0 0 1 2 0V33z"/>`,
    `<path fill="currentColor" d="M32 28.5C31.4 24.5 28.4 22.3 24 22.5C24.6 26.5 27.6 28.8 32 28.5Z"/>`,
    `<path fill="currentColor" d="M32 26.5C32.6 22.2 35.8 19.8 40.5 20C39.9 24.3 36.7 26.8 32 26.5Z"/>`,
  ].join('')
}

// C · alpana of grain: a sun whose rays are paddy grains, like the rice-paste alpana drawn at harvest
function alpana() {
  const parts = [`<circle class="acc" cx="32" cy="32" r="8.5"/>`]
  const n = 12
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2
    parts.push(grain(f(32 + Math.cos(a) * 12), f(32 + Math.sin(a) * 12), a, 17, 4.3))
  }
  for (let i = 0; i < n; i++) {
    const a = ((i + 0.5) / n) * Math.PI * 2 - Math.PI / 2
    const x = 32 + Math.cos(a) * 25.5, y = 32 + Math.sin(a) * 25.5
    parts.push(`<circle fill="currentColor" cx="${f(x)}" cy="${f(y)}" r="1.7"/>`)
  }
  return parts.join('')
}

const marks = { a: bowingEar(), b: fertileLand(), c: alpana() }
for (const [k, body] of Object.entries(marks)) {
  writeFileSync(`${out}/mark-${k}.svg`, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" color="#0D3B2E"><style>.acc{fill:var(--acc,#F2A231)}.on{fill:var(--on,#FAF5EA)}</style>${body}</svg>`)
}
writeFileSync(`${out}/sprite.html`, `<svg style="position:absolute;width:0;height:0" aria-hidden="true">${Object.entries(marks).map(([k, b]) => `<symbol id="m-${k}" viewBox="0 0 64 64">${b}</symbol>`).join('')}</svg>`)
console.log('wrote', Object.keys(marks).length, 'marks to', out)
