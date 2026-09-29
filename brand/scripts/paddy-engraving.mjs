// CLI for the brand pattern. The drawing itself lives in frontend/src/lib/engraving.js (one source
// for the website, the brand files and Figma).
// Usage: node brand/scripts/paddy-engraving.mjs <out.svg> [width] [height] [seed] [stalks] [layout] [colour]
// layout "sweep": stalks fan out from the bottom-left corner. layout "field": stalks rise along the bottom.
import { writeFileSync } from 'node:fs'
import { engrave } from '../../frontend/src/lib/engraving.js'

const [, , file, W, H, seed, n, layout, color] = process.argv
if (file) {
  const svg = engrave({ W: +(W || 1200), H: +(H || 700), seed: +(seed || 7), n: +(n || 9), layout: layout || 'sweep', color: color || 'currentColor' })
  writeFileSync(file, svg)
  console.log(file, (svg.length / 1024).toFixed(0) + ' KB')
}
