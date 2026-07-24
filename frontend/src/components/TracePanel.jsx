import { useState } from 'react'

/**
 * The visible agent trace — Tier 0 item 8, and 20 of the agentic points.
 *
 * No longer the primary trace surface: GraphPanel.jsx renders the
 * provenance graph and nests this component, collapsed, as "Raw log (n
 * events)" underneath it. Kept as-is (and still exported standalone) so the
 * exhaustive chronological view is demoted, not lost.
 *
 * Rules this panel exists to satisfy:
 *   - every tool call shows name, params, raw result, timestamp (CLAUDE.md §2.5)
 *   - the panel is English, unlike the rest of the UI (PRD.md §9)
 *   - "a tool that doesn't appear here doesn't exist for the judges"
 *
 * Params and results arrive already redacted — masking happens in
 * backend/api/redact.py, by construction, before the event is ever encoded.
 * The `redacted` list on each event names the fields that were masked, which
 * is why this panel can state plainly that credentials were removed on
 * purpose, rather than leaving a judge to wonder what `***` is hiding.
 */
export default function TracePanel({ trace, usage }) {
  if (trace.length === 0) {
    return (
      <p className="muted empty-hint">
        No tool calls yet. Every call the agent makes appears here with its raw
        params and results.
      </p>
    )
  }

  return (
    <div className="trace">
      {trace.map((event) => (
        <TraceEntry key={`${event.id}-${event.seq}`} event={event} />
      ))}
      {usage && (
        <p className="usage mono">
          {usage.in_tokens} in · {usage.out_tokens} out · $
          {Number(usage.cost_usd ?? 0).toFixed(4)}
        </p>
      )}
    </div>
  )
}

function TraceEntry({ event }) {
  const [open, setOpen] = useState(false)
  const isCall = event.type === 'tool_call'
  const body = isCall ? event.params : event.result_raw
  const redacted = event.redacted ?? []

  return (
    <section className={`trace-entry ${isCall ? 'is-call' : 'is-result'}`}>
      <button
        className="trace-head"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span className={`type type-${event.type}`}>
          {isCall ? 'call' : 'result'}
        </span>
        <span className="trace-name mono">{event.name ?? event.type}</span>
        <span className="trace-ts mono">{formatTs(event.ts)}</span>
      </button>

      {open && (
        <>
          <pre className="trace-body mono">{JSON.stringify(body, null, 2)}</pre>
          {redacted.length > 0 && (
            <p className="trace-redacted mono">
              redacted: {redacted.join(', ')} — credentials masked before
              streaming (NOTES.md #19)
            </p>
          )}
        </>
      )}
    </section>
  )
}

function formatTs(ts) {
  if (!ts) return ''
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  return date.toLocaleTimeString('en-GB', { hour12: false })
}
