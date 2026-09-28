import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../api/client.js'
import { voiceKeys } from '../api/channels.js'

/**
 * The voice line, simulated in the browser: tap to talk, tap again to send.
 * The clip goes to the same voice turn a real call uses
 * (backend/channels/voice/turn.py): speech-to-text, the agent, text-to-speech.
 * Hanging up sends the SMS summary of what the call produced.
 *
 * The phone's keypad works during the call as on a real line: keys drive the
 * USSD menu, read aloud (backend/channels/voice/ivr.py). Numbers end with #
 * or a pause, exactly as the Phone Link bridge buffers them.
 *
 * Half-duplex on purpose: push-to-talk needs no voice-activity detection, so
 * a demo in a noisy hall still works. The real Phone Link line is half-duplex too.
 */
const NUMBER_PAUSE_MS = 3000
const DTMF = { 1: [697, 1209], 2: [697, 1336], 3: [697, 1477], 4: [770, 1209], 5: [770, 1336], 6: [770, 1477],
  7: [852, 1209], 8: [852, 1336], 9: [852, 1477], '*': [941, 1209], 0: [941, 1336], '#': [941, 1477] }

let audioCtx = null
function beep(key) {
  // The real key tone, so the demo sounds like the phone line it simulates.
  try {
    audioCtx = audioCtx || new AudioContext()
    const gain = audioCtx.createGain()
    gain.gain.value = 0.08
    gain.connect(audioCtx.destination)
    for (const f of DTMF[key] || []) {
      const osc = audioCtx.createOscillator()
      osc.frequency.value = f
      osc.connect(gain)
      osc.start()
      osc.stop(audioCtx.currentTime + 0.12)
    }
  } catch {
    // No Web Audio: the key still goes through.
  }
}

export default function VoiceCall({ msisdn, onEnd, pressed }) {
  const [callId] = useState(() => crypto.randomUUID())
  const [state, setState] = useState('idle') // idle | recording | thinking
  const [turns, setTurns] = useState([])
  const [error, setError] = useState('')
  const [digits, setDigits] = useState('')
  const recorder = useRef(null)
  const chunks = useRef([])
  const player = useRef(null)
  const expectNumber = useRef(false)
  const pauseTimer = useRef(null)
  const typed = useRef('') // number entry in progress; `digits` mirrors it for display

  useEffect(() => () => { player.current?.pause(); clearTimeout(pauseTimer.current) }, [])

  const speak = (body) => {
    if (body.audio_b64) {
      player.current?.pause()
      player.current = new Audio(`data:${body.audio_type};base64,${body.audio_b64}`)
      player.current.play().catch(() => {})
    } else if (body.tts_error) {
      setError(`শব্দ তৈরি হয়নি: ${body.tts_error}`)
    }
  }

  const sendKeys = async (keys) => {
    clearTimeout(pauseTimer.current)
    typed.current = ''
    setDigits('')
    if (!keys.replace(/#/g, '')) return
    setState('thinking')
    setError('')
    try {
      const body = await voiceKeys(msisdn, callId, keys)
      expectNumber.current = Boolean(body.expects_number)
      setTurns((prev) => [...prev, { transcript: `⌨ ${keys}`, reply_text: body.answer || body.screen }])
      speak(body)
    } catch (err) {
      setError(err.message)
    } finally {
      setState('idle')
    }
  }

  // A key from the phone's keypad (PhonePage): menu choices go at once,
  // number entry waits for # or a pause.
  useEffect(() => {
    if (!pressed) return
    const { key } = pressed
    beep(key)
    if (expectNumber.current && key !== '*') {
      if (key === '#') {
        sendKeys(`${typed.current}#`)
        return
      }
      typed.current += key
      setDigits(typed.current)
      clearTimeout(pauseTimer.current)
      const entry = typed.current
      pauseTimer.current = setTimeout(() => sendKeys(entry), NUMBER_PAUSE_MS)
      return
    }
    sendKeys(key)
    // sendKeys is stable enough for this: it only reads refs and props that do not change mid-call.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pressed])

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
      speak(body)
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
      {turns.length === 0 && <p className="lcd-hint">কথা বলুন, অথবা মেনুর জন্য বোতাম চাপুন</p>}
      <ol className="call-turns">
        {turns.map((t, i) => (
          <li key={i}>
            <p className="turn-q">{t.transcript || '…'}</p>
            <p className="turn-a">{t.reply_text}</p>
          </li>
        ))}
      </ol>
      {digits && <p className="lcd-entry mono">› {digits} (শেষে #)</p>}
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
