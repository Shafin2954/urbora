/**
 * Settings — language, text size, and the reading voice.
 *
 * Three controls, no tabs, no sections that need scrolling past. Each one is a
 * row of large tap targets rather than a <select>, because a segmented row
 * shows the farmer what the options ARE without a tap, and a dropdown on a
 * cheap Android phone is a system-styled sheet that fights the rest of the app.
 * The voice picker is the exception: it can hold thirty OS voices, which no row
 * of buttons survives.
 *
 * Every change applies immediately — no Save button. The whole point of a text
 * size control is watching the text resize while you choose.
 */
import { useEffect, useState } from 'react'
import { FONT_PX } from '../state/useSettings.js'

const supportsSpeech = () => typeof window !== 'undefined' && 'speechSynthesis' in window

function Segmented({ label, note, value, options, onChange }) {
  return (
    <div className="setting">
      <span className="setting-label">{label}</span>
      <div className="segmented" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`segment${option.value === value ? ' is-on' : ''}`}
            aria-pressed={option.value === value}
            onClick={() => onChange(option.value)}
            style={option.px ? { fontSize: `${option.px}px` } : undefined}
          >
            {option.label}
          </button>
        ))}
      </div>
      {note && <p className="setting-note">{note}</p>}
    </div>
  )
}

export default function SettingsModal({ settings, t, onClose }) {
  const [voices, setVoices] = useState([])

  useEffect(() => {
    if (!supportsSpeech()) return undefined
    // Chrome populates the voice list asynchronously and fires voiceschanged
    // once it has; reading it only on mount reliably yields [] on a cold load.
    const load = () => setVoices(window.speechSynthesis.getVoices())
    load()
    window.speechSynthesis.addEventListener('voiceschanged', load)
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load)
  }, [])

  // Preferred voices first: a Bangla setting should not have to scroll past
  // forty English voices to find the one that can actually read the reply.
  const wanted = settings.language === 'en' ? 'en' : 'bn'
  const sorted = [...voices].sort((a, b) => {
    const rank = (v) => (v.lang?.toLowerCase().startsWith(wanted) ? 0 : 1)
    return rank(a) - rank(b) || a.name.localeCompare(b.name)
  })

  const preview = () => {
    if (!supportsSpeech()) return
    const sample = settings.language === 'en'
      ? 'This is how replies will sound.'
      : 'উত্তর এভাবেই পড়ে শোনানো হবে।'
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(sample)
    utterance.lang = settings.speechLang
    utterance.rate = settings.voiceRate
    const chosen = voices.find((v) => v.voiceURI === settings.voiceURI)
    if (chosen) utterance.voice = chosen
    window.speechSynthesis.speak(utterance)
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="settings-card" role="dialog" aria-modal="true" aria-label={t('settings.title')} onClick={(e) => e.stopPropagation()}>
        <header className="settings-head">
          <h2>{t('settings.title')}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label={t('settings.close')}>✕</button>
        </header>

        <Segmented
          label={t('settings.language')}
          note={t('settings.languageNote')}
          value={settings.language}
          onChange={(language) => settings.set({ language })}
          options={[
            { value: 'bn', label: t('settings.bangla') },
            { value: 'en', label: t('settings.english') },
          ]}
        />

        <Segmented
          label={t('settings.fontSize')}
          value={settings.fontSize}
          onChange={(fontSize) => settings.set({ fontSize })}
          options={[
            { value: 'small', label: t('settings.small'), px: FONT_PX.small },
            { value: 'medium', label: t('settings.medium'), px: FONT_PX.medium },
            { value: 'large', label: t('settings.large'), px: FONT_PX.large },
          ]}
        />

        <div className="setting">
          <span className="setting-label">{t('settings.voice')}</span>
          {supportsSpeech() && sorted.length > 0 ? (
            <>
              <select
                className="field"
                value={settings.voiceURI}
                onChange={(event) => settings.set({ voiceURI: event.target.value })}
              >
                <option value="">{t('settings.voiceDefault')}</option>
                {sorted.map((voice) => (
                  <option key={voice.voiceURI} value={voice.voiceURI}>
                    {voice.name} ({voice.lang})
                  </option>
                ))}
              </select>

              <label className="slider-row">
                <span>{t('settings.speed')}: {settings.voiceRate.toFixed(1)}x</span>
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={settings.voiceRate}
                  onChange={(event) => settings.set({ voiceRate: Number(event.target.value) })}
                />
              </label>

              <button type="button" className="secondary" onClick={preview}>▶ {t('settings.speak')}</button>
              <p className="setting-note">{t('settings.voiceNote')}</p>
            </>
          ) : (
            // Say the browser has none rather than showing an empty dropdown
            // that looks like the app failed to load them.
            <p className="setting-note">{t('settings.voiceNone')}</p>
          )}
        </div>

        <div className="settings-foot">
          <button type="button" className="secondary" onClick={settings.reset}>{t('settings.reset')}</button>
          <button type="button" onClick={onClose}>{t('settings.close')}</button>
        </div>
      </div>
    </div>
  )
}
