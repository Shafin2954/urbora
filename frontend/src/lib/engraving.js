// Engraved grain line art (SVG string) from a fixed seed: the brand pattern (brand/BRAND-CORE.md §5).
// Style follows the team's references (2026-09-30): long sweeping stems, bold ears built from
// overlapping outlined grains, inner hatching, fine sketch dashes, hatched leaf blades.
// Drawn as rice paddy: plump grains, ears that bow at the tip, no long wheat awns.
// Pure function, no DOM: used by brand/scripts (Node) and the website build alike.

export function engrave({ W = 1200, H = 700, seed = 7, n = 9, layout = 'sweep', color = 'currentColor', weight = 1 } = {}) {
  let s = seed
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647)
  const r = (a, b) => a + rnd() * (b - a)
  const f = (v) => v.toFixed(1)
  const out = []
  const sw = (w) => (w * weight).toFixed(2)
  const line = (pts, w) => out.push(`<path stroke-width="${sw(w)}" d="${pts.map((p, i) => (i ? 'L' : 'M') + f(p[0]) + ' ' + f(p[1])).join('')}"/>`)

  // smooth curve through points (Catmull-Rom to cubic)
  const smooth = (pts, w) => {
    let d = `M${f(pts[0][0])} ${f(pts[0][1])}`
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6]
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6]
      d += `C${f(c1[0])} ${f(c1[1])} ${f(c2[0])} ${f(c2[1])} ${f(p2[0])} ${f(p2[1])}`
    }
    out.push(`<path stroke-width="${sw(w)}" d="${d}"/>`)
  }

  // a path that follows a gentle arc: start, heading, length, total turn
  const walk = (x, y, a, len, bend, N = 24) => {
    const pts = [[x, y]]
    for (let i = 1; i <= N; i++) { a += bend / N; const p = pts[i - 1]; pts.push([p[0] + Math.cos(a) * len / N, p[1] + Math.sin(a) * len / N]) }
    return pts
  }
  const dirAt = (pts, i) => { const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)]; return Math.atan2(b[1] - a[1], b[0] - a[0]) }

  // one grain: an outlined almond with two hatch lines along its length
  function grain(x, y, a, len, wid) {
    const c = Math.cos(a), sn = Math.sin(a)
    const P = (u, v) => [x + u * c - v * sn, y + u * sn + v * c]
    const b = P(0, 0), t = P(len, 0)
    const l1 = P(len * 0.3, -wid), l2 = P(len * 0.8, -wid * 0.75), r1 = P(len * 0.3, wid), r2 = P(len * 0.8, wid * 0.75)
    out.push(`<path stroke-width="${sw(1.25)}" d="M${f(b[0])} ${f(b[1])}C${f(l1[0])} ${f(l1[1])} ${f(l2[0])} ${f(l2[1])} ${f(t[0])} ${f(t[1])}C${f(r2[0])} ${f(r2[1])} ${f(r1[0])} ${f(r1[1])} ${f(b[0])} ${f(b[1])}Z"/>`)
    for (const k of [-0.38, 0.12]) line([P(len * 0.22, wid * k), P(len * 0.8, wid * k * 0.6)], 0.7)
    if (rnd() < 0.25) line([P(len * 1.02, 0), P(len * 1.3, r(-1.5, 1.5))], 0.6)
  }

  // an ear: grains in alternating pairs along the top of the stem, shrinking toward the bowed tip
  function ear(pts, from) {
    const N = pts.length - 1, count = N - from
    for (let i = from, k = 0; i <= N; i += 2, k += 2) {
      const t = k / count, [x, y] = pts[i], a = dirAt(pts, i)
      const len = (1 - t * 0.4) * r(24, 28), wid = len * 0.34
      grain(x, y, a - r(0.5, 0.68), len, wid)
      grain(x, y, a + r(0.5, 0.68), len, wid)
      if (k % 4 === 2) { // the engraver's sketch dashes beside the ear
        const side = rnd() < 0.5 ? -1 : 1, o = len * 1.2
        const p1 = [x + Math.cos(a + side * 1.2) * o, y + Math.sin(a + side * 1.2) * o]
        line([p1, [p1[0] + Math.cos(a) * r(5, 10), p1[1] + Math.sin(a) * r(5, 10)]], 0.6)
      }
    }
    grain(pts[N][0], pts[N][1], dirAt(pts, N), 20, 6)
  }

  // a leaf blade: two edges, a midrib and hatching on one side
  function blade(x, y, a, len, bend) {
    const mid = walk(x, y, a, len, bend, 18)
    const L = [], R = []
    mid.forEach((p, i) => {
      const t = i / 18, w = Math.sin(Math.PI * Math.min(1, t * 1.1 + 0.08)) * len * 0.045 * (1 - t * 0.55)
      const d = dirAt(mid, i)
      L.push([p[0] + Math.cos(d - Math.PI / 2) * w, p[1] + Math.sin(d - Math.PI / 2) * w])
      R.push([p[0] + Math.cos(d + Math.PI / 2) * w, p[1] + Math.sin(d + Math.PI / 2) * w])
    })
    smooth(L, 1.1); smooth(R, 1.1); smooth(mid.slice(1, -2), 0.6)
    for (let i = 2; i < 16; i += 2) line([mid[i], L[i + 1]], 0.55)
  }

  function stalk(x, y, a, len, bend) {
    // stem at ~6px steps; the last earLen pixels bow a little more, like ripening paddy
    const earLen = r(140, 190), N = Math.max(4, Math.ceil(len / 6)), K = Math.min(Math.ceil(earLen / 6), N - 2)
    const pts = [[x, y]]
    let ang = a
    const droop = (Math.cos(a) >= 0 ? 1 : -1) * r(0.25, 0.45)
    for (let i = 1; i <= N; i++) {
      ang += bend / N + (i > N - K ? droop / K : 0)
      const p = pts[i - 1]; pts.push([p[0] + Math.cos(ang) * 6, p[1] + Math.sin(ang) * 6])
    }
    smooth(pts.filter((_, i) => i % 3 === 0 || i === N), 1.5)
    // a faint second line beside the stem: the engraved double stroke
    const stemEnd = N - K
    smooth(pts.slice(0, stemEnd).filter((_, i) => i % 3 === 0).map((p) => { const i = pts.indexOf(p); return [p[0] + 2.2 * Math.cos(dirAt(pts, i) + Math.PI / 2), p[1] + 2.2 * Math.sin(dirAt(pts, i) + Math.PI / 2)] }), 0.6)
    ear(pts, stemEnd)
    const nb = rnd() < 0.6 ? 1 : 2
    for (let i = 0; i < nb; i++) {
      const at = Math.floor(r(0.1, 0.35) * stemEnd), p = pts[at], d = dirAt(pts, at), side = i % 2 ? 1 : -1
      blade(p[0], p[1], d + side * r(0.25, 0.5), Math.min(len * r(0.4, 0.6), 420), side * r(0.4, 0.9))
    }
  }

  if (layout === 'field') {
    for (let i = 0; i < n; i++) {
      const x = (i + r(0.1, 0.9)) / n * W
      stalk(x, H + 10, -Math.PI / 2 + r(-0.2, 0.35), H * r(0.6, 0.95), r(0.2, 0.7))
    }
  } else {
    for (let i = 0; i < n; i++) {
      const t = i / Math.max(1, n - 1)
      const a = -Math.PI / 2 + 0.12 + t * 1.2 + r(-0.08, 0.08)
      stalk(r(-0.05, 0.12) * W, H + r(0, 0.06) * H, a, Math.hypot(W, H) * r(0.42, 0.7), r(0.2, 0.45))
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" fill="none" stroke="${color}" stroke-linecap="round" stroke-linejoin="round">${out.join('')}</svg>`
}
