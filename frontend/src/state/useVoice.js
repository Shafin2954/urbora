/**
 * Voice in and out — docs/product/competition.md Tier 2, "Bengali or voice interaction for
 * low-literacy accessibility".
 *
 * The two halves use different mechanisms, for a reason worth recording.
 *
 * OUT (read-aloud) is `speechSynthesis`: on-device, free, and works everywhere
 * including Brave.
 *
 * IN (dictation) used to be `SpeechRecognition` from the same Web Speech API,
 * and that was a mistake. Brave keeps the constructor — so feature detection
 * says yes and the button appears — but blocks the Google relay the API needs,
 * so `start()` succeeds and the next event is a `network` error: the mic turns
 * on for a second and dies with nothing to show. Firefox never shipped the API
 * at all. Bangla dictation was a browser-and-vendor lottery, and the browser
 * this project is demoed in loses it.
 *
 * So recording is now `MediaRecorder` (universally supported) and recognition
 * happens on the server via Whisper (`POST /api/transcribe`). One path, every
 * browser, better Bengali. The trade-off is honest and stated in the README:
 * dictation now needs the network and the backend, where the old path ran
 * on-device.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { apiUrl } from '../api/client.js'

const hasRecorder =
  typeof window !== 'undefined' &&
  typeof window.MediaRecorder !== 'undefined' &&
  Boolean(navigator?.mediaDevices?.getUserMedia)

export const speechInputSupported = hasRecorder
export const speechOutputSupported =
  typeof window !== 'undefined' && 'speechSynthesis' in window

/**
 * Every way this can fail, in words the farmer can act on.
 *
 * The previous version surfaced the raw code ('network') in small grey text,
 * which is indistinguishable from silence. A farmer who is told "permission
 * denied" can fix it; one shown "network" cannot.
 */
const MESSAGES = {
  bn: {
    denied: 'মাইক্রোফোন ব্যবহারের অনুমতি দেওয়া হয়নি। ব্রাউজারের ঠিকানা বারের পাশে অনুমতি দিন।',
    notFound: 'কোনো মাইক্রোফোন পাওয়া যায়নি।',
    busy: 'মাইক্রোফোন অন্য কোথাও ব্যবহার হচ্ছে।',
    empty: 'কিছু শোনা যায়নি। আবার চেষ্টা করুন।',
    server: 'কথা লেখায় রূপান্তর করা গেল না। আবার চেষ্টা করুন।',
    generic: 'মাইক্রোফোন চালু করা গেল না।',
  },
  en: {
    denied: 'Microphone permission was blocked. Allow it from the icon in the address bar.',
    notFound: 'No microphone was found.',
    busy: 'The microphone is in use by another app.',
    empty: 'Nothing was heard. Try again.',
    server: 'Could not turn that speech into text. Try again.',
    generic: 'Could not start the microphone.',
  },
}

function describe(failure, lang) {
  const words = MESSAGES[lang === 'en' ? 'en' : 'bn']
  const name = failure?.name ?? ''
  if (name === 'NotAllowedError' || name === 'SecurityError') return words.denied
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return words.notFound
  if (name === 'NotReadableError' || name === 'AbortError') return words.busy
  if (failure?.status === 'server') return words.server
  if (failure?.status === 'empty') return words.empty
  return words.generic
}

/**
 * Hold-to-talk dictation. `onText` receives the finished transcript.
 *
 * There are three visible states rather than two, because a round trip is not
 * instant and a farmer staring at an unchanged box assumes it failed:
 * idle -> listening (recording) -> transcribing (uploaded, waiting).
 */
export function useDictation({ language, onText }) {
  const [listening, setListening] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [error, setError] = useState(null)

  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const onTextRef = useRef(onText)
  onTextRef.current = onText

  const release = useCallback(() => {
    // Stopping every track is what turns the browser's recording indicator off.
    // Without it the tab keeps claiming the mic after the farmer is done, which
    // is both alarming and a real privacy problem.
    recorderRef.current?.stream?.getTracks?.().forEach((track) => track.stop())
    recorderRef.current = null
  }, [])

  useEffect(() => () => release(), [release])

  const send = useCallback(async (blob) => {
    if (!blob || blob.size < 1200) {           // a tap, not an utterance
      setError(describe({ status: 'empty' }, language))
      return
    }
    setTranscribing(true)
    try {
      const form = new FormData()
      form.append('file', blob, 'speech.webm')
      form.append('language', language === 'en' ? 'en' : 'bn')
      const response = await fetch(apiUrl('/api/transcribe'), { method: 'POST', body: form })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw Object.assign(new Error(body.detail ?? 'failed'), { status: 'server' })
      const text = (body.text ?? '').trim()
      if (!text) { setError(describe({ status: 'empty' }, language)); return }
      onTextRef.current?.(text)
    } catch (failure) {
      setError(describe({ ...failure, status: failure.status ?? 'server' }, language))
    } finally {
      setTranscribing(false)
    }
  }, [language])

  const stop = useCallback(() => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') recorder.stop()
    setListening(false)
  }, [])

  const start = useCallback(async () => {
    if (recorderRef.current || transcribing) return
    setError(null)
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (failure) {
      setError(describe(failure, language))
      return
    }

    let recorder
    try {
      recorder = new MediaRecorder(stream)
    } catch {
      // Some browsers reject the default container; let them choose.
      recorder = new MediaRecorder(stream, { mimeType: '' })
    }

    chunksRef.current = []
    recorder.ondataavailable = (event) => {
      if (event.data?.size) chunksRef.current.push(event.data)
    }
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
      chunksRef.current = []
      release()
      send(blob)
    }

    recorderRef.current = recorder
    recorder.start()
    setListening(true)
  }, [language, release, send, transcribing])

  return {
    supported: hasRecorder,
    listening,
    transcribing,
    busy: listening || transcribing,
    error,
    start,
    stop,
    toggle: () => (listening ? stop() : start()),
  }
}

/** Read a reply aloud, using the voice and speed chosen in settings. */
export function useSpeech({ lang, voiceURI, rate }) {
  const [speakingId, setSpeakingId] = useState(null)

  const stop = useCallback(() => {
    if (!speechOutputSupported) return
    window.speechSynthesis.cancel()
    setSpeakingId(null)
  }, [])

  useEffect(() => stop, [stop])

  const speak = useCallback((text, id) => {
    if (!speechOutputSupported || !text) return
    // Always cancel first: speechSynthesis queues, so a second tap without this
    // reads both messages back to back instead of switching to the new one.
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    utterance.rate = rate
    const chosen = window.speechSynthesis.getVoices().find((v) => v.voiceURI === voiceURI)
    if (chosen) utterance.voice = chosen
    utterance.onend = () => setSpeakingId(null)
    utterance.onerror = () => setSpeakingId(null)

    setSpeakingId(id)
    window.speechSynthesis.speak(utterance)
  }, [lang, rate, voiceURI])

  return {
    supported: speechOutputSupported,
    speakingId,
    speak,
    stop,
    toggle: (text, id) => (speakingId === id ? stop() : speak(text, id)),
  }
}
