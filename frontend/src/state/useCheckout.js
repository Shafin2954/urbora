/**
 * Checkout state machine.
 *
 *   basket ──getQuote──► confirm ──charge──► done
 *      ▲                    │                 │
 *      └────── cancel ──────┘                 └── reset ──► basket
 *
 * The `confirm` stage exists because CLAUDE.md §2.13 requires a confirmation
 * step before any charge. It is enforced on the server (a charge without a
 * registered quote is a 409), so this stage is the farmer-facing half of a
 * guarantee, not the guarantee itself.
 *
 * Two things this hook deliberately does NOT do:
 *   - It never derives the mode. That comes from the server, which reads it off
 *     the client object actually in use (rule 13: simulated output can never be
 *     hand-labelled live).
 *   - It never composes the receipt. The server returns the exact text sent to
 *     the phone; a second copy built here would eventually disagree with the SMS.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  CheckoutHttpError,
  chargeConfirmed,
  fetchCheckoutMode,
  requestQuote,
} from '../api/checkout.js'

/** Bangla for the farmer, technical detail kept separately for the judge. */
function describe(error) {
  if (error instanceof CheckoutHttpError) {
    if (error.status === 409) {
      return {
        bn: 'নিশ্চিতকরণের মেয়াদ শেষ হয়েছে। আবার নিশ্চিত করুন।',
        detail: error.detail,
        recoverable: true,
      }
    }
    if (error.status === 400) {
      return {
        bn: 'নম্বরটি সঠিক নয়। ১১ সংখ্যার মোবাইল নম্বর দিন।',
        detail: error.detail,
        recoverable: true,
      }
    }
    return { bn: 'সার্ভারে সমস্যা হয়েছে।', detail: error.detail, recoverable: true }
  }
  // A network failure is not a payment failure — say so, because "it failed"
  // and "we don't know whether it failed" are different things to a farmer.
  return {
    bn: 'সংযোগ পাওয়া যায়নি। টাকা কাটা হয়নি বলে ধরে নিন, তবে ব্যালেন্স দেখে নিন।',
    detail: String(error?.message ?? error),
    recoverable: true,
  }
}

export function useCheckout(basket) {
  const [stage, setStage] = useState('basket')
  const [mobile, setMobile] = useState('')
  const [quote, setQuote] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState(null)

  const abort = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchCheckoutMode(controller.signal)
      .then((body) => setMode(body.mode))
      // Mode unknown is its own state: the UI must say "unknown" rather than
      // guess "simulator", because guessing wrong in the other direction is
      // how simulated output gets presented as live.
      .catch(() => setMode(null))
    return () => controller.abort()
  }, [])

  useEffect(() => () => abort.current?.abort(), [])

  const body = useCallback(
    () => ({
      farm_id: basket?.farmId ?? '',
      mobile,
      amount: basket?.amount ?? 0,
      items: basket?.items ?? [],
    }),
    [basket, mobile],
  )

  const getQuote = useCallback(async () => {
    if (!basket || busy) return
    abort.current?.abort()
    abort.current = new AbortController()
    setBusy(true)
    setError(null)
    try {
      const got = await requestQuote(body(), abort.current.signal)
      setQuote(got)
      setStage('confirm')
    } catch (failure) {
      if (failure.name !== 'AbortError') setError(describe(failure))
    } finally {
      setBusy(false)
    }
  }, [basket, body, busy])

  const confirm = useCallback(async () => {
    // The double-tap guard. The server's quote is single-use so a second charge
    // would be refused anyway, but a farmer on a laggy phone should not have to
    // rely on that to avoid seeing an alarming error.
    if (busy || stage !== 'confirm') return
    abort.current?.abort()
    abort.current = new AbortController()
    setBusy(true)
    setError(null)
    try {
      const got = await chargeConfirmed(body(), abort.current.signal)
      setResult(got)
      setStage('done')
    } catch (failure) {
      if (failure.name === 'AbortError') return
      const described = describe(failure)
      setError(described)
      // A stale confirmation sends the farmer back to re-confirm rather than
      // leaving a dead "confirm" button that will keep failing.
      if (failure.status === 409) {
        setQuote(null)
        setStage('basket')
      }
    } finally {
      setBusy(false)
    }
  }, [body, busy, stage])

  const cancel = useCallback(() => {
    abort.current?.abort()
    setQuote(null)
    setError(null)
    setStage('basket')
  }, [])

  const reset = useCallback(() => {
    abort.current?.abort()
    setQuote(null)
    setResult(null)
    setError(null)
    setStage('basket')
  }, [])

  return {
    stage,
    mobile,
    setMobile,
    quote,
    result,
    error,
    busy,
    mode,
    getQuote,
    confirm,
    cancel,
    reset,
  }
}
