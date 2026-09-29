// Writes the standard logo files from the seal master in frontend/src/lib/seal.js.
// Usage: node brand/scripts/seal.mjs <outdir>
import { writeFileSync, mkdirSync } from 'node:fs'
import { seal, svgDoc } from '../../frontend/src/lib/seal.js'

const outDir = process.argv[2]
if (outDir) {
  mkdirSync(outDir, { recursive: true })
  const files = {
    'mark.svg': seal({ detail: 'full' }),
    'mark-simple.svg': seal({ detail: 'simple' }),
    'mark-on-dark.svg': seal({ detail: 'full', ink: '#0D3B2E', ground: '#FAF5EA' }), // the seal keeps its own ground
    'mark-mono.svg': seal({ detail: 'simple', sun: '#0D3B2E', sprout: '#FAF5EA' }),
    'mark-white.svg': seal({ detail: 'simple', ink: '#FAF5EA', sun: '#FAF5EA', ground: '#0D3B2E', sprout: '#0D3B2E' }),
    'favicon.svg': seal({ detail: 'simple', ring: false }),
  }
  for (const [name, inner] of Object.entries(files)) writeFileSync(`${outDir}/${name}`, svgDoc(inner))
  console.log('wrote', Object.keys(files).length, 'files to', outDir)
}
