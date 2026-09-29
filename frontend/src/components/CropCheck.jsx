import { useEffect, useMemo, useState } from 'react'
import { triageCheck, triageOptions } from '../api/triage.js'
import Value from './Provenance.jsx'

// "ফসলের সমস্যা চিনুন": the product's first job, on the web. Six taps, the same questions the
// keypad menu asks, answered by the deterministic KB table (backend/api/triage.py). The AI model
// is not involved; a combination the KB does not cover says so. The dose total for the farmer's
// land is computed by units.scale_rate and shown with its provenance.

const CROP_ICON = { aman_rice: '🌾', boro_rice: '🌾', potato: '🥔', mustard: '🌼', lentil: '🫘' }
const STEPS = ['crop', 'stage', 'organ', 'symptom', 'extent', 'weather', 'area']
const STEP_Q = {
  crop: 'কোন ফসল?',
  stage: 'ফসল এখন কোন অবস্থায়?',
  organ: 'গাছের কোথায় সমস্যা দেখছেন?',
  symptom: 'দেখতে কেমন?',
  extent: 'জমির কতটুকুতে?',
  weather: 'গত সপ্তাহে কী হয়েছিল?',
  area: 'জমি কত বিঘা? (মাত্রা হিসাবের জন্য)',
}
const COVERAGE = {
  S: { label: 'তথ্যের সাথে মিলে যায়', cls: 'cov-s' },
  W: { label: 'হতে পারে', cls: 'cov-w' },
  P: { label: 'নাম জানা, দমনের যাচাই করা তথ্য নেই', cls: 'cov-p' },
}
const bnDigits = (s) => String(s).replace(/[0-9]/g, (d) => '০১২৩৪৫৬৭৮৯'[d])

export default function CropCheck() {
  const [opts, setOpts] = useState(null)
  const [err, setErr] = useState('')
  const [ans, setAns] = useState({})
  const [area, setArea] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    triageOptions().then(setOpts).catch(() => setErr('সার্ভারের সাথে যোগাযোগ হচ্ছে না। একটু পরে আবার চেষ্টা করুন।'))
  }, [])

  const crop = useMemo(() => opts?.crops.find((c) => c.key === ans.crop), [opts, ans.crop])
  const organ = useMemo(() => crop?.organs.find((o) => o.key === ans.organ), [crop, ans.organ])
  const step = STEPS.find((s) => s !== 'area' && !ans[s]) || 'area'

  const choices = () => {
    if (!opts) return []
    switch (step) {
      case 'crop': return opts.crops.map((c) => ({ key: c.key, label: c.name_bn, icon: CROP_ICON[c.key] }))
      case 'stage': return crop.stages.map((s) => ({
        key: s.key, label: s.name_bn,
        hint: `${bnDigits(s.days[0])}–${bnDigits(s.days[1])} দিন ${crop.days_basis === 'after_transplanting' ? 'রোপণের পর' : 'বোনার পর'}`,
      }))
      case 'organ': return crop.organs.map((o) => ({ key: o.key, label: o.name_bn, icon: o.icon }))
      case 'symptom': return organ.symptoms.map((s) => ({ key: s.key, label: s.name_bn }))
      case 'extent': return opts.extents.map((e) => ({ key: e.key, label: e.name_bn }))
      case 'weather': return opts.weather.map((w) => ({ key: w.key, label: w.name_bn }))
      default: return []
    }
  }

  const pick = (key) => {
    setResult(null)
    // changing an earlier answer clears everything after it
    const i = STEPS.indexOf(step)
    const next = Object.fromEntries(Object.entries(ans).filter(([k]) => STEPS.indexOf(k) < i))
    setAns({ ...next, [step]: key })
  }
  const back = (k) => {
    setResult(null)
    const i = STEPS.indexOf(k)
    setAns(Object.fromEntries(Object.entries(ans).filter(([s]) => STEPS.indexOf(s) < i)))
  }
  const labelOf = (k) => {
    if (!opts) return ''
    const v = ans[k]
    if (k === 'crop') return crop?.name_bn
    if (k === 'stage') return crop?.stages.find((s) => s.key === v)?.name_bn
    if (k === 'organ') return organ?.name_bn
    if (k === 'symptom') return organ?.symptoms.find((s) => s.key === v)?.name_bn
    if (k === 'extent') return opts.extents.find((e) => e.key === v)?.name_bn
    if (k === 'weather') return opts.weather.find((w) => w.key === v)?.name_bn
    return ''
  }

  const submit = async (e) => {
    e?.preventDefault()
    setBusy(true); setErr('')
    try {
      const a = parseFloat(String(area).replace(/[০-৯]/g, (d) => '০১২৩৪৫৬৭৮৯'.indexOf(d)))
      setResult(await triageCheck({ ...ans, area_bigha: a > 0 ? a : null }))
    } catch {
      setErr('উত্তর আনা গেল না। আবার চেষ্টা করুন।')
    } finally {
      setBusy(false)
    }
  }
  const restart = () => { setAns({}); setArea(''); setResult(null) }

  const done = STEPS.filter((s) => s !== 'area' && ans[s])
  return (
    <div className="check">
      <ol className="check-trail" aria-label="আপনার উত্তর">
        {done.map((k) => (
          <li key={k}><button type="button" className="chip-done" onClick={() => back(k)} title="বদলাতে চাপুন">{labelOf(k)} <span aria-hidden="true">✎</span></button></li>
        ))}
      </ol>

      {err && <p className="check-err" role="alert">{err}</p>}
      {!opts && !err && <p className="check-wait">প্রশ্ন আনা হচ্ছে…</p>}

      {opts && !result && step !== 'area' && (
        <fieldset className="check-step" key={step}>
          <legend><span className="check-no">{bnDigits(STEPS.indexOf(step) + 1)}/৭</span>{STEP_Q[step]}</legend>
          <div className="choice-grid">
            {choices().map((c) => (
              <button type="button" key={c.key} className="choice" onClick={() => pick(c.key)}>
                {c.icon && <span className="choice-icon" aria-hidden="true">{c.icon}</span>}
                <span className="choice-label">{c.label}</span>
                {c.hint && <small>{c.hint}</small>}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {opts && !result && step === 'area' && (
        <form className="check-step" onSubmit={submit}>
          <legend><span className="check-no">৭/৭</span>{STEP_Q.area}</legend>
          <div className="area-row">
            <label className="area-field">
              <input id="check-area" inputMode="decimal" placeholder="যেমন ২" value={area} onChange={(e) => setArea(e.target.value)} aria-label="জমি, বিঘায়" />
              <span>বিঘা</span>
            </label>
            <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'খোঁজা হচ্ছে…' : 'উত্তর দেখুন'}</button>
          </div>
          <p className="area-note">না জানলে ফাঁকা রাখুন। ১ বিঘা = ৩৩ শতাংশ।</p>
        </form>
      )}

      {result && <Result r={result} onRestart={restart} />}
    </div>
  )
}

function Result({ r, onRestart }) {
  return (
    <article className="check-result" aria-live="polite">
      <header>
        <p className="result-case">{r.summary_bn}</p>
        {r.coverage === 'none'
          ? <span className="cov cov-p">তথ্য যথেষ্ট নয়</span>
          : <span className={`cov ${r.coverage === 'covered' ? 'cov-s' : 'cov-w'}`}>{r.coverage === 'covered' ? 'যাচাই করা তথ্য' : 'আংশিক তথ্য'}</span>}
      </header>

      {r.no_kb_bn && <p className="result-honest">{r.no_kb_bn}</p>}

      {r.candidates.length > 0 && (
        <ul className="result-list">
          {r.candidates.map((c, i) => (
            <li key={c.key} className={i === 0 ? 'top' : ''}>
              <div className="cand-head">
                <h4>{i === 0 ? 'সম্ভবত: ' : 'অথবা: '}{c.name_bn}</h4>
                <span className={`cov ${COVERAGE[c.coverage].cls}`}>{COVERAGE[c.coverage].label}</span>
              </div>
              {c.advice_bn && <p>{c.advice_bn}</p>}
              {c.source.title && <cite>সূত্র: {c.source.title}</cite>}
            </li>
          ))}
        </ul>
      )}

      {r.dose && (
        <div className="result-dose">
          <p className="dose-label">মাত্রা (তথ্যসূত্রে যেমন লেখা)</p>
          <p className="dose-text">{r.dose.text_bn}</p>
          {r.dose.total && (
            <p className="dose-total">
              আপনার জমিতে মোট <Value value={r.dose.total.value} prov={r.dose.total.prov} unit={r.dose.total.unit} />
              {r.dose.water_l && <> , {r.dose.water_l} লিটার পানিতে</>}
            </p>
          )}
          {r.dose.source.title && <cite>সূত্র: {r.dose.source.title}</cite>}
        </div>
      )}

      {r.safety_bn.length > 0 && <ul className="result-safety">{r.safety_bn.map((s) => <li key={s}>{s}</li>)}</ul>}

      <footer className="result-foot">
        <p>এই উত্তর এসেছে যাচাই করা কৃষি তথ্যের সারণি থেকে। AI এখানে আন্দাজ করে না।</p>
        <div className="result-actions">
          <button type="button" className="btn btn-quiet" onClick={onRestart}>আবার শুরু করুন</button>
          <a className="btn btn-primary" href="/?guest=1#/app">আরও জিজ্ঞেস করুন</a>
        </div>
      </footer>
    </article>
  )
}
