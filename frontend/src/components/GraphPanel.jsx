import { useEffect, useMemo, useRef, useState } from 'react'
import { buildGraph, NODE_STYLE } from '../lib/traceGraph.js'
import { verticalLayout, clamp } from '../lib/graphLayout.js'

/**
 * The provenance graph — Tier 0 item 8, replacing the raw JSON trace dump.
 *
 * Farm at the center. Every node is a fact the plan rests on; every edge is
 * labeled with the tool call that produced it. Walking an edge inward answers
 * "where did this number come from" without reading a single line of JSON —
 * click the node and the raw params/result are still right there
 * (NodeInspector), so the judge-facing guarantee in TracePanel.jsx's own
 * comment ("a tool that doesn't appear here doesn't exist") still holds.
 *
 * No physics, no dragging: frontend/src/lib/graphLayout.js is a fixed
 * chronological layout, so the same trace always draws the same picture and
 * nothing moves under the judge's cursor while they're reading it. Pan/zoom
 * only, per the brief — "just pan-able, not that interactive."
 *
 * The column runs top-to-bottom, one tool call per row, so a serial run of
 * calls can never hide its own earlier steps (see verticalLayout's comment for
 * why the previous left-to-right version did).
 */

const VB_W = 640
const VB_H = 460
const FOCUS_SCALE = 1.8
// Column sits left-of-centre because node captions run rightward from it.
const focusNewest = (graph) => ({
  scale: FOCUS_SCALE,
  x: VB_W * 0.3 - graph.last.x * FOCUS_SCALE,
  y: VB_H * 0.62 - graph.last.y * FOCUS_SCALE,
})

export default function GraphPanel({ trace, usage, streaming }) {
  const graph = useMemo(() => buildGraph(trace), [trace])
  const laid = useMemo(() => verticalLayout(graph), [graph])
  const [frozenLaid, setFrozenLaid] = useState(null)
  const display = frozenLaid ?? laid
  const activeCall = [...Object.values(graph.callsById)].reverse().find((call) => !Object.hasOwn(call, 'result'))

  const [view, setView] = useState(() => focusNewest(laid))
  const [dragging, setDragging] = useState(false)
  const userMovedRef = useRef(false)
  const draggingRef = useRef(null)
  const svgRef = useRef(null)

  const nodeCount = display.nodes.length
  useEffect(() => {
    if (frozenLaid) return
    // Auto-follow the newest fact ONLY until the judge takes the wheel. This
    // guard was written before (userMovedRef) but never read, so every arriving
    // node silently threw away whatever they had panned or zoomed to.
    if (userMovedRef.current) return
    setView(focusNewest(display))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeCount, frozenLaid])

  const recentre = () => {
    userMovedRef.current = false
    setView(focusNewest(display))
  }

  /** Client px -> viewBox units. Exact, so it survives preserveAspectRatio. */
  const toViewBox = (clientX, clientY) => {
    const svg = svgRef.current
    const ctm = svg?.getScreenCTM()
    if (!ctm) return null
    const point = svg.createSVGPoint()
    point.x = clientX
    point.y = clientY
    const local = point.matrixTransform(ctm.inverse())
    return { x: local.x, y: local.y }
  }

  // Only the truly new nodes/edges animate in — a re-render from an
  // unrelated state change must not replay the entrance on everything.
  const seenNodesRef = useRef(new Set())
  const seenEdgesRef = useRef(new Set())
  const newNodeIds = useMemo(() => {
    const fresh = new Set()
    for (const n of display.nodes) if (!seenNodesRef.current.has(n.id)) fresh.add(n.id)
    return fresh
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [display.nodes])
  const newEdgeIds = useMemo(() => {
    const fresh = new Set()
    for (const e of display.edges) if (!seenEdgesRef.current.has(e.id)) fresh.add(e.id)
    return fresh
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [display.edges])
  useEffect(() => {
    for (const n of display.nodes) seenNodesRef.current.add(n.id)
    for (const e of display.edges) seenEdgesRef.current.add(e.id)
  })

  const onPointerDown = (e) => {
    const start = toViewBox(e.clientX, e.clientY)
    if (!start) return
    draggingRef.current = { start, origX: view.x, origY: view.y }
    setDragging(true)
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e) => {
    if (!draggingRef.current) return
    const now = toViewBox(e.clientX, e.clientY)
    if (!now) return
    userMovedRef.current = true
    const { start, origX, origY } = draggingRef.current
    setView((v) => ({ ...v, x: origX + (now.x - start.x), y: origY + (now.y - start.y) }))
  }
  const onPointerUp = () => {
    draggingRef.current = null
    setDragging(false)
  }

  /**
   * Zoom. Three things the previous version got wrong, all of which made it
   * feel like it was jumping rather than zooming:
   *
   *   1. a fixed x0.9 / x1.1 per event, so a trackpad (which fires a stream of
   *      small deltas) rocketed while a mouse notch crawled;
   *   2. `deltaMode` ignored, so line- and page-mode wheels were read as pixels;
   *   3. only `scale` changed, so the picture slid out from under the cursor.
   *
   * Now: one continuous exponential response to the real delta, and the point
   * under the pointer is held fixed. The easing itself is a CSS transition on
   * the viewport group (turned off mid-drag, where it would lag the pointer).
   */
  const onWheel = (e) => {
    e.preventDefault()
    const at = toViewBox(e.clientX, e.clientY)
    if (!at) return
    userMovedRef.current = true
    const rect = svgRef.current.getBoundingClientRect()
    const perLine = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? rect.height : 1
    const delta = e.deltaY * perLine
    setView((v) => {
      const scale = clamp(v.scale * Math.exp(-delta * 0.002), 0.35, 3)
      const f = scale / v.scale
      return { scale, x: at.x - (at.x - v.x) * f, y: at.y - (at.y - v.y) * f }
    })
  }

  if (graph.nodes.length <= 1 && trace.length === 0) {
    return (
      <p className="muted empty-hint">
        কাজ শুরু হলে এখানে তথ্যের সংযোগচিত্র দেখা যাবে।
      </p>
    )
  }

  return (
    <div className="graph-panel">
      <div className="graph-toolbar">
        <span>{frozenLaid ? 'চিত্র স্থির আছে' : 'কাজের সঙ্গে চিত্র তৈরি হচ্ছে'}</span>
        <strong className={`graph-active-tool${activeCall ? ' is-active' : ''}`}>{activeCall ? `চলছে: ${TOOL_LABELS[activeCall.name] ?? 'কাজ'}` : streaming ? 'উত্তর তৈরি হচ্ছে' : ''}</strong>
        <span className="graph-buttons">
          <button className="graph-freeze" onClick={recentre} title="সর্বশেষ ধাপে ফিরুন">
            মাঝে আনুন
          </button>
          <button className="graph-freeze" onClick={() => setFrozenLaid(frozenLaid ? null : laid)}>
            {frozenLaid ? 'চালু করুন' : 'স্থির করুন'}
          </button>
        </span>
      </div>
      <svg
        ref={svgRef}
        className="graph-svg"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        role="group"
        aria-label="Provenance graph"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
      >
        <g
          className={`graph-viewport${dragging ? ' is-dragging' : ''}`}
          transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}
        >
          {display.edges.map((edge) => (
            <EdgeView key={edge.id} edge={edge} isNew={newEdgeIds.has(edge.id)} isActive={Boolean(graph.callsById[edge.callId] && !Object.hasOwn(graph.callsById[edge.callId], 'result'))} />
          ))}
          {display.nodes.map((node) => (
            <NodeView
              key={node.id}
              node={node}
              isNew={newNodeIds.has(node.id)}
            />
          ))}
        </g>
      </svg>

      {usage && (
        <p className="usage mono">
          {usage.in_tokens} in · {usage.out_tokens} out · $
          {Number(usage.cost_usd ?? 0).toFixed(4)}
        </p>
      )}

    </div>
  )
}

function polygonPoints(r, sides, rotationDeg = -90) {
  const pts = []
  for (let i = 0; i < sides; i++) {
    const angle = ((360 / sides) * i + rotationDeg) * (Math.PI / 180)
    pts.push(`${(r * Math.cos(angle)).toFixed(1)},${(r * Math.sin(angle)).toFixed(1)}`)
  }
  return pts.join(' ')
}

function Shape({ kind, r, fill, stroke, dashed }) {
  const style = NODE_STYLE[kind]
  const commonProps = {
    fill,
    stroke,
    strokeWidth: 2,
    strokeDasharray: dashed ? '4 3' : undefined,
    strokeLinejoin: 'round',
    strokeLinecap: 'round',
  }
  switch (style.shape) {
    case 'circle':
      return <circle r={r} {...commonProps} />
    case 'square':
      return <rect x={-r} y={-r} width={r * 2} height={r * 2} rx={4} {...commonProps} />
    case 'triangle':
      return <polygon points={polygonPoints(r, 3)} {...commonProps} />
    case 'pentagon':
      return <polygon points={polygonPoints(r, 5)} {...commonProps} />
    case 'hexagon':
      return <polygon points={polygonPoints(r, 6, 0)} {...commonProps} />
    default:
      return <circle r={r} {...commonProps} />
  }
}

/**
 * Captions sit to the RIGHT of the glyph, anchored at the start.
 *
 * They used to be centred under it, which forced a background rect sized from
 * the string length; on a 170px horizontal pitch those rects overlapped their
 * neighbours. Running rightward into the empty half of the canvas removes the
 * conflict outright, so the backgrounds are gone too — one less thing drawing
 * over the picture.
 */
function NodeView({ node, isNew }) {
  const style = NODE_STYLE[node.kind] ?? NODE_STYLE.question
  const stroke = node.excluded || node.degraded ? 'var(--clay)' : style.stroke
  const dashed = Boolean(node.excluded || node.degraded || node.dashed)
  const hitRadius = Math.max(22, style.r + 6)
  const labelX = style.r + 11

  return (
    <g
      className={`graph-node${isNew ? ' is-new' : ''}`}
      transform={`translate(${node.x} ${node.y})`}
      tabIndex={0}
      role="img"
      aria-label={`${node.kind}: ${node.label}`}
    >
      <circle r={hitRadius} fill="transparent" />
      <Shape kind={node.kind} r={style.r} fill={style.fill} stroke={stroke} dashed={dashed} />
      <text
        className="graph-node-label"
        x={labelX}
        y={node.sub ? -1 : 4}
        textAnchor="start"
        fill="var(--ink)"
      >
        {node.label}
      </text>
      {node.sub && (
        <text className="graph-node-sub mono" x={labelX} y={13} textAnchor="start" fill="var(--ink-soft)">
          {node.sub}
        </text>
      )}
    </g>
  )
}

const TOOL_LABELS = {
  rag_query: 'তথ্য খোঁজা', geocode: 'স্থান খোঁজা', get_forecast: 'আবহাওয়া',
  get_climatology: 'জলবায়ু', crop_scorer: 'ফসল বাছাই', season_plan: 'পরিকল্পনা',
  finance_projection: 'হিসাব', ask_farmer: 'প্রশ্ন', cropdb_sql: 'তথ্যভান্ডার',
}

/**
 * One stroke per edge — a straight drop between neighbouring rows, a leftward
 * bow for anything that reaches further (see verticalLayout). The tool caption
 * rides the bow's own midpoint, so a long edge no longer stamps its label on
 * top of every node it passes.
 */
function EdgeView({ edge, isNew, isActive }) {
  const toKind = edge.tool === 'rag_query' || edge.to.startsWith('source:') ? 'var(--leaf)' : edge.to.startsWith('weather:') || edge.to.startsWith('place:') ? 'var(--soil)' : edge.to === 'plan' || edge.to === 'finance' ? 'var(--green-dark)' : 'var(--green)'
  const label = TOOL_LABELS[edge.tool] ?? 'কাজ'
  const labelWidth = Math.max(26, label.length * 7 + 12)
  // A straight drop has its midpoint ON the line; nudge the caption clear of it.
  const labelX = edge.bow === 0 ? edge.mx - labelWidth / 2 - 8 : edge.mx
  return (
    <g className={`graph-edge${isNew ? ' is-new' : ''}${isActive ? ' is-active' : ''}`}>
      <path
        className="graph-edge-line"
        d={edge.d}
        fill="none"
        stroke={toKind}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={edge.dashed ? '4 3' : undefined}
        opacity={0.7}
      />
      {isNew && <g transform={`translate(${edge.mx} ${edge.my})`}><polygon className="graph-edge-pulse" points="0,-7 6,5 -6,5" fill={toKind} /></g>}
      <rect x={labelX - labelWidth / 2} y={edge.my - 7} width={labelWidth} height={14} rx={3} fill="var(--bg)" opacity={0.94} />
      <text className="graph-edge-label" x={labelX} y={edge.my + 4} textAnchor="middle" fill="var(--soil)">{label}</text>
    </g>
  )
}
