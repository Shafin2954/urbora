import { useCallback, useEffect, useRef, useState } from 'react'
import ChannelMonitor from '../components/ChannelMonitor.jsx'
import { channelStatus, fetchInbox, missedCall, sendSms, ussdStep } from '../api/channels.js'
import { BRAND_NAME } from '../branding.js'
import VoiceCall from './VoiceCall.jsx'
import './phone.css'

const DEMO_CODE = '*3700#'
const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']

/**
 * A button phone in the browser — the SIMULATOR for the channels a real
 * farmer uses on a real SIM: dial a USSD code, send an SMS, give a missed
 * call, or call the voice line. Every request goes to the same backend flows
 * a real gateway would hit (backend/api/channels.py), and the monitor beside
 * it replays the agent's trace for the conversation. Labelled সিমুলেটর
 * throughout (CLAUDE.md rules 13 and 15): nothing here touches a phone network.
 */
const PhoneIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
    <path
      fill="currentColor"
      d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.6a1 1 0 0 1-.25 1l-2.2 2.2z"
    />
  </svg>
)

export default function PhonePage() {
  const [msisdn, setMsisdn] = useState('01712345678')
  const [view, setView] = useState('home') // home | ussd | sms | call
  const [callKey, setCallKey] = useState(null) // latest keypad press during a call
  const [entry, setEntry] = useState('')
  const [screen, setScreen] = useState('')
  const [ussdSession, setUssdSession] = useState(null)
  const [ussdEnded, setUssdEnded] = useState(false)
  const [inbox, setInbox] = useState([])
  const [smsDraft, setSmsDraft] = useState('')
  const [notice, setNotice] = useState('')
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const lastSeen = useRef(0)
  const lcdRef = useRef(null)
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    channelStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  // The inbox is polled: replies come from the agent in the background.
  useEffect(() => {
    let alive = true
    const tick = () =>
      fetchInbox(msisdn)
        .then((body) => {
          if (!alive) return
          setInbox(body.messages)
          const outCount = body.messages.filter((m) => m.direction === 'out').length
          setUnread(view === 'sms' ? 0 : Math.max(0, outCount - lastSeen.current))
          if (view === 'sms') lastSeen.current = outCount
        })
        .catch(() => {})
    tick()
    const id = setInterval(tick, 2000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [msisdn, view])

  const dialUssd = useCallback(async () => {
    const session = crypto.randomUUID()
    setBusy(true)
    try {
      const body = await ussdStep(session, msisdn, null, true)
      setUssdSession(session)
      setScreen(body.text)
      setUssdEnded(body.end)
      setView('ussd')
    } catch (err) {
      setNotice(err.message)
    } finally {
      setBusy(false)
      setEntry('')
    }
  }, [msisdn])

  const replyUssd = useCallback(
    async (text) => {
      if (!ussdSession || ussdEnded) return
      setBusy(true)
      try {
        const body = await ussdStep(ussdSession, msisdn, text)
        setScreen(body.text)
        setUssdEnded(body.end)
      } catch (err) {
        setNotice(err.message)
      } finally {
        setBusy(false)
        setEntry('')
      }
    },
    [msisdn, ussdSession, ussdEnded],
  )

  // During a call the keypad sends tones to the call (the spoken menu); otherwise it types.
  const onKey = (k) => {
    if (view === 'call') return setCallKey({ key: k, seq: Date.now() })
    setEntry((e) => e + k)
  }

  const onGreen = () => {
    setNotice('')
    if (view === 'ussd') return replyUssd(entry)
    if (/^\*\d+#$/.test(entry)) return dialUssd()
    if (entry === '') return setView('call')
    setNotice(`USSD কোড ডায়াল করুন, যেমন ${DEMO_CODE}`)
  }

  const onRed = () => {
    setView('home')
    setEntry('')
    setScreen('')
    setUssdSession(null)
    setUssdEnded(false)
    setNotice('')
  }

  const onMissedCall = async () => {
    setNotice('')
    try {
      await missedCall(msisdn)
      setNotice('মিসড কল দেওয়া হয়েছে। SMS আসছে…')
    } catch (err) {
      setNotice(err.message)
    }
  }

  const onSendSms = async (event) => {
    event.preventDefault()
    const text = smsDraft.trim()
    if (!text) return
    setSmsDraft('')
    try {
      await sendSms(msisdn, text)
    } catch (err) {
      setNotice(err.message)
    }
  }

  useEffect(() => {
    if (lcdRef.current) lcdRef.current.scrollTop = lcdRef.current.scrollHeight
  }, [inbox, screen, view])

  const emulatorOff = status && !status.emulator_enabled

  return (
    <main className="phone-page">
      <header className="phone-page-head">
        <a href="#/" className="back-link">← {BRAND_NAME}</a>
        <h1>বাটন ফোন</h1>
        <span className="badge-sim">সিমুলেটর</span>
      </header>

      {emulatorOff && (
        <p className="error">
          এমুলেটর বন্ধ: সার্ভার আসল SMS প্রদানকারী ({status.sms.provider}) ব্যবহার করছে।
        </p>
      )}

      <div className="phone-layout">
        <div className="phone-col">
          <label className="phone-number">
            ফোন নম্বর
            <input
              className="field mono"
              value={msisdn}
              onChange={(e) => setMsisdn(e.target.value)}
              inputMode="tel"
            />
          </label>

          <div className="handset" aria-label="বাটন ফোন সিমুলেটর">
            <div className="lcd" role="status" aria-live="polite" ref={lcdRef}>
              {view === 'home' && (
                <>
                  <p className="lcd-title">{BRAND_NAME}</p>
                  <p>ডায়াল করুন {DEMO_CODE}</p>
                  <p>অথবা সবুজ বোতাম = কল</p>
                  {unread > 0 && <p className="lcd-unread">✉ {unread} নতুন SMS</p>}
                  <p className="lcd-entry mono">{entry || ' '}</p>
                </>
              )}
              {view === 'ussd' && (
                <>
                  <pre className="lcd-text">{screen}</pre>
                  {!ussdEnded && <p className="lcd-entry mono">› {entry}</p>}
                  {ussdEnded && <p className="lcd-hint">লাল বোতাম = শেষ</p>}
                </>
              )}
              {view === 'sms' && (
                <ol className="lcd-thread">
                  {inbox.length === 0 && <li className="lcd-hint">কোনো SMS নেই</li>}
                  {inbox.map((m) => (
                    <li key={m.sms_id} className={`sms sms-${m.direction}`}>
                      <pre>{m.body}</pre>
                      <span className="sms-meta mono">{m.segments} SMS · {m.status}</span>
                    </li>
                  ))}
                </ol>
              )}
              {view === 'call' && <VoiceCall msisdn={msisdn} onEnd={onRed} pressed={callKey} />}
              {busy && <p className="lcd-hint">…</p>}
            </div>

            <div className="soft-keys">
              <button className="key key-green" onClick={onGreen} aria-label="কল বা পাঠান"><PhoneIcon /></button>
              <button className="key" onClick={() => setView(view === 'sms' ? 'home' : 'sms')}>
                ✉ SMS{unread > 0 ? ` (${unread})` : ''}
              </button>
              <button className="key key-red" onClick={onRed} aria-label="শেষ">✕</button>
            </div>
            <div className="keypad">
              {KEYS.map((k) => (
                <button key={k} className="key" onClick={() => onKey(k)}>{k}</button>
              ))}
            </div>
            <button className="key key-wide" onClick={() => setEntry((e) => e.slice(0, -1))}>⌫ মুছুন</button>
          </div>

          {view === 'ussd' && !ussdEnded && (
            <form className="phone-type" onSubmit={(e) => { e.preventDefault(); replyUssd(entry) }}>
              <input
                className="field"
                placeholder="লেখা উত্তর (যেমন প্রশ্ন)"
                value={entry}
                onChange={(e) => setEntry(e.target.value)}
              />
              <button className="btn">পাঠান</button>
            </form>
          )}
          {view === 'sms' && (
            <form className="phone-type" onSubmit={onSendSms}>
              <input
                className="field"
                placeholder="SMS লিখুন…"
                value={smsDraft}
                onChange={(e) => setSmsDraft(e.target.value)}
              />
              <button className="btn">পাঠান</button>
            </form>
          )}
          <button className="btn btn-quiet" onClick={onMissedCall}>মিসড কল দিন</button>
          {notice && <p className="phone-notice" role="status">{notice}</p>}
        </div>

        <div className="monitor-col">
          <ChannelMonitor follow />
        </div>
      </div>
    </main>
  )
}
