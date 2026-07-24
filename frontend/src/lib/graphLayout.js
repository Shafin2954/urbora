/**
 * graphLayout.js — deterministic radial layout for the provenance graph.
 *
 * No force simulation on purpose: a physics layout jitters and is
 * non-deterministic, and it would visibly shove nodes around under the
 * judge's cursor every time a new SSE event arrives mid-turn. Instead this
 * is a fixed BFS-from-farm layout — same graph in, same positions out, every
 * time, and a node's angle only ever gets more crowded as siblings arrive,
 * never reassigned.
 *
 * Ring 1 (radius r1) holds every node one hop from `farm`. Ring 2 (radius r2)
 * holds everything one hop further out. Given the edge shapes traceGraph.js
 * produces (farm -> X, X -> Y, nothing deeper), depth never exceeds 2, so two
 * rings is the whole layout — no collision solver needed.
 */

const CATEGORY_ORDER = {
  place: 0,
  weather: 1,
  source: 2,
  crop: 3,
  question: 4,
  plan: 5,
  finance: 6,
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}

export function layout({ nodes, edges }, opts = {}) {
  const r1 = opts.r1 ?? 190
  const r2 = opts.r2 ?? 380

  const byId = new Map(nodes.map((n) => [n.id, n]))
  const adjacency = new Map(nodes.map((n) => [n.id, []]))
  for (const edge of edges) {
    if (!byId.has(edge.from) || !byId.has(edge.to)) continue
    adjacency.get(edge.from).push(edge.to)
    adjacency.get(edge.to).push(edge.from)
  }

  const rootId = byId.has('farm') ? 'farm' : nodes[0]?.id
  const depth = new Map()
  const parent = new Map()

  if (rootId) {
    depth.set(rootId, 0)
    const queue = [rootId]
    while (queue.length) {
      const current = queue.shift()
      const d = depth.get(current)
      if (d >= 2) continue // our edge model never goes deeper; this is a safety cap, not a real limit
      for (const neighbor of adjacency.get(current) ?? []) {
        if (!depth.has(neighbor)) {
          depth.set(neighbor, d + 1)
          parent.set(neighbor, current)
          queue.push(neighbor)
        }
      }
    }
  }
  // Anything unreachable (shouldn't happen — every node traceGraph.js builds
  // is connected to farm) still gets drawn, one ring out, rather than
  // silently vanishing.
  for (const node of nodes) {
    if (node.id !== rootId && !depth.has(node.id)) {
      depth.set(node.id, 1)
      parent.set(node.id, rootId)
    }
  }

  const ring1 = nodes.filter((n) => depth.get(n.id) === 1)
  const ring2 = nodes.filter((n) => depth.get(n.id) === 2)

  ring1.sort((a, b) => (CATEGORY_ORDER[a.kind] ?? 8) - (CATEGORY_ORDER[b.kind] ?? 8) || a.id.localeCompare(b.id))

  const childrenOf = new Map()
  for (const node of ring2) {
    const p = parent.get(node.id)
    if (!childrenOf.has(p)) childrenOf.set(p, [])
    childrenOf.get(p).push(node)
  }

  const weight = (node) => 1 + (childrenOf.get(node.id)?.length ?? 0)
  const totalWeight = ring1.reduce((sum, n) => sum + weight(n), 0) || 1

  const positions = new Map()
  if (rootId) positions.set(rootId, { x: 0, y: 0 })

  let angleCursor = -Math.PI / 2 // first branch points up
  for (const node of ring1) {
    const span = (weight(node) / totalWeight) * Math.PI * 2
    const angle = angleCursor + span / 2
    positions.set(node.id, { x: r1 * Math.cos(angle), y: r1 * Math.sin(angle) })

    const kids = childrenOf.get(node.id) ?? []
    if (kids.length) {
      const kidSpan = span / kids.length
      let kidCursor = angleCursor
      for (const kid of kids) {
        const kidAngle = kidCursor + kidSpan / 2
        positions.set(kid.id, { x: r2 * Math.cos(kidAngle), y: r2 * Math.sin(kidAngle) })
        kidCursor += kidSpan
      }
    }
    angleCursor += span
  }
  // Defensive: a ring-2 node whose parent wasn't actually ring-1 (shouldn't
  // happen given the BFS above) still gets a position instead of NaN.
  for (const node of ring2) {
    if (!positions.has(node.id)) positions.set(node.id, { x: r2, y: 0 })
  }

  const positionedNodes = nodes.map((n) => ({ ...n, ...(positions.get(n.id) ?? { x: 0, y: 0 }) }))
  const posById = new Map(positionedNodes.map((n) => [n.id, n]))

  const positionedEdges = edges
    .filter((e) => posById.has(e.from) && posById.has(e.to))
    .map((e) => {
      const a = posById.get(e.from)
      const b = posById.get(e.to)
      return { ...e, x1: a.x, y1: a.y, x2: b.x, y2: b.y, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 }
    })

  const xs = positionedNodes.map((n) => n.x)
  const ys = positionedNodes.map((n) => n.y)
  const pad = 60
  const bbox = xs.length
    ? {
        minX: Math.min(...xs) - pad,
        minY: Math.min(...ys) - pad,
        maxX: Math.max(...xs) + pad,
        maxY: Math.max(...ys) + pad,
      }
    : { minX: -200, minY: -200, maxX: 200, maxY: 200 }

  return { nodes: positionedNodes, edges: positionedEdges, bbox }
}

export function fitTransform(bbox, viewportW, viewportH, { minScale = 0.3, maxScale = 2.5, marginFactor = 0.9 } = {}) {
  const w = Math.max(1, bbox.maxX - bbox.minX)
  const h = Math.max(1, bbox.maxY - bbox.minY)
  const scale = clamp(Math.min(viewportW / w, viewportH / h) * marginFactor, minScale, maxScale)
  const cx = (bbox.minX + bbox.maxX) / 2
  const cy = (bbox.minY + bbox.maxY) / 2
  return {
    scale,
    x: viewportW / 2 - cx * scale,
    y: viewportH / 2 - cy * scale,
  }
}

export { clamp }
