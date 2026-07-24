import { useEffect, useMemo, useRef, useState } from 'react'
import { buildGraph, NODE_STYLE, LEGEND } from '../lib/traceGraph.js'
import { layout, fitTransform, clamp } from '../lib/graphLayout.js'
import NodeInspector from './NodeInspector.jsx'
import TracePanel from './TracePanel.jsx'

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

export default function GraphPanel({ trace, usage }) {
  const graph = useMemo(() => buildGraph(trace), [trace])
  const laid = useMemo(() => layout(graph), [graph])

  const [view, setView] = useState(() => fitTransform(laid.bbox, VB_W, VB_H))
  const [selectedId, setSelectedId] = useState(null)
  const userMovedRef = useRef(false)
  const draggingRef = useRef(null)
  const svgRef = useRef(null)

  const nodeCount = laid.nodes.length
  useEffect(() => {
    if (userMovedRef.current) return
    setView(fitTransform(laid.bbox, VB_W, VB_H))
    // Re-fit whenever the graph gains or loses nodes, but stop chasing the
    // judge's own pan/zoom the moment they touch it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeCount])

  // Only the truly new nodes/edges animate in — a re-render from an
  // unrelated state change must not replay the entrance on everything.
  const seenNodesRef = useRef(new Set())
  const seenEdgesRef = useRef(new Set())
  const newNodeIds = useMemo(() => {
    const fresh = new Set()
    for (const n of laid.nodes) if (!seenNodesRef.current.has(n.id)) fresh.add(n.id)
    return fresh
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [laid.nodes])
  const newEdgeIds = useMemo(() => {
    const fresh = new Set()
    for (const e of laid.edges) if (!seenEdgesRef.current.has(e.id)) fresh.add(e.id)
    return fresh
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [laid.edges])
  useEffect(() => {
    for (const n of laid.nodes) seenNodesRef.current.add(n.id)
    for (const e of laid.edges) seenEdgesRef.current.add(e.id)
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

  const selectedNode = selectedId ? laid.nodes.find((n) => n.id === selectedId) : null

  if (graph.nodes.length <= 1 && trace.length === 0) {
    return (
      <p className="muted empty-hint">
        No tool calls yet. As the agent works, a graph grows outward from the
        farm — every node a fact, every edge the tool that produced it.
      </p>
    )
  }

  return (
    <div className="graph-panel">
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
          {laid.edges.map((edge) => (
            <EdgeView key={edge.id} edge={edge} isNew={newEdgeIds.has(edge.id)} />
          ))}
          {laid.nodes.map((node) => (
            <NodeView
              key={node.id}
              node={node}
              isNew={newNodeIds.has(node.id)}
              isSelected={node.id === selectedId}
              onSelect={() => setSelectedId(node.id)}
            />
          ))}
        </g>
      </svg>

      <ul className="graph-legend" aria-label="Legend">
        {LEGEND.map(({ kind, label }) => (
          <li key={kind} className="graph-legend-item">
            <MiniShape kind={kind} />
            <span>{label}</span>
          </li>
        ))}
      </ul>

      {usage && (
        <p className="usage mono">
          {usage.in_tokens} in · {usage.out_tokens} out · $
          {Number(usage.cost_usd ?? 0).toFixed(4)}
        </p>
      )}

      <details className="graph-raw-log">
        <summary>Raw log ({trace.length} events)</summary>
        <TracePanel trace={trace} usage={null} />
      </details>

      {selectedNode && (
        <NodeInspector node={selectedNode} callsById={graph.callsById} onClose={() => setSelectedId(null)} />
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

function MiniShape({ kind }) {
  const style = NODE_STYLE[kind]
  const r = 9
  return (
    <svg width="20" height="20" viewBox="-10 -10 20 20" aria-hidden="true">
      <Shape kind={kind} r={r} fill={style.fill} stroke={style.stroke} />
    </svg>
  )
}

function NodeView({ node, isNew, isSelected, onSelect }) {
  const style = NODE_STYLE[node.kind] ?? NODE_STYLE.question
  const stroke = node.excluded || node.degraded ? 'var(--clay)' : style.stroke
  const dashed = Boolean(node.excluded || node.degraded || node.dashed)
  const hitRadius = Math.max(22, style.r + 6)

  return (
    <g
      className={`graph-node${isNew ? ' is-new' : ''}${isSelected ? ' is-selected' : ''}`}
      transform={`translate(${node.x} ${node.y})`}
      tabIndex={0}
      role="button"
      aria-label={`${node.kind}: ${node.label}`}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect()
        }
      }}
    >
      <circle r={hitRadius} fill="transparent" />
      <Shape kind={node.kind} r={style.r} fill={style.fill} stroke={stroke} dashed={dashed} />
      <text
        className="graph-node-label"
        y={style.r + 14}
        textAnchor="middle"
        fill="var(--ink)"
      >
        {node.label}
      </text>
      {node.sub && (
        <text className="graph-node-sub mono" y={style.r + 27} textAnchor="middle" fill="var(--ink-soft)">
          {node.sub}
        </text>
      )}
    </g>
  )
}

function EdgeView({ edge, isNew }) {
  return (
    <g className={`graph-edge${isNew ? ' is-new' : ''}`}>
      <line x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2} stroke="var(--border)" strokeWidth={1.5} />
      <rect x={edge.mx - 34} y={edge.my - 8} width={68} height={14} fill="var(--bg)" opacity={0.9} />
      <text className="graph-edge-label mono" x={edge.mx} y={edge.my + 3} textAnchor="middle" fill="var(--soil)">
        {edge.tool}
      </text>
    </g>
  )
}
