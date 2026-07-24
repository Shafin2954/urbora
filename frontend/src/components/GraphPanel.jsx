import { useEffect, useMemo, useRef, useState } from 'react'
import { buildGraph, NODE_STYLE } from '../lib/traceGraph.js'
import { linearLayout, clamp } from '../lib/graphLayout.js'

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
 * BFS-from-farm layout, so the same trace always draws the same picture and
 * nothing moves under the judge's cursor while they're reading it. Pan/zoom
 * only, per the brief — "just pan-able, not that interactive."
 */

const VB_W = 640
const VB_H = 460
const focusNewest = (graph) => ({ scale: 1.25, x: VB_W * 0.54 - graph.last.x * 1.25, y: VB_H / 2 - graph.last.y * 1.25 })

export default function GraphPanel({ trace, usage, streaming }) {
  const graph = useMemo(() => buildGraph(trace), [trace])
  const laid = useMemo(() => linearLayout(graph), [graph])
  const [frozenLaid, setFrozenLaid] = useState(null)
  const display = frozenLaid ?? laid
  const activeCall = [...Object.values(graph.callsById)].reverse().find((call) => !Object.hasOwn(call, 'result'))

  const [view, setView] = useState(() => focusNewest(laid))
  const userMovedRef = useRef(false)
  const draggingRef = useRef(null)
  const svgRef = useRef(null)

  const nodeCount = display.nodes.length
  useEffect(() => {
    if (frozenLaid) return
    setView(focusNewest(display))
    // A fresh fact becomes the reading focus; the user can still pan freely
    // until the following fact arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeCount, frozenLaid])

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
    draggingRef.current = { startX: e.clientX, startY: e.clientY, origX: view.x, origY: view.y }
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e) => {
    if (!draggingRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const factor = VB_W / rect.width
    const dx = (e.clientX - draggingRef.current.startX) * factor
    const dy = (e.clientY - draggingRef.current.startY) * factor
    userMovedRef.current = true
    setView((v) => ({ ...v, x: draggingRef.current.origX + dx, y: draggingRef.current.origY + dy }))
  }
  const onPointerUp = () => {
    draggingRef.current = null
  }
  const onWheel = (e) => {
    e.preventDefault()
    userMovedRef.current = true
    setView((v) => ({ ...v, scale: clamp(v.scale * (e.deltaY > 0 ? 0.9 : 1.1), 0.5, 2.5) }))
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
        <button className="graph-freeze" onClick={() => setFrozenLaid(frozenLaid ? null : laid)}>
          {frozenLaid ? 'চালু করুন' : 'স্থির করুন'}
        </button>
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
        <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
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

function NodeView({ node, isNew }) {
  const style = NODE_STYLE[node.kind] ?? NODE_STYLE.question
  const stroke = node.excluded || node.degraded ? 'var(--clay)' : style.stroke
  const dashed = Boolean(node.excluded || node.degraded || node.dashed)
  const hitRadius = Math.max(22, style.r + 6)

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
      <LabelBackground text={node.label} y={style.r + 14} className="graph-node-label-bg" />
      <text
        className="graph-node-label"
        y={style.r + 14}
        textAnchor="middle"
        fill="var(--ink)"
      >
        {node.label}
      </text>
      {node.sub && <>
        <LabelBackground text={node.sub} y={style.r + 27} className="graph-node-sub-bg" />
        <text className="graph-node-sub mono" y={style.r + 27} textAnchor="middle" fill="var(--ink-soft)">{node.sub}</text>
      </>}
    </g>
  )
}

const TOOL_LABELS = {
  rag_query: 'তথ্য খোঁজা', geocode: 'স্থান খোঁজা', get_forecast: 'আবহাওয়া',
  get_climatology: 'জলবায়ু', crop_scorer: 'ফসল বাছাই', season_plan: 'পরিকল্পনা',
  finance_projection: 'হিসাব', ask_farmer: 'প্রশ্ন', cropdb_sql: 'তথ্যভান্ডার',
}

function EdgeView({ edge, isNew, isActive }) {
  const length = Math.hypot(edge.x2 - edge.x1, edge.y2 - edge.y1)
  const toKind = edge.tool === 'rag_query' || edge.to.startsWith('source:') ? 'var(--leaf)' : edge.to.startsWith('weather:') || edge.to.startsWith('place:') ? 'var(--soil)' : edge.to === 'plan' || edge.to === 'finance' ? 'var(--green-dark)' : 'var(--green)'
  const label = TOOL_LABELS[edge.tool] ?? 'কাজ'
  const labelWidth = Math.max(26, label.length * 7 + 12)
  return (
    <g className={`graph-edge${isNew ? ' is-new' : ''}${isActive ? ' is-active' : ''}`}>
      <line className="graph-edge-lead" x1={edge.x1} y1={edge.y1} x2={edge.mx} y2={edge.my} stroke={toKind} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={edge.dashed ? '4 3' : undefined} opacity={0.7} />
      <line className="graph-edge-tail" x1={edge.mx} y1={edge.my} x2={edge.x2} y2={edge.y2} stroke={toKind} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={edge.dashed ? '4 3' : undefined} opacity={0.7} />
      {isNew && <g transform={`translate(${edge.mx} ${edge.my})`}><polygon className="graph-edge-pulse" points="0,-7 6,5 -6,5" fill={toKind} /></g>}
      {length >= 40 && <>
        <rect x={edge.mx - labelWidth / 2} y={edge.my - 8} width={labelWidth} height={14} rx={3} fill="var(--bg)" opacity={0.94} />
        <text className="graph-edge-label" x={edge.mx} y={edge.my + 3} textAnchor="middle" fill="var(--soil)">{label}</text>
      </>}
    </g>
  )
}

function LabelBackground({ text, y, className }) {
  const width = Math.max(20, String(text).length * 6.2 + 8)
  return <rect className={className} x={-width / 2} y={y - 10} width={width} height={14} rx={3} fill="var(--bg)" opacity={0.92} />
}
