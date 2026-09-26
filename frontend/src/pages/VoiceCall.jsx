import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../api/client.js'

/**
 * The voice line, simulated in the browser: tap to talk, tap again to send.
 * The clip goes to the same voice turn a real call uses
 * (backend/channels/voice/turn.py): speech-to-text, the agent, text-to-speech.
 * Hanging up sends the SMS summary of what the call produced.
 *
 * Half-duplex on purpose: push-to-talk needs no voice-activity detection, so
 * a demo in a noisy hall still works. The real phone line (USB modem) is
 * full-duplex.
 */
export default function VoiceCall({ msisdn, onEnd }) {
  const [callId] = useState(() => crypto.randomUUID())
  const [state, setState] = useState('idle') // idle | recording | thinking
  const [turns, setTurns] = useState([])
  const [error, setError] = useState('')
  const recorder = useRef(null)
  const chunks = useRef([])
  const player = useRef(null)

  useEffect(() => () => player.current?.pause(), [])

  const start = async () => {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      chunks.current = []
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        send(new Blob(chunks.current, { type: rec.mimeType || 'audio/webm' }))
      }
      recorder.current = rec
      rec.start()
      setState('recording')
    } catch {
      setError('মাইক্রোফোন পাওয়া যায়নি')
    }
  }

  const stop = () => recorder.current?.state === 'recording' && recorder.current.stop()

  const send = async (blob) => {
    setState('thinking')
    const form = new FormData()
    form.append('msisdn', msisdn)
    form.append('call_id', callId)
    form.append('file', blob, 'speech.webm')
    try {
      const response = await fetch(apiUrl('/api/channels/emulator/voice/turn'), { method: 'POST', body: form })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
      setTurns((prev) => [...prev, body])
      if (body.audio_b64) {
        player.current?.pause()
        player.current = new Audio(`data:${body.audio_type};base64,${body.audio_b64}`)
        player.current.play().catch(() => {})
      } else if (body.tts_error) {
        setError(`শব্দ তৈরি হয়নি: ${body.tts_error}`)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setState('idle')
    }
  }

  const hangUp = async () => {
    stop()
    player.current?.pause()
    try {
      await fetch(apiUrl('/api/channels/emulator/voice/hangup'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msisdn, call_id: callId }),
      })
    } catch {
      // The call still ends; the summary SMS is best-effort.
    }
    onEnd()
  }

  return (
    <div className="call">
      <p className="lcd-title">কল চলছে</p>
      <ol className="call-turns">
        {turns.map((t, i) => (
          <li key={i}>
            <p className="turn-q">{t.transcript || '…'}</p>
            <p className="turn-a">{t.reply_text}</p>
          </li>
        ))}
      </ol>
      {error && <p className="lcd-hint">{error}</p>}
      <div className="call-actions">
        {state === 'recording' ? (
          <button className="btn" onClick={stop}>■ পাঠান</button>
        ) : (
          <button className="btn" onClick={start} disabled={state === 'thinking'}>
            {state === 'thinking' ? 'ভাবছি…' : '🎙 বলুন'}
          </button>
        )}
        <button className="btn btn-danger" onClick={hangUp}>কল শেষ</button>
      </div>
    </div>
  )
}
