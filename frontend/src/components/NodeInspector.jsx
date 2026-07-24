/**
 * NodeInspector.jsx — the raw params/result behind one graph node.
 *
 * This is what makes the graph more than a picture: click a node and you get
 * exactly what TracePanel.jsx always showed for that call — the tool name,
 * the raw params, the raw result, both timestamps, and which fields were
 * redacted before the event ever left the server. A judge tracing a number
 * in the plan back to a real call ends here.
 *
 * An overlay, not a sidebar — LOG3.md [12:50] records that an inline
 * provenance panel once squeezed the finance table down to a few characters
 * per item name. An overlay never steals width from anything else on screen.
 */
export default function NodeInspector({ node, callsById, onClose }) {
  const call = node.sourceCallId ? callsById[node.sourceCallId] : null
  const duration =
    call?.tsCall && call?.tsResult ? Date.parse(call.tsResult) - Date.parse(call.tsCall) : null
  const redacted = [...(call?.redactedCall ?? []), ...(call?.redactedResult ?? [])]

  return (
    <div className="inspector-overlay" role="dialog" aria-label={`${node.kind} details: ${node.label}`}>
      <div className="inspector-panel">
        <div className="inspector-head">
          <div>
            <span className="inspector-kind mono">{node.kind}</span>
            <h3>{node.label}</h3>
          </div>
          <button className="secondary" onClick={onClose}>
            Close
          </button>
        </div>

        {node.sub && <p className="inspector-sub">{node.sub}</p>}

        {!call && (
          <p className="muted empty-hint">No tool call backs this node yet.</p>
        )}

        {call && (
          <>
            <p className="inspector-tool mono">
              <span className="type type-tool_call">call</span> {call.name}
              {duration != null && <span className="muted"> · {duration}ms</span>}
            </p>

            <p className="label">params</p>
            <pre className="trace-body mono">{JSON.stringify(call.params, null, 2)}</pre>

            <p className="label">result</p>
            <pre className="trace-body mono">{JSON.stringify(call.result, null, 2)}</pre>

            {redacted.length > 0 && (
              <p className="trace-redacted mono">
                redacted: {redacted.join(', ')} — credentials masked before streaming (NOTES.md #19)
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
