import { useCallback, useEffect, useState } from 'react'
import {
  cancelOrder, createListing, fetchCatalog, fetchDistricts, findInputs, myListings, myOrders,
  placeOrder, priceGuide, remember, respondOffer,
} from '../api/market.js'
import { BRAND_NAME } from '../branding.js'

const QUICK_INPUTS = ['urea', 'tsp', 'mop', 'mancozeb', 'tricyclazole', 'carbendazim']
const CROPS = [
  ['boro_rice', 'বোরো ধান'], ['aman_rice', 'আমন ধান'], ['potato', 'আলু'], ['mustard', 'সরিষা'], ['lentil', 'মসুর'],
]
const taka = (n) => `৳${Math.round(n).toLocaleString('en-US')}`
const OFFER_BN = { pending: 'অপেক্ষমাণ', accepted: 'গৃহীত', rejected: 'বাতিল', withdrawn: 'প্রত্যাহার' }
const distance = (km) => (km < 1 ? 'একই জেলায়' : `${km} কিমি`)

function DemoBadge({ on, label = 'ডেমো' }) {
  return on ? <span className="badge-demo">{label}</span> : null
}

function PriceGuide({ guide }) {
  if (!guide) return null
  const fg = guide.farm_gate
  const wp = guide.wholesale_pattern
  if (!fg && !wp) return <p className="muted">এই ফসলের কোনো উৎস-সহ দাম পাওয়া যায়নি।</p>
  return (
    <div className="guide">
      <h3>দামের ধারণা</h3>
      {fg && (
        <p>
          খামার-দাম <strong>{taka(fg.price_bdt_per_kg)}/কেজি</strong>{' '}
          <span className="muted">({fg.date}, {fg.provenance.source_title})</span>
        </p>
      )}
      {wp?.this_month_avg_bdt_per_kg != null && (
        <p>
          পাইকারি বাজারে এ মাসের গড় <strong>৳{wp.this_month_avg_bdt_per_kg}/কেজি</strong>{' '}
          <span className="muted">(অতীতের গড় {wp.years_covered}, পূর্বাভাস নয়; পাইকারি দাম, খামার-দাম নয়)</span>
        </p>
      )}
    </div>
  )
}

function Buy({ msisdn, districts, catalog, onOrdered }) {
  const [district, setDistrict] = useState('Rajshahi')
  const [product, setProduct] = useState('')
  const [result, setResult] = useState(null)
  const [packs, setPacks] = useState({})
  const [confirming, setConfirming] = useState(null)
  const [error, setError] = useState('')

  const search = async (generic) => {
    setProduct(generic)
    setError('')
    setConfirming(null)
    try {
      setResult(await findInputs(generic, district))
    } catch (err) {
      setError(err.message)
    }
  }

  const order = async (offer) => {
    try {
      await placeOrder(msisdn, offer.product_id, packs[offer.product_id] ?? 1)
      setConfirming(null)
      onOrdered()
    } catch (err) {
      setError(err.message)
    }
  }

  const label = (g) => catalog.find((c) => c.generic === g)?.label_bn ?? g
  return (
    <section className="market-section">
      <label className="field-label">
        জেলা
        <select className="field" value={district} onChange={(e) => setDistrict(e.target.value)}>
          {districts.map((d) => <option key={d.value} value={d.value}>{d.label_bn}</option>)}
        </select>
      </label>
      <div className="chip-row">
        {QUICK_INPUTS.map((g) => (
          <button key={g} className={`chip ${product === g ? 'chip-on' : ''}`} onClick={() => search(g)}>{label(g)}</button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {result && result.offers.length === 0 && <p className="muted">৮০ কিমির মধ্যে কোনো দোকানে পাওয়া যায়নি।</p>}
      {result && (
        <ol className="offers">
          {result.offers.map((o) => {
            const n = packs[o.product_id] ?? 1
            return (
              <li key={o.product_id} className="offer">
                <div className="offer-head">
                  <strong>{o.rank}. {o.dealer_name}</strong> <DemoBadge on={o.is_demo} label="ডেমো দোকান" />
                  {!o.verified && <span className="badge-quiet">যাচাই হয়নি</span>}
                </div>
                <p>
                  {o.brand_name}, {o.pack_size} {o.pack_unit} প্যাকেট — <strong>{taka(o.price_bdt)}</strong>{' '}
                  <span className="muted">(৳{o.unit_price}/{o.pack_unit})</span>
                </p>
                <p className="muted">
                  {distance(o.km)} · মজুদ {o.stock_packs} · স্কোর {o.score} (দাম {o.components.price}, দূরত্ব {o.components.distance},
                  মজুদ {o.components.stock}, আস্থা {o.components.trust})
                </p>
                <p className="muted small">উৎস: {o.provenance.source_title}, {o.provenance.locator}</p>
                <div className="offer-actions">
                  <label>
                    প্যাকেট
                    <input className="field field-narrow" type="number" min="1" max={o.stock_packs} value={n}
                      onChange={(e) => setPacks({ ...packs, [o.product_id]: Math.max(1, Number(e.target.value) || 1) })} />
                  </label>
                  {confirming === o.product_id ? (
                    <>
                      <span className="confirm-text">{taka(o.price_bdt * n)} দোকানে নগদে — নিশ্চিত?</span>
                      <button onClick={() => order(o)} disabled={!msisdn}>হ্যাঁ, অর্ডার</button>
                      <button className="secondary" onClick={() => setConfirming(null)}>না</button>
                    </>
                  ) : (
                    <button onClick={() => setConfirming(o.product_id)} disabled={!msisdn}>অর্ডার করুন</button>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      )}
      {result && !msisdn && <p className="notice">অর্ডার করতে উপরে ফোন নম্বর দিন — অর্ডারের খবর SMS-এ আসবে।</p>}
      {result && <p className="muted small">র‍্যাঙ্কিং: {result.ranking_rule}</p>}
    </section>
  )
}

function Sell({ msisdn, districts, onListed }) {
  const [crop, setCrop] = useState('potato')
  const [qty, setQty] = useState('')
  const [price, setPrice] = useState('')
  const [district, setDistrict] = useState('Rajshahi')
  const [guide, setGuide] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    priceGuide(crop).then(setGuide).catch(() => setGuide(null))
  }, [crop])

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    try {
      await createListing({ msisdn, crop, qty_kg: Number(qty), asking_price_per_kg: price ? Number(price) : null, district })
      setQty('')
      setPrice('')
      onListed()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section className="market-section">
      <div className="chip-row">
        {CROPS.map(([key, bn]) => (
          <button key={key} className={`chip ${crop === key ? 'chip-on' : ''}`} onClick={() => setCrop(key)}>{bn}</button>
        ))}
      </div>
      <PriceGuide guide={guide} />
      <form className="sell-form" onSubmit={submit}>
        <label className="field-label">কত কেজি
          <input className="field" type="number" min="1" required value={qty} onChange={(e) => setQty(e.target.value)} />
        </label>
        <label className="field-label">চাওয়া দাম (৳/কেজি, ঐচ্ছিক)
          <input className="field" type="number" min="0.1" step="0.1" value={price} onChange={(e) => setPrice(e.target.value)} />
        </label>
        <label className="field-label">জেলা
          <select className="field" value={district} onChange={(e) => setDistrict(e.target.value)}>
            {districts.map((d) => <option key={d.value} value={d.value}>{d.label_bn}</option>)}
          </select>
        </label>
        <button disabled={!msisdn}>তালিকা করুন</button>
      </form>
      {!msisdn && <p className="notice">তালিকা করতে উপরে ফোন নম্বর দিন — অফার SMS-এ আসবে।</p>}
      {error && <p className="error">{error}</p>}
    </section>
  )
}

function Mine({ msisdn, refresh }) {
  const [orders, setOrders] = useState([])
  const [listings, setListings] = useState([])
  const [error, setError] = useState('')
  const load = useCallback(() => {
    if (!msisdn) return
    myOrders(msisdn).then((d) => setOrders(d.orders)).catch((e) => setError(e.message))
    myListings(msisdn).then((d) => setListings(d.listings)).catch((e) => setError(e.message))
  }, [msisdn])
  useEffect(load, [load, refresh])

  if (!msisdn) return <p className="notice">ফোন নম্বর দিলে আপনার অর্ডার ও তালিকা দেখা যাবে।</p>
  const act = (fn) => fn().then(load).catch((e) => setError(e.message))
  return (
    <section className="market-section">
      {error && <p className="error">{error}</p>}
      <h3>আমার অর্ডার</h3>
      {orders.length === 0 && <p className="muted">কোনো অর্ডার নেই।</p>}
      <ul className="plain-list">
        {orders.map((o) => (
          <li key={o.order_id} className="card">
            <strong>#{o.order_id} {o.totals.lines[0].name} × {o.totals.lines[0].packs}</strong> — {taka(o.totals.farmer_pays)}
            <p>{o.status_bn} · {o.dealer.name} <DemoBadge on={o.dealer.is_demo} label="ডেমো দোকান" /></p>
            {['placed', 'confirmed'].includes(o.status) && (
              <button className="secondary" onClick={() => act(() => cancelOrder(msisdn, o.order_id))}>বাতিল</button>
            )}
          </li>
        ))}
      </ul>
      <h3>আমার ফসল তালিকা</h3>
      {listings.length === 0 && <p className="muted">কোনো তালিকা নেই।</p>}
      <ul className="plain-list">
        {listings.map((l) => (
          <li key={l.listing_id} className="card">
            <strong>#{l.listing_id} {CROPS.find(([k]) => k === l.crop)?.[1]} {l.qty_kg} কেজি</strong>
            {l.asking_price_per_kg ? ` — চাওয়া ৳${l.asking_price_per_kg}/কেজি` : ''} · {l.status === 'open' ? 'খোলা' : 'বিক্রি হয়েছে'}
            {l.offers.length === 0 && <p className="muted">এখনো কোনো অফার নেই।</p>}
            {l.offers.map((o) => (
              <div key={o.offer_id} className="offer-row">
                <span>
                  {o.buyer.name} <DemoBadge on={o.buyer.is_demo} label="ডেমো ক্রেতা" /> — ৳{o.price_per_kg}/কেজি × {o.qty_kg}{' '}
                  = আপনি পাবেন <strong>{taka(o.totals.farmer_receives)}</strong> ({OFFER_BN[o.status] ?? o.status})
                </span>
                {o.status === 'pending' && l.status === 'open' && (
                  <span className="offer-buttons">
                    <button onClick={() => act(() => respondOffer(msisdn, o.offer_id, true))}>গ্রহণ</button>
                    <button className="secondary" onClick={() => act(() => respondOffer(msisdn, o.offer_id, false))}>বাতিল</button>
                  </span>
                )}
              </div>
            ))}
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * The farmer's marketplace (#/market): buy the inputs the agent recommended
 * from ranked nearby dealers, sell the harvest to buyers with a cited price
 * guide, and follow orders/offers. Seeded demo dealers and buyers are
 * labelled ডেমো everywhere (CLAUDE.md rule 16).
 */
export default function MarketPage() {
  const [msisdn, setMsisdnState] = useState(() => remember('market.msisdn'))
  const [tab, setTab] = useState('buy')
  const [districts, setDistricts] = useState([{ value: 'Rajshahi', label_bn: 'রাজশাহী' }])
  const [catalog, setCatalog] = useState([])
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    fetchDistricts().then((d) => setDistricts(d.districts)).catch(() => {})
    fetchCatalog().then((d) => setCatalog(d.inputs)).catch(() => {})
  }, [])

  const setMsisdn = (value) => {
    setMsisdnState(value)
    remember('market.msisdn', value)
  }
  const done = () => {
    setRefresh((n) => n + 1)
    setTab('mine')
  }

  return (
    <main className="market-page">
      <header className="phone-page-head">
        <a href="#/" className="back-link">← {BRAND_NAME}</a>
        <h1>বাজার</h1>
      </header>
      <label className="field-label">
        আপনার ফোন নম্বর
        <input className="field mono" inputMode="tel" placeholder="01XXXXXXXXX" value={msisdn}
          onChange={(e) => setMsisdn(e.target.value.trim())} />
      </label>
      <nav className="tabs market-tabs">
        {[['buy', 'উপকরণ কিনুন'], ['sell', 'ফসল বিক্রি'], ['mine', 'আমার']].map(([key, label]) => (
          <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>
      {tab === 'buy' && <Buy msisdn={msisdn} districts={districts} catalog={catalog} onOrdered={done} />}
      {tab === 'sell' && <Sell msisdn={msisdn} districts={districts} onListed={done} />}
      {tab === 'mine' && <Mine msisdn={msisdn} refresh={refresh} />}
    </main>
  )
}
