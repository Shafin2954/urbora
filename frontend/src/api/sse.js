/**
 * SSE client over fetch.
 *
 * Why not EventSource: EventSource can only issue GET requests, and the real
 * contract (docs/archive/hackathon/PLAN.md §2) is `POST /api/chat {session_id, farm_id, message}`
 * -> SSE. Building on EventSource would mean throwing the client away the day
 * /api/chat lands. So the transport is fetch + a streaming body reader from
 * hour zero, and the hello-world endpoint exercises exactly the path the agent
 * will use.
 *
 * The parser follows the SSE framing rules that actually matter to us:
 *   - frames are separated by a blank line
 *   - lines starting with ':' are comments (our keep-alive heartbeat)
 *   - multiple `data:` lines in one frame concatenate with '\n'
 *   - a single leading space after 'data:' is stripped
 * Every payload we send is one JSON object with a `type` field (see
 * backend/api/sse.py for the matching decision on the server side).
 */

/** Split one raw frame into its payload string, or null if it carries no data. */
function parseFrame(frame) {
  const dataLines = []
  for (const line of frame.split('\n')) {
    if (line === '' || line.startsWith(':')) continue // heartbeat / comment
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    if (field !== 'data') continue // we don't use event:/id:/retry:
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    dataLines.push(value)
  }
  return dataLines.length ? dataLines.join('\n') : null
}

/**
 * Open an SSE stream and invoke onEvent for each decoded event object.
 *
 * @param {string} url
 * @param {object}   opts
 * @param {string}   [opts.method='POST']
 * @param {object}   [opts.body]     JSON-serialised request body
 * @param {AbortSignal} [opts.signal] abort to cancel the stream
 * @param {(event: object) => void} opts.onEvent
 * @returns {Promise<void>} resolves when the server closes the stream
 */
export async function streamSSE(url, { method = 'POST', body, signal, onEvent }) {
  const response = await fetch(url, {
    method,
    headers: {
      Accept: 'text/event-stream',
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    throw new Error(`${method} ${url} -> HTTP ${response.status} ${response.statusText}`)
  }
  if (!response.body) {
    throw new Error('Response has no readable body — streaming unsupported here.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break

      // stream:true keeps multi-byte characters intact across chunk
      // boundaries — Bangla is 3 bytes per character in UTF-8 and *will*
      // straddle a chunk eventually.
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

      let split
      while ((split = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, split)
        buffer = buffer.slice(split + 2)
        const payload = parseFrame(frame)
        if (payload === null) continue
        try {
          onEvent(JSON.parse(payload))
        } catch {
          // A malformed frame must not kill a live plan mid-stream.
          onEvent({ type: 'error', message: `Unparseable SSE payload: ${payload}` })
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {})
  }
}
