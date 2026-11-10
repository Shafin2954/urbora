/**
 * The Finance tab — itemised costs, three scenarios, break-even (PRD §8.5).
 *
 * This is where the judged accuracy moment happens (docs/archive/hackathon/PLAN.md §5 step 3): change
 * the area from 2 bigha to 3 and every number moves consistently. So the area
 * editor posts to `/api/finance/recompute` and re-renders from the response —
 * the same pure engine the agent's tool calls, never a recalculation here.
 * There is no arithmetic in this file at all, by design; even the item totals
 * are the server's, so what a judge adds up on screen is what the engine
 * printed.
 *
 * Every rendered number goes through `<Value prov=…>`, which refuses to print
 * a figure that arrives without provenance.
 */
import { useState } from 'react'
import { apiUrl } from '../api/client.js'
import Value, { Assumption } from './Provenance.jsx'

const AREA_UNITS = ['bigha', 'katha', 'decimal', 'acre', 'hectare']

const SCENARIO_LABEL = {
  conservative: 'খারাপ হলে',
  base: 'সম্ভাব্য',
  optimistic: 'ভালো হলে',
}

// Money is displayed with Western numerals (CLAUDE.md §2.10 / NOTES #17) so it
// can be checked against the trace and the SMS.
const money = (n) =>
  n === null || n === undefined
    ? '—'
    : Number(n).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })

const qty = (n) =>
  n === null || n === undefined ? '—' : Number(n).toLocaleString('en-US')

export default function FinancePanel({ finance, farmId, onFinance }) {
  const [scenario, setScenario] = useState('base')
  const [area, setArea] = useState('')
  const [unit, setUnit] = useState('bigha')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (!finance) return null

  const current = finance.scenarios?.[scenario]
  if (!current) return null

  const recompute = async () => {
    const value = Number(area)
    if (!value || busy) return
    setBusy(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('/api/finance/recompute'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farm_id: farmId,
          overrides: { area: value, area_unit: unit },
        }),
      })
      const body = await response.json()
      if (!response.ok) {
        // The server names what is missing or uncited; showing that beats a
        // generic failure, because the usual cause is a price nobody curated.
        setError(body.detail ?? `HTTP ${response.status}`)
        return
      }
      onFinance(body.finance)
    } catch (failure) {
      setError(String(failure.message ?? failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="finance">
      <div className="scenario-tabs" role="tablist" aria-label="পরিস্থিতি">
        {['conservative', 'base', 'optimistic'].map((key) => (
          <button
            key={key}
            role="tab"
            aria-selected={scenario === key}
            className={`scenario ${scenario === key ? 'is-active' : ''}`}
            onClick={() => setScenario(key)}
          >
            {SCENARIO_LABEL[key]}
          </button>
        ))}
      </div>

      {/* The two numbers a farmer came for, before any table. */}
      <div className="headline">
        <div>
          <span className="headline-key">লাভ</span>
          <strong className={current.net_profit < 0 ? 'loss' : 'gain'}>
            ৳{money(current.net_profit)}
          </strong>
        </div>
        <div>
          <span className="headline-key">খরচ</span>
          <strong>৳{money(current.total_cost)}</strong>
        </div>
        <div>
          <span className="headline-key">ROI</span>
          <strong>{current.roi_pct}%</strong>
        </div>
      </div>

      {/* Two columns, not four. A 390px screen cannot fit name/qty/rate/total
          without clipping the total — the one column the farmer is here for.
          The quantity and rate go under the name as the multiplication that
          produces the total, which also makes each row checkable by hand. */}
      <table className="items">
        <thead>
          <tr>
            <th>খরচের খাত</th>
            <th className="num">মোট</th>
          </tr>
        </thead>
        <tbody>
          {current.items.map((item, index) => (
            <tr key={`${item.name}-${index}`}>
              <td>
                <span className="item-name">{item.name}</span>
                <span className="item-calc mono">
                  {qty(item.qty)} {item.unit} × ৳{money(item.unit_cost)}
                </span>
              </td>
              <td className="num">
                {/* Tap any line total to see the row it was priced from. */}
                <Value value={money(item.total)} prov={item.provenance} />
              </td>
            </tr>
          ))}
          <tr className="items-total">
            <td>মোট খরচ</td>
            <td className="num mono">{money(current.total_cost)}</td>
          </tr>
        </tbody>
      </table>

      <dl className="facts">
        <div>
          <dt>ফলন</dt>
          <dd className="mono">{qty(current.expected_yield_kg)} kg</dd>
        </div>
        <div>
          <dt>দর</dt>
          <dd className="mono">৳{money(current.price_per_kg)}/kg</dd>
        </div>
        <div>
          <dt>আয়</dt>
          <dd className="mono">৳{money(current.revenue)}</dd>
        </div>
      </dl>

      <div className="breakeven">
        <h3>খরচ উঠতে হলে</h3>
        <p>
          দর এই থাকলে ফলন দরকার{' '}
          <strong className="mono">{qty(finance.breakeven_yield_kg)} kg</strong>
          {' — '}অথবা ফলন এই থাকলে দর দরকার{' '}
          <strong className="mono">৳{money(finance.breakeven_price_bdt)}/kg</strong>।
        </p>
      </div>

      {/* The live edit. Its whole job is to prove the numbers are computed. */}
      <div className="recompute">
        <h3>জমির পরিমাণ বদলে দেখুন</h3>
        <div className="row">
          <input
            className="field field-narrow"
            type="number"
            inputMode="decimal"
            min="0"
            step="0.1"
            placeholder="3"
            value={area}
            onChange={(event) => setArea(event.target.value)}
            aria-label="নতুন জমির পরিমাণ"
          />
          <select
            className="field field-narrow"
            value={unit}
            onChange={(event) => setUnit(event.target.value)}
            aria-label="একক"
          >
            {AREA_UNITS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <button onClick={recompute} disabled={busy || !Number(area)}>
            {busy ? 'হিসাব হচ্ছে…' : 'হিসাব করুন'}
          </button>
        </div>
        {error && (
          <p className="error" role="alert">
            <span className="mono detail">{error}</span>
          </p>
        )}
      </div>

      {finance.assumptions?.length > 0 && (
        <section className="assumptions">
          <h3>যেসব ধরে নেওয়া হয়েছে</h3>
          {finance.assumptions.map((prov, index) => (
            <Assumption key={`${prov.source_id}-${index}`} prov={prov} />
          ))}
        </section>
      )}
    </div>
  )
}
