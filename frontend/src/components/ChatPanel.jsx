import { useEffect, useRef, useState } from 'react'
import InputRequest from './InputRequest.jsx'

/**
 * The chat surface: transcript, the open input_request (if any), composer.
 *
 * Bangla-first per PRD.md §9 — every farmer-facing string here is Bangla. The
 * composer stays enabled while a widget is showing, because widgets are
 * accelerators and free text must always work in parallel.
 */
export default function ChatPanel({
  messages,
  inputRequest,
  streaming,
  error,
  onSend,
  onAnswerInput,
}) {
  const [draft, setDraft] = useState('')
  const endRef = useRef(null)

  // Follow the stream, so the newest tokens stay on screen without scrolling.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, inputRequest])

  const submit = () => {
    const text = draft.trim()
    if (!text || streaming) return
    setDraft('')
    onSend(text)
  }

  return (
    <div className="chat">
      <div className="transcript">
        {messages.length === 0 && (
          <p className="muted empty-hint">
            প্রশ্ন লিখুন — যেমন “আগামী রবি মৌসুমে কী চাষ করব?”
          </p>
        )}

        {messages
          // A turn that produced only an `error` leaves an assistant message
          // with no text. Rendering it gives an empty bubble that reads as a
          // broken reply, so an empty one only survives while it is the live
          // message being streamed into (where it carries the caret).
          .filter(
            (message, index) =>
              message.text || (streaming && index === messages.length - 1),
          )
          .map((message, index, visible) => (
            <article key={message.id} className={`msg msg-${message.role}`}>
              <p className="msg-text">
                {message.text}
                {/* Caret only on the message actually being written to, so
                    "thinking" is visible without a spinner that lies. */}
                {streaming &&
                  message.role === 'assistant' &&
                  index === visible.length - 1 && (
                    <span className="caret" aria-label="উত্তর আসছে" />
                  )}
              </p>
            </article>
          ))}

        {inputRequest && (
          <InputRequest
            request={inputRequest}
            onAnswer={onAnswerInput}
            disabled={streaming}
          />
        )}

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <div ref={endRef} />
      </div>

      <div className="composer">
        <input
          className="field"
          type="text"
          value={draft}
          placeholder="এখানে লিখুন…"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && submit()}
        />
        <button onClick={submit} disabled={streaming || !draft.trim()}>
          পাঠান
        </button>
      </div>
    </div>
  )
}
