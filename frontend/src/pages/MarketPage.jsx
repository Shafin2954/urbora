import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  cancelOrder, createListing, fetchCatalog, fetchDistricts, findInputs, myListings, myOrders,
  placeOrder, priceGuide, remember, respondOffer,
} from '../api/market.js'
import SiteNav from '../components/SiteNav.jsx'

// The farmer's marketplace (#/market): buy the inputs the advisor recommended from ranked
// nearby dealers, sell the harvest with a cited price guide, and follow orders and offers.
// Every figure comes from the market API (listings with provenance, backend/finance/market.py
// for totals); nothing is computed or invented here beyond packs × the listed pack price for
// the confirmation line. Seeded demo dealers and buyers are labelled ডেমো everywhere
// (CLAUDE.md rule 16).

const CROPS = [
  ['boro_rice', 'বোরো ধান', '🌾'], ['aman_rice', 'আমন ধান', '🌾'], ['potato', 'আলু', '🥔'],
  ['mustard', 'সরিষা', '🌼'], ['lentil', 'মসুর', '🫘'],
]
const CATEGORY_ICON = { সার: '🧪', ছত্রাকনাশক: '🍃', কীটনাশক: '🐛' }
const UNIT_BN = { kg: 'কেজি', l: 'লিটার', g: 'গ্রাম', ml: 'মিলি' }
const taka = (n) => `৳${Math.round(n).toLocaleString('en-US')}`
const OFFER_BN = { pending: 'অপেক্ষমাণ', accepted: 'গৃহীত', rejected: 'বাতিল', withdrawn: 'প্রত্যাহার' }
const distance = (km) => (km < 1 ? 'একই এলাকায়' : `${km} কিমি দূরে`)
const SCORE_PARTS = [['price', 'দাম', 40], ['distance', 'দূরত্ব', 30], ['stock', 'মজুদ', 15], ['trust', 'আস্থা', 15]]

function DemoBadge({ on, label = 'ডেমো' }) {
  return on ? <span className="badge-demo">{label}</span> : null
}

function DistrictSelect({ value, onChange, districts }) {
  return (
    <label className="mk-field">
      <span>জেলা</span>
      <select className="field" value={value} onChange={(e) => onChange(e.target.value)}>
        {districts.map((d) => <option key={d.value} value={d.value}>{d.label_bn}</option>)}
      </select>
    </label>
  )
}

function PriceGuide({ guide }) {
  if (!guide) return null
  const fg = guide.farm_gate
  const wp = guide.wholesale_pattern
  if (!fg && !wp) return <p className="mk-note">এই ফসলের কোনো উৎস-সহ দাম পাওয়া যায়নি।</p>
  return (
    <div className="mk-guide">
      <h3>দামের ধারণা</h3>
      <div className="mk-guide-rows">
        {fg && (
          <div>
            <span className="mk-guide-label">খামার-দাম</span>
            <strong>{taka(fg.price_bdt_per_kg)}<small>/কেজি</small></strong>
            <cite>{fg.date} · {fg.provenance.source_title}</cite>
          </div>
        )}
        {wp?.this_month_avg_bdt_per_kg != null && (
          <div>
            <span className="mk-guide-label">পাইকারি, এ মাসের গড়</span>
            <strong>৳{wp.this_month_avg_bdt_per_kg}<small>/কেজি</small></strong>
            <cite>অতীতের গড় ({wp.years_covered}), পূর্বাভাস নয়; পাইকারি দাম, খামার-দাম নয়</cite>
          </div>
        )}
      </div>
    </div>
  )
}

function Offer({ offer: o, msisdn, onOrder }) {
  const [packs, setPacks] = useState(1)
  const [confirming, setConfirming] = useState(false)
  const unit = UNIT_BN[o.pack_unit] ?? o.pack_unit
  return (
    <li className={`mk-offer${o.rank === 1 ? ' is-top' : ''}`}>
      <div className="mk-offer-rank" aria-label={`ক্রম ${o.rank}`}>{o.rank}</div>
      <div className="mk-offer-body">
        <div className="mk-offer-head">
          <h4>{o.dealer_name}</h4>
          <DemoBadge on={o.is_demo} label="ডেমো দোকান" />
          {!o.verified && <span className="badge-quiet">যাচাই হয়নি</span>}
        </div>
        <p className="mk-offer-sub">{o.upazila ? `${o.upazila} · ` : ''}{o.brand_name}, {o.pack_size} {unit} প্যাকেট</p>
        <ul className="mk-facts">
          <li>📍 {distance(o.km)}</li>
          <li>📦 মজুদ {o.stock_packs} প্যাকেট</li>
        </ul>
        <div className="mk-score" title={`স্কোর ${o.score}/100`}>
          {SCORE_PARTS.map(([key, label, max]) => (
            <span key={key} className="mk-score-part">
              <span className="mk-score-label">{label}</span>
              <span className="mk-bar"><span style={{ width: `${(o.components[key] / max) * 100}%` }} /></span>
            </span>
          ))}
          <span className="mk-score-total">{o.score}<small>/100</small></span>
        </div>
        <cite className="mk-source">উৎস: {o.provenance.source_title}, {o.provenance.locator}</cite>
      </div>
      <div className="mk-offer-buy">
        <p className="mk-price">{taka(o.price_bdt)}<small>প্রতি প্যাকেট</small></p>
        <p className="mk-unit-price">৳{o.unit_price}/{unit}</p>
        {confirming ? (
          <div className="mk-confirm">
            <p>{packs} প্যাকেট · <b>{taka(o.price_bdt * packs)}</b> দোকানে নগদে। নিশ্চিত?</p>
            <div>
              <button onClick={() => onOrder(o, packs).then(() => setConfirming(false))}>হ্যাঁ, অর্ডার</button>
              <button className="secondary" onClick={() => setConfirming(false)}>না</button>
            </div>
          </div>
        ) : (
          <div className="mk-order">
            <div className="mk-stepper" role="group" aria-label="প্যাকেট">
              <button type="button" className="secondary" onClick={() => setPacks(Math.max(1, packs - 1))} aria-label="কমান">−</button>
              <span>{packs}</span>
              <button type="button" className="secondary" onClick={() => setPacks(Math.min(o.stock_packs, packs + 1))} aria-label="বাড়ান">+</button>
            </div>
            <button onClick={() => setConfirming(true)} disabled={!msisdn}>অর্ডার করুন</button>
          </div>
        )}
      </div>
    </li>
  )
}

function Buy({ msisdn, districts, catalog, onOrdered }) {
  const [district, setDistrict] = useState('Rajshahi')
  const [product, setProduct] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const groups = useMemo(() => {
    const out = {}
    for (const item of catalog) (out[item.category_bn] ??= []).push(item)
    return Object.entries(out)
  }, [catalog])

  const search = useCallback(async (generic, where) => {
    setProduct(generic)
    setError('')
    setLoading(true)
    try {
      setResult(await findInputs(generic, where))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { if (product) search(product, district) }, [district]) // eslint-disable-line react-hooks/exhaustive-deps

  const order = async (offer, packs) => {
    try {
      await placeOrder(msisdn, offer.product_id, packs)
      onOrdered()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="mk-buy">
      <aside className="mk-panel mk-pick">
        <DistrictSelect value={district} onChange={setDistrict} districts={districts} />
        {groups.map(([category, items]) => (
          <div key={category} className="mk-group">
            <h3>{CATEGORY_ICON[category] ?? '•'} {category}</h3>
            <div className="mk-products">
              {items.map((item) => (
                <button key={item.generic} className={`mk-product${product === item.generic ? ' is-on' : ''}`}
                  aria-pressed={product === item.generic} onClick={() => search(item.generic, district)}>
                  {item.label_bn}
                </button>
              ))}
            </div>
          </div>
        ))}
      </aside>
      <section className="mk-results" aria-live="polite">
        {error && <p className="error">{error}</p>}
        {!result && !loading && (
          <div className="mk-empty">
            <span aria-hidden="true">🛒</span>
            <h3>কী কিনবেন বেছে নিন</h3>
            <p>বাম পাশ থেকে সার বা ওষুধ বাছলে কাছের দোকানগুলো দাম, দূরত্ব আর মজুদ মিলিয়ে সাজানো দেখাবে।</p>
          </div>
        )}
        {loading && <p className="mk-note">দোকান খোঁজা হচ্ছে…</p>}
        {result && !loading && (
          <>
            <header className="mk-results-head">
              <h2>{result.product_bn} <small>{districts.find((d) => d.value === result.district)?.label_bn ?? result.district}-এর কাছে</small></h2>
              <p>{result.offers.length}টি দোকান</p>
            </header>
            {result.offers.length === 0 && <p className="mk-note">৮০ কিমির মধ্যে কোনো দোকানে পাওয়া যায়নি।</p>}
            <ol className="mk-offers">
              {result.offers.map((o) => <Offer key={o.product_id} offer={o} msisdn={msisdn} onOrder={order} />)}
            </ol>
            {!msisdn && <p className="notice">অর্ডার করতে উপরে ফোন নম্বর দিন, অর্ডারের খবর SMS-এ আসবে।</p>}
            <p className="mk-rule">সাজানোর নিয়ম: দাম 40 + দূরত্ব 30 + মজুদ 15 + আস্থা 15। টাকা দিয়ে কেউ আগে আসতে পারে না।</p>
          </>
        )}
      </section>
    </div>
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
    <div className="mk-sell">
      <section className="mk-panel">
        <h3 className="mk-step">১. কোন ফসল বেচবেন?</h3>
        <div className="mk-crops">
          {CROPS.map(([key, bn, icon]) => (
            <button key={key} className={`mk-crop${crop === key ? ' is-on' : ''}`} aria-pressed={crop === key} onClick={() => setCrop(key)}>
              <span aria-hidden="true">{icon}</span>{bn}
            </button>
          ))}
        </div>
        <PriceGuide guide={guide} />
      </section>
      <form className="mk-panel mk-sell-form" onSubmit={submit}>
        <h3 className="mk-step">২. কত আর কোন দামে?</h3>
        <label className="mk-field"><span>কত কেজি</span>
          <input className="field" type="number" min="1" required value={qty} onChange={(e) => setQty(e.target.value)} placeholder="যেমন 500" />
        </label>
        <label className="mk-field"><span>চাওয়া দাম (৳/কেজি, ইচ্ছা হলে)</span>
          <input className="field" type="number" min="0.1" step="0.1" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="যেমন 22" />
        </label>
        <DistrictSelect value={district} onChange={setDistrict} districts={districts} />
        <button disabled={!msisdn}>বিক্রির তালিকায় দিন</button>
        {!msisdn && <p className="notice">তালিকা করতে উপরে ফোন নম্বর দিন, ক্রেতার দাম SMS-এ আসবে।</p>}
        {error && <p className="error">{error}</p>}
        <p className="mk-note">SMS থেকেও দেওয়া যায়: <span className="mono">বিক্রি আলু 500 কেজি 22 টাকা</span></p>
      </form>
    </div>
  )
}

const STATUS_TONE = { placed: 'wait', confirmed: 'go', ready: 'go', delivered: 'done', cancelled: 'off', rejected: 'off' }

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

  if (!msisdn) return <div className="mk-empty"><span aria-hidden="true">📋</span><h3>ফোন নম্বর দিন</h3><p>উপরে নম্বর দিলে আপনার অর্ডার আর বিক্রির তালিকা এখানে দেখা যাবে।</p></div>
  const act = (fn) => fn().then(load).catch((e) => setError(e.message))
  return (
    <div className="mk-mine">
      {error && <p className="error">{error}</p>}
      <section className="mk-panel">
        <h3 className="mk-step">🛒 আমার অর্ডার</h3>
        {orders.length === 0 && <p className="mk-note">কোনো অর্ডার নেই।</p>}
        <ul className="mk-list">
          {orders.map((o) => (
            <li key={o.order_id} className="mk-item">
              <div>
                <strong>{o.totals.lines[0].name} × {o.totals.lines[0].packs}</strong>
                <p>#{o.order_id} · {o.dealer.name} <DemoBadge on={o.dealer.is_demo} label="ডেমো দোকান" /></p>
              </div>
              <div className="mk-item-end">
                <b>{taka(o.totals.farmer_pays)}</b>
                <span className={`mk-status mk-status-${STATUS_TONE[o.status] ?? 'wait'}`}>{o.status_bn}</span>
                {['placed', 'confirmed'].includes(o.status) && (
                  <button className="secondary" onClick={() => act(() => cancelOrder(msisdn, o.order_id))}>বাতিল</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="mk-panel">
        <h3 className="mk-step">🌾 আমার বিক্রির তালিকা</h3>
        {listings.length === 0 && <p className="mk-note">কোনো তালিকা নেই।</p>}
        <ul className="mk-list">
          {listings.map((l) => (
            <li key={l.listing_id} className="mk-item mk-item-col">
              <div className="mk-item-row">
                <strong>{CROPS.find(([k]) => k === l.crop)?.[1]} {l.qty_kg} কেজি</strong>
                <span className={`mk-status mk-status-${l.status === 'open' ? 'go' : 'done'}`}>{l.status === 'open' ? 'খোলা' : 'বিক্রি হয়েছে'}</span>
              </div>
              <p>#{l.listing_id}{l.asking_price_per_kg ? ` · চাওয়া ৳${l.asking_price_per_kg}/কেজি` : ''}</p>
              {l.offers.length === 0 && <p className="mk-note">এখনো কোনো ক্রেতার দাম আসেনি।</p>}
              {l.offers.map((o) => (
                <div key={o.offer_id} className="mk-bid">
                  <span>
                    {o.buyer.name} <DemoBadge on={o.buyer.is_demo} label="ডেমো ক্রেতা" /> · ৳{o.price_per_kg}/কেজি × {o.qty_kg}
                    <br />আপনি পাবেন <strong>{taka(o.totals.farmer_receives)}</strong> <small>({OFFER_BN[o.status] ?? o.status})</small>
                  </span>
                  {o.status === 'pending' && l.status === 'open' && (
                    <span className="mk-bid-actions">
                      <button onClick={() => act(() => respondOffer(msisdn, o.offer_id, true))}>গ্রহণ</button>
                      <button className="secondary" onClick={() => act(() => respondOffer(msisdn, o.offer_id, false))}>না</button>
                    </span>
                  )}
                </div>
              ))}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

const TABS = [['buy', '🛒', 'উপকরণ কিনুন'], ['sell', '🌾', 'ফসল বিক্রি'], ['mine', '📋', 'আমার অর্ডার ও তালিকা']]

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
    <div className="page-shell">
      <SiteNav active="market" />
      <header className="mk-hero">
        <div className="mk-hero-inner">
          <div>
            <p className="mk-eyebrow">বাজার</p>
            <h1>সার-বীজ কেনা, ফসল বেচা</h1>
            <p className="mk-lead">কাছের দোকানের দাম মিলিয়ে কিনুন, ফসলের দাম জেনে বেচুন। অর্ডার আর ক্রেতার দামের খবর আসে SMS-এ।</p>
            <p className="mk-demo-note">এখনকার দোকান ও ক্রেতারা ডেমো তথ্য, পরীক্ষার জন্য।</p>
          </div>
          <label className="mk-phone">
            <span>আপনার ফোন নম্বর</span>
            <input className="field mono" inputMode="tel" placeholder="01XXXXXXXXX" value={msisdn}
              onChange={(e) => setMsisdn(e.target.value.trim())} />
            <small>অর্ডার আর দামের SMS এই নম্বরে যাবে।</small>
          </label>
        </div>
      </header>
      <main className="market-page">
        <nav className="mk-tabs" role="tablist">
          {TABS.map(([key, icon, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} className={`mk-tab${tab === key ? ' is-on' : ''}`} onClick={() => setTab(key)}>
              <span aria-hidden="true">{icon}</span>{label}
            </button>
          ))}
        </nav>
        {tab === 'buy' && <Buy msisdn={msisdn} districts={districts} catalog={catalog} onOrdered={done} />}
        {tab === 'sell' && <Sell msisdn={msisdn} districts={districts} onListed={done} />}
        {tab === 'mine' && <Mine msisdn={msisdn} refresh={refresh} />}
      </main>
    </div>
  )
}
