import { useCallback, useEffect, useRef, useState } from 'react'
import { apiUrl } from '../api/client.js'
import { streamSSE } from '../api/sse.js'

/**
 * The one place SSE event semantics live.
 *
 * Every event type in the PLAN.md §2 contract is handled here and nowhere
 * else, so components stay dumb renderers. Unknown event types are kept rather
 * than dropped — when A adds an event this hook hasn't learned yet, it must
 * show up in the trace instead of vanishing silently.
 */

const newId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
const westernDigits = (text) => String(text).replace(/[০-৯]/g, (digit) => '0123456789'['০১২৩৪৫৬৭৮৯'.indexOf(digit)])

/**
 * Which farm this browser is talking about.
 *
 * One farm per install: PRD §8 lists auth beyond farm profiles as a non-goal,
 * so there is no farm picker and no login. The default is the seeded demo farm
 * (`backend/memory/seed_demo.py`), which is what makes the agent open by
 * recalling a returning farmer instead of starting cold. Override with
 * VITE_FARM_ID to talk to a different one.
 */
export function useChat({ farmId, sessionId, accessToken, onCropName, onChatTitle } = {}) {
  const [messages, setMessages] = useState([])
  const [trace, setTrace] = useState([])
  const [inputRequest, setInputRequest] = useState(null)
  const [plan, setPlan] = useState(null)
  const [finance, setFinance] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [usage, setUsage] = useState(null)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)

  const abortRef = useRef(null)
  const sessionRef = useRef(sessionId ?? newId())
  // The assistant message currently being streamed into.
  const activeIdRef = useRef(null)

  useEffect(() => {
    sessionRef.current = sessionId ?? newId()
    setMessages([]); setTrace([]); setPlan(null); setFinance(null); setAlerts([]); setInputRequest(null); setError(null)
    if (!sessionId || !accessToken) return undefined
    const controller = new AbortController()
    fetch(apiUrl(`/api/sessions/${sessionId}`), { headers: { Authorization: `Bearer ${accessToken}` }, signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then((body) => setMessages((body.messages ?? []).flatMap((message, index) => {
        if (!['user', 'assistant'].includes(message.role) || typeof message.content !== 'string') return []
        return [{ id: `history-${index}`, role: message.role, text: message.content }]
      })))
      .catch((err) => { if (!controller.signal.aborted) setError(err.message) })
    return () => controller.abort()
  }, [sessionId, accessToken])

  const appendToken = useCallback((text) => {
    setMessages((prev) => {
      const id = activeIdRef.current
      const index = prev.findIndex((m) => m.id === id)
      if (index === -1) return prev
      const next = [...prev]
      next[index] = { ...next[index], text: next[index].text + text }
      return next
    })
  }, [])

  const handleEvent = useCallback(
    (event) => {
      switch (event.type) {
        case 'token':
          // The trace remains raw; farmer-facing assistant prose is normalized
          // so it can be compared with the Western-number tool values.
          appendToken(westernDigits(event.text))
          break

        case 'tool_call':
        case 'tool_result':
          setTrace((prev) => [...prev, { ...event, seq: prev.length }])
          break

        case 'input_request':
          // At most one open question at a time — PRD.md §8 Tier0.1 is explicit
          // that the agent asks at most one question per turn.
          setInputRequest(event)
          break

        case 'plan_update':
          setPlan(event.plan)
          if (event.plan?.crop) onCropName?.(event.plan.crop)
          break

        case 'finance_update':
          setFinance(event.finance)
          break

        case 'alert':
          setAlerts((prev) => [...prev, event.alert])
          break

        case 'done':
          setUsage(event.usage ?? null)
          setMessages((prev) => {
            const id = activeIdRef.current
            const index = prev.findIndex((message) => message.id === id)
            if (index === -1) return prev
            const match = prev[index].text.match(/^\s*\[\[CHAT_TITLE:\s*([^\]]{1,80})\]\]\s*/)
            if (!match) return prev
            onChatTitle?.(match[1].trim())
            const next = [...prev]
            next[index] = { ...next[index], text: next[index].text.slice(match[0].length) }
            return next
          })
          break

        case 'error':
          setError(event.message)
          break

        default:
          // Don't drop what we don't understand — surface it.
          setTrace((prev) => [...prev, { ...event, seq: prev.length, unknown: true }])
      }
    },
    [appendToken, onChatTitle, onCropName],
  )

  const send = useCallback(
    async (text, { endpoint = '/api/chat' } = {}) => {
      const trimmed = (text ?? '').trim()
      if (!trimmed || streaming) return

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      const assistantId = newId()
      activeIdRef.current = assistantId

      setError(null)
      setInputRequest(null)
      setUsage(null)
      setStreaming(true)
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: 'user', text: trimmed },
        { id: assistantId, role: 'assistant', text: '' },
      ])

      try {
        await streamSSE(apiUrl(endpoint), {
          method: 'POST',
          body: {
            session_id: sessionRef.current,
            farm_id: farmId,
            message: trimmed,
          },
          signal: controller.signal,
          onEvent: handleEvent,
        })
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message)
      } finally {
        if (abortRef.current === controller) abortRef.current = null
        activeIdRef.current = null
        setStreaming(false)
      }
    },
    [farmId, handleEvent, streaming],
  )

  /** Answer an input_request widget. Sent as ordinary text so the agent needs
   *  no second parsing path, and so the answer is visible in the transcript. */
  const answerInput = useCallback(
    (value, options) => {
      setInputRequest(null)
      return send(value, options)
    },
    [send],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  return {
    messages,
    trace,
    inputRequest,
    plan,
    finance,
    // The Finance tab's live area edit replaces the projection with the one
    // /api/finance/recompute returns — same engine, same shape, so the tab and
    // the agent can never show different numbers for the same farm.
    setFinance,
    setAlerts,
    alerts,
    usage,
    streaming,
    error,
    sessionId: sessionRef.current,
    farmId,
    send,
    answerInput,
    stop,
  }
}
