import { useEffect, useRef, useState } from 'react'
import InputRequest from './InputRequest.jsx'
import MarkdownLite from '../lib/markdownLite.jsx'
import { apiUrl } from '../api/client.js'
import { useDictation, useSpeech } from '../state/useVoice.js'

/**
 * A leaf-photo classification, shown with the two things that make it safe to
 * read: how confident the model is, and whether the crop it thinks it is
 * looking at is one this app can actually diagnose. A rice leaf still comes
 * back as one of PlantVillage's 38 classes, so "not your crop" has to be
 * louder than the label itself.
 */
function Diagnosis({ result, onAsk }) {
  if (!result) return null
  if (result.error) return <p className="error" role="alert">{result.message_bn ?? result.error}</p>

  const top = result.predictions?.[0]
  const pct = top ? Math.round(top.confidence * 100) : null

  return (
    <div className={`diagnosis${result.is_supported_crop ? '' : ' is-out-of-scope'}`}>
      <strong>{top?.crop_in_photo} — {top?.condition}</strong>
      <span className="mono diagnosis-conf">{pct}%</span>
      {!result.is_supported_crop && <p className="notice">{result.out_of_scope_note_bn}</p>}
      <p className="setting-note">{result.field_photo_caveat_bn}</p>
      <p className="mono detail">{result.top_label}</p>
      {result.is_supported_crop && onAsk && (
        <button type="button" className="secondary" onClick={() => onAsk(top)}>
          {result.next_step_bn}
        </button>
      )}
    </div>
  )
}

/**
 * The chat surface: transcript, the open input_request (if any), composer.
 *
 * Bangla-first per PRD.md §9, now switchable to English from settings — the
 * chrome via `t`, the advice itself because the agent is told the language. The
 * composer stays enabled while a widget is showing, because widgets are
 * accelerators and free text must always work in parallel.
 *
 * The composer carries a microphone and each reply carries a speaker, so a
 * farmer who reads slowly can talk to this and be talked back to. Both are
 * browser-native and both hide themselves where unsupported (see useVoice.js).
 */
export default function ChatPanel({
  messages,
  inputRequest,
  streaming,
  error,
  onSend,
  onAnswerInput,
  onNewChat,
  t,
  settings,
}) {
  const [draft, setDraft] = useState('')
  const endRef = useRef(null)
  const fileRef = useRef(null)
  const [diagnosis, setDiagnosis] = useState(null)
  const [diagnosing, setDiagnosing] = useState(false)

  // Whether this deployment can actually classify a photo. Asked once, so the
  // camera button is absent rather than dead where torch was never installed —
  // same rule the microphone follows.
  const [canDiagnose, setCanDiagnose] = useState(false)
  useEffect(() => {
    let live = true
    fetch(apiUrl('/api/diagnose/status'))
      .then((response) => (response.ok ? response.json() : { available: false }))
      .then((body) => live && setCanDiagnose(Boolean(body.available)))
      .catch(() => {})
    return () => { live = false }
  }, [])

  const uploadPhoto = async (file) => {
    if (!file) return
    setDiagnosing(true)
    setDiagnosis(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const response = await fetch(apiUrl('/api/diagnose/image'), { method: 'POST', body: form })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
      setDiagnosis(body)
    } catch (failure) {
      setDiagnosis({ error: 'failed', message_bn: String(failure.message) })
    } finally {
      setDiagnosing(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  // Append, don't replace: the farmer may have typed part of the question
  // before reaching for the microphone, and the old version wiped it.
  const dictation = useDictation({
    language: settings.language,
    onText: (text) => setDraft((draft) => (draft ? `${draft} ${text}` : text)),
  })
  const speech = useSpeech({
    lang: settings.speechLang,
    voiceURI: settings.voiceURI,
    rate: settings.voiceRate,
  })

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
      {onNewChat && <div className="chat-head"><button className="secondary" onClick={onNewChat}>{t('sidebar.newChat')}</button></div>}
      <div className="transcript">
        {messages.length === 0 && (
          <p className="muted empty-hint">
            {settings.language === 'en'
              ? 'Ask a question — for example "What should I grow this rabi season?"'
              : 'প্রশ্ন লিখুন — যেমন “আগামী রবি মৌসুমে কী চাষ করব?”'}
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
              <div className="msg-text">
                <MarkdownLite text={message.text} />
                {/* Caret only on the message actually being written to, so
                    "thinking" is visible without a spinner that lies. */}
                {streaming &&
                  message.role === 'assistant' &&
                  index === visible.length - 1 && (
                    <span className="caret" aria-label="উত্তর আসছে" />
                  )}
              </div>
              {/* Read-aloud, on finished assistant replies only: speaking a
                  half-streamed sentence just gets cut off mid-word. */}
              {speech.supported && message.role === 'assistant' && message.text &&
                !(streaming && index === visible.length - 1) && (
                <button
                  type="button"
                  className="msg-speak"
                  onClick={() => speech.toggle(message.text, message.id)}
                  aria-label={speech.speakingId === message.id ? t('chat.speakStop') : t('chat.speak')}
                  title={speech.speakingId === message.id ? t('chat.speakStop') : t('chat.speak')}
                >
                  {speech.speakingId === message.id ? '◼' : '🔊'}
                </button>
              )}
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
          // The farmer gets a plain Bangla apology; the raw error (English,
          // developer-facing) stays one tap away for whoever is debugging.
          <div className="error" role="alert">
            <p>{t('chat.failed')}</p>
            <details className="error-detail">
              <summary>{t('chat.failedDetail')}</summary>
              <code>{error}</code>
            </details>
          </div>
        )}

        <div ref={endRef} />
      </div>

      <div className="composer">
        {(diagnosing || diagnosis) && (
          <div className="composer-attachment">
            {diagnosing
              ? <p className="setting-note">ছবি পরীক্ষা করা হচ্ছে…</p>
              : <Diagnosis
                  result={diagnosis}
                  onAsk={(top) => { setDiagnosis(null); onSend(`আমার ${top.crop_in_photo} গাছে ${top.condition} ধরা পড়েছে। এর প্রতিকার কী?`) }}
                />}
          </div>
        )}
        <div className={`composer-bar${dictation.listening ? ' is-listening' : ''}`}>
          {canDiagnose && (
            <>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                capture="environment"
                hidden
                onChange={(event) => uploadPhoto(event.target.files?.[0])}
              />
              <button
                type="button"
                className="composer-attach"
                onClick={() => fileRef.current?.click()}
                disabled={diagnosing}
                aria-label="পাতার ছবি দিন"
                title="পাতার ছবি দিন"
              >
                +
              </button>
            </>
          )}
          <input
            className="composer-input"
            type="text"
            value={draft}
            placeholder={
              dictation.listening ? t('chat.listening')
                : dictation.transcribing ? t('chat.transcribing')
                : t('chat.placeholder')
            }
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && submit()}
          />
          {/* Absent, not disabled, where the browser has no recogniser — see
              useVoice.js on why a dead mic is worse than no mic. */}
          {dictation.supported && (
            <button
              type="button"
              className={`composer-mic${dictation.listening ? ' is-on' : ''}${dictation.transcribing ? ' is-working' : ''}`}
              onClick={dictation.toggle}
              disabled={dictation.transcribing}
              aria-label={dictation.listening ? t('chat.micStop') : t('chat.mic')}
              title={dictation.listening ? t('chat.micStop') : t('chat.mic')}
            >
              {dictation.transcribing ? '…' : dictation.listening ? '◼' : '🎙'}
            </button>
          )}
          <button
            className="composer-send"
            onClick={submit}
            disabled={streaming || !draft.trim()}
            aria-label={t('chat.send')}
            title={t('chat.send')}
          >
            ➤
          </button>
        </div>
        {dictation.error && <p className="error" role="alert">{dictation.error}</p>}
      </div>
    </div>
  )
}
