/**
 * Farmer-facing preferences: language, text size, and the voice used to read
 * replies aloud.
 *
 * These are the first thing in this app to survive a reload — everything else
 * is server state or in-memory. localStorage is the right store for them: they
 * belong to the device (a shared family phone in sunlight wants big text
 * regardless of who is signed in), they must apply before the first paint, and
 * they are worthless to anyone but this browser.
 *
 * Language is NOT purely cosmetic. It is sent with every chat turn so the agent
 * answers in the chosen language — CLAUDE.md rule 10 makes Bangla the default
 * and says the reply mirrors the farmer; this makes "the farmer" explicit
 * instead of inferring it from whatever script they last typed in.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'

const KEY = 'agrisense.settings.v1'

export const DEFAULTS = {
  language: 'bn', // Bangla-first (CLAUDE.md rule 10)
  fontSize: 'medium',
  voiceURI: '',
  voiceRate: 1,
}

// `medium` is deliberately the app's existing 15px root (index.css) so the
// default view is unchanged; the other two step meaningfully, because a step
// too small to notice is a control that looks broken.
export const FONT_PX = { small: 13.5, medium: 15, large: 18 }

function read() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return DEFAULTS
    const saved = JSON.parse(raw)
    // Spread over DEFAULTS, so a settings file written by an older build (or a
    // hand-edited one) can never leave a key undefined.
    return { ...DEFAULTS, ...saved }
  } catch {
    return DEFAULTS
  }
}

export function useSettings() {
  const [settings, setSettings] = useState(read)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(settings))
    } catch {
      /* private mode / quota — preferences just don't persist, app still works */
    }
  }, [settings])

  useEffect(() => {
    const root = document.documentElement
    root.style.fontSize = `${FONT_PX[settings.fontSize] ?? FONT_PX.medium}px`
    root.lang = settings.language === 'en' ? 'en' : 'bn'
  }, [settings.fontSize, settings.language])

  const set = useCallback((patch) => setSettings((s) => ({ ...s, ...patch })), [])
  const reset = useCallback(() => setSettings(DEFAULTS), [])

  // BCP-47 tags for the Web Speech APIs. bn-BD, not bn-IN: the vocabulary and
  // accent differ enough to matter for a Bangladeshi farmer.
  const speechLang = settings.language === 'en' ? 'en-US' : 'bn-BD'

  return useMemo(
    () => ({ ...settings, speechLang, set, reset }),
    [settings, speechLang, set, reset],
  )
}
