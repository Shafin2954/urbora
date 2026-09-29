// Writes the website's brand files into frontend/public from the shared masters
// (frontend/src/lib/seal.js, frontend/src/lib/engraving.js). Re-run after changing either.
// Usage (repo root): node brand/scripts/build-web-assets.mjs
import { writeFileSync, mkdirSync } from 'node:fs'
import { seal, svgDoc } from '../../frontend/src/lib/seal.js'
import { engrave } from '../../frontend/src/lib/engraving.js'

const pub = 'frontend/public'
mkdirSync(`${pub}/pattern`, { recursive: true })

// Browser tab and home-screen icons. The tab icon uses the simple seal (no rays) so it reads at 16px.
writeFileSync(`${pub}/icon.svg`, svgDoc(seal({ detail: 'simple' })))
writeFileSync(`${pub}/icon-maskable.svg`,
  `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 200 200"><rect width="200" height="200" fill="#0D3B2E"/><g transform="translate(34 34) scale(.66)">${seal({ detail: 'full' })}</g></svg>`)

// Patterns. Colours are baked in because the files are used as CSS backgrounds.
const files = {
  'sweep-sepia.svg': { W: 1200, H: 800, seed: 5, n: 9, layout: 'sweep', color: '#6B4A1E' },
  'field-sepia.svg': { W: 1600, H: 380, seed: 9, n: 11, layout: 'field', color: '#6B4A1E' },
  'field-straw.svg': { W: 1600, H: 380, seed: 21, n: 11, layout: 'field', color: '#FAF5EA' },
}
for (const [name, opts] of Object.entries(files)) writeFileSync(`${pub}/pattern/${name}`, engrave(opts))
console.log('wrote icons and', Object.keys(files).length, 'patterns to', pub)
