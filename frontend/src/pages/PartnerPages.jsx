import { useCallback, useEffect, useState } from 'react'
import {
  buyerHome, dealerHome, fetchCatalog, fetchDistricts, makeOffer, registerBuyer, registerDealer,
  remember, saveProduct, setOrderStatus,
} from '../api/market.js'
import SiteNav from '../components/SiteNav.jsx'

const NEXT = { placed: ['confirmed', 'cancelled'], confirmed: ['ready', 'cancelled'], ready: ['collected', 'delivered'] }
const STATUS_BN = { confirmed: 'নিশ্চিত', cancelled: 'বাতিল', ready: 'প্রস্তুত', collected: 'সংগ্রহ হয়েছে', delivered: 'পৌঁছে দেওয়া' }
const CROP_BN = { boro_rice: 'বোরো ধান', aman_rice: 'আমন ধান', potato: 'আলু', mustard: 'সরিষা', lentil: 'মসুর' }
const taka = (n) => `৳${Math.round(n).toLocaleString('en-US')}`
const OFFER_BN = { pending: 'অপেক্ষমাণ', accepted: 'গৃহীত', rejected: 'বাতিল', withdrawn: 'প্রত্যাহার' }

function useDistricts() {
  const [list, setList] = useState([{ value: 'Rajshahi', label_bn: 'রাজশাহী' }])
  useEffect(() => {
    fetchDistricts().then((d) => setList(d.districts)).catch(() => {})
  }, [])
  return list
}

/** Register, or paste the token received at registration. */
function Join({ kind, onToken }) {
  const districts = useDistricts()
  const [form, setForm] = useState({ name: '', district: 'Rajshahi', msisdn: '', upazila: '', kind: 'wholesaler' })
  const [paste, setPaste] = useState('')
  const [issued, setIssued] = useState('')
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    try {
      const body = kind === 'dealer'
        ? { name: form.name, district: form.district, msisdn: form.msisdn, upazila: form.upazila || null }
        : { name: form.name, district: form.district, msisdn: form.msisdn, kind: form.kind }
      const res = await (kind === 'dealer' ? registerDealer(body) : registerBuyer(body))
      setIssued(res.token)
    } catch (err) {
      setError(err.message)
    }
  }

  if (issued) {
    return (
      <section className="market-section">
        <p className="notice">নিবন্ধন হয়েছে। এই কোডটি লিখে রাখুন — এটাই আপনার পাসওয়ার্ড:</p>
        <p className="mono token">{issued}</p>
        <button onClick={() => onToken(issued)}>চালিয়ে যান</button>
      </section>
    )
  }
  return (
    <section className="market-section">
      <form className="sell-form" onSubmit={submit}>
        <h2>{kind === 'dealer' ? 'দোকান নিবন্ধন' : 'ক্রেতা নিবন্ধন'}</h2>
        <label className="field-label">নাম<input className="field" required value={form.name} onChange={set('name')} /></label>
        <label className="field-label">জেলা
          <select className="field" value={form.district} onChange={set('district')}>
            {districts.map((d) => <option key={d.value} value={d.value}>{d.label_bn}</option>)}
          </select>
        </label>
        {kind === 'dealer' ? (
          <label className="field-label">উপজেলা<input className="field" value={form.upazila} onChange={set('upazila')} /></label>
        ) : (
          <label className="field-label">ধরন
            <select className="field" value={form.kind} onChange={set('kind')}>
              <option value="wholesaler">পাইকার</option><option value="stockist">মজুতদার</option>
              <option value="processor">প্রক্রিয়াজাতকারী</option><option value="retailer">খুচরা বিক্রেতা</option>
            </select>
          </label>
        )}
        <label className="field-label">ফোন (অর্ডার/অফারের SMS আসবে)
          <input className="field mono" required inputMode="tel" value={form.msisdn} onChange={set('msisdn')} />
        </label>
        <button>নিবন্ধন করুন</button>
        <p className="muted small">নতুন অ্যাকাউন্ট "যাচাই হয়নি" দেখাবে যতক্ষণ না আমরা যাচাই করি।</p>
      </form>
      <form className="phone-type" onSubmit={(e) => { e.preventDefault(); onToken(paste.trim()) }}>
        <input className="field mono" placeholder="আগের কোড দিয়ে ঢুকুন" value={paste} onChange={(e) => setPaste(e.target.value)} />
        <button>ঢুকুন</button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  )
}

function Shell({ title, storeKey, kind, children }) {
  const [token, setToken] = useState(() => remember(storeKey))
  const use = (t) => { setToken(t); remember(storeKey, t) }
  return (
    <div className="page-shell">
      <SiteNav>
        {token && <button className="secondary" onClick={() => use('')}>বের হন</button>}
      </SiteNav>
      <header className="mk-hero">
        <div className="mk-hero-inner">
          <div>
            <p className="mk-eyebrow">{kind === 'dealer' ? 'দোকানদারদের জন্য' : 'ক্রেতাদের জন্য'}</p>
            <h1>{title}</h1>
          </div>
        </div>
      </header>
      <main className="market-page partner-page">
        {token ? children(token, () => use('')) : <Join kind={kind} onToken={use} />}
      </main>
    </div>
  )
}

function DealerHome({ token, onBadToken }) {
  const [data, setData] = useState(null)
  const [catalog, setCatalog] = useState([])
  const [draft, setDraft] = useState({ generic: 'urea', brand_name: '', pack_size: 50, pack_unit: 'kg', price_bdt: '', stock_packs: '' })
  const [error, setError] = useState('')
  const load = useCallback(() => dealerHome(token).then(setData).catch((e) => {
    if (e.message.includes('token')) onBadToken(); else setError(e.message)
  }), [token, onBadToken])
  useEffect(() => { load(); fetchCatalog().then((d) => setCatalog(d.inputs)).catch(() => {}) }, [load])

  const save = async (product) => {
    setError('')
    try {
      await saveProduct(token, {
        ...product, pack_size: Number(product.pack_size), price_bdt: Number(product.price_bdt),
        stock_packs: Number(product.stock_packs),
      })
      load()
    } catch (err) {
      setError(err.message)
    }
  }
  const move = (id, status) => setOrderStatus(token, id, status).then(load).catch((e) => setError(e.message))
  if (!data) return <p className="muted">লোড হচ্ছে…</p>
  const d = data.dealer
  return (
    <section className="market-section">
      <p><strong>{d.name}</strong>, {d.upazila || d.district} · {d.verified ? 'যাচাইকৃত' : 'যাচাই হয়নি'} · সম্পন্ন অর্ডার {d.completed_orders}
        {d.is_demo ? <span className="badge-demo">ডেমো</span> : null}</p>
      {error && <p className="error">{error}</p>}
      <h3>অর্ডার</h3>
      {data.orders.length === 0 && <p className="muted">কোনো অর্ডার নেই।</p>}
      <ul className="plain-list">
        {data.orders.map((o) => (
          <li key={o.order_id} className="card">
            <strong>#{o.order_id} {o.totals.lines[0].name} × {o.totals.lines[0].packs}</strong> — {taka(o.totals.farmer_pays)}
            {' '}(আপনি পাবেন {taka(o.totals.dealer_payout)}, কমিশন {taka(o.totals.commission)})
            <p>{o.status_bn} · {o.payment === 'cod' ? 'নগদে' : 'মোবাইল ব্যালেন্স'}</p>
            <span className="offer-buttons">
              {(NEXT[o.status] || []).map((s) => (
                <button key={s} className={s === 'cancelled' ? 'secondary' : ''} onClick={() => move(o.order_id, s)}>{STATUS_BN[s]}</button>
              ))}
            </span>
          </li>
        ))}
      </ul>
      <h3>পণ্য ও দাম</h3>
      <div className="table-scroll">
      <table className="market-table">
        <thead><tr><th>পণ্য</th><th>প্যাকেট</th><th>দাম ৳</th><th>মজুদ</th><th /></tr></thead>
        <tbody>
          {data.products.map((p) => <ProductRow key={p.product_id} product={p} onSave={save} />)}
        </tbody>
      </table>
      </div>
      <form className="sell-form" onSubmit={(e) => { e.preventDefault(); save(draft) }}>
        <h3>নতুন পণ্য</h3>
        <label className="field-label">উপাদান
          <select className="field" value={draft.generic} onChange={(e) => setDraft({ ...draft, generic: e.target.value })}>
            {catalog.map((c) => <option key={c.generic} value={c.generic}>{c.label_bn} ({c.category_bn})</option>)}
          </select>
        </label>
        <label className="field-label">ব্র্যান্ড/নাম<input className="field" required value={draft.brand_name} onChange={(e) => setDraft({ ...draft, brand_name: e.target.value })} /></label>
        <label className="field-label">প্যাকেটের আকার<input className="field" type="number" step="0.01" min="0.01" required value={draft.pack_size} onChange={(e) => setDraft({ ...draft, pack_size: e.target.value })} /></label>
        <label className="field-label">একক
          <select className="field" value={draft.pack_unit} onChange={(e) => setDraft({ ...draft, pack_unit: e.target.value })}>
            <option value="kg">কেজি</option><option value="l">লিটার</option>
          </select>
        </label>
        <label className="field-label">প্যাকেটের দাম ৳<input className="field" type="number" min="1" required value={draft.price_bdt} onChange={(e) => setDraft({ ...draft, price_bdt: e.target.value })} /></label>
        <label className="field-label">মজুদ (প্যাকেট)<input className="field" type="number" min="0" required value={draft.stock_packs} onChange={(e) => setDraft({ ...draft, stock_packs: e.target.value })} /></label>
        <button>যোগ করুন</button>
      </form>
    </section>
  )
}

function ProductRow({ product, onSave }) {
  const [p, setP] = useState(product)
  const dirty = p.price_bdt !== product.price_bdt || p.stock_packs !== product.stock_packs
  return (
    <tr>
      <td>{p.brand_name} {p.is_demo ? <span className="badge-demo">ডেমো</span> : null}</td>
      <td>{p.pack_size} {p.pack_unit}</td>
      <td><input className="field field-narrow" type="number" value={p.price_bdt} onChange={(e) => setP({ ...p, price_bdt: Number(e.target.value) })} /></td>
      <td><input className="field field-narrow" type="number" value={p.stock_packs} onChange={(e) => setP({ ...p, stock_packs: Number(e.target.value) })} /></td>
      <td>{dirty && <button onClick={() => onSave(p)}>সংরক্ষণ</button>}</td>
    </tr>
  )
}

function BuyerHome({ token, onBadToken }) {
  const [data, setData] = useState(null)
  const [bids, setBids] = useState({})
  const [error, setError] = useState('')
  const load = useCallback(() => buyerHome(token).then(setData).catch((e) => {
    if (e.message.includes('token')) onBadToken(); else setError(e.message)
  }), [token, onBadToken])
  useEffect(() => { load() }, [load])

  const offer = async (listing) => {
    setError('')
    try {
      await makeOffer(token, { listing_id: listing.listing_id, price_per_kg: Number(bids[listing.listing_id]) })
      load()
    } catch (err) {
      setError(err.message)
    }
  }
  if (!data) return <p className="muted">লোড হচ্ছে…</p>
  const b = data.buyer
  return (
    <section className="market-section">
      <p><strong>{b.name}</strong>, {b.district} · {b.verified ? 'যাচাইকৃত' : 'যাচাই হয়নি'}{b.is_demo ? <span className="badge-demo">ডেমো</span> : null}</p>
      {error && <p className="error">{error}</p>}
      <h3>কাছের ফসল (১৫০ কিমির মধ্যে)</h3>
      {data.listings.length === 0 && <p className="muted">এখন কোনো খোলা তালিকা নেই।</p>}
      <ul className="plain-list">
        {data.listings.map((l) => (
          <li key={l.listing_id} className="card">
            <strong>#{l.listing_id} {CROP_BN[l.crop]} {l.qty_kg} কেজি</strong>, {l.district}
            {l.km != null && ` (${l.km} কিমি)`}{l.asking_price_per_kg ? ` — চাওয়া ৳${l.asking_price_per_kg}/কেজি` : ''}
            {l.is_demo ? <span className="badge-demo">ডেমো</span> : null}
            {l.price_guide.farm_gate && (
              <p className="muted small">খামার-দাম ৳{l.price_guide.farm_gate.price_bdt_per_kg}/কেজি ({l.price_guide.farm_gate.date})</p>
            )}
            <div className="offer-actions">
              <input className="field field-narrow" type="number" step="0.1" min="0.1" placeholder="৳/কেজি"
                value={bids[l.listing_id] ?? ''} onChange={(e) => setBids({ ...bids, [l.listing_id]: e.target.value })} />
              <button disabled={!bids[l.listing_id]} onClick={() => offer(l)}>অফার দিন</button>
              {bids[l.listing_id] && (
                <span className="muted">
                  কৃষক পাবেন {taka(l.qty_kg * bids[l.listing_id])}; প্ল্যাটফর্ম ফি আপনার দিক থেকে যোগ হবে
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
      <h3>আমার অফার</h3>
      <ul className="plain-list">
        {data.offers.map((o) => (
          <li key={o.offer_id} className="card">
            #{o.offer_id} তালিকা #{o.listing_id}: ৳{o.price_per_kg}/কেজি × {o.qty_kg} — আপনি দেবেন{' '}
            <strong>{taka(o.totals.buyer_pays)}</strong> (ফি {taka(o.totals.platform_fee)}) · {OFFER_BN[o.status] ?? o.status}
          </li>
        ))}
      </ul>
    </section>
  )
}

export function DealerPage() {
  return (
    <Shell title="দোকানের পাতা: দাম, মজুদ আর অর্ডার" storeKey="market.dealerToken" kind="dealer">
      {(token, out) => <DealerHome token={token} onBadToken={out} />}
    </Shell>
  )
}

export function BuyerPage() {
  return (
    <Shell title="ক্রেতার পাতা: কাছের ফসল আর দাম" storeKey="market.buyerToken" kind="buyer">
      {(token, out) => <BuyerHome token={token} onBadToken={out} />}
    </Shell>
  )
}
