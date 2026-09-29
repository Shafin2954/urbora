import { useEffect, useRef, useState } from 'react'
import BrandMark, { Lockup } from '../components/BrandMark.jsx'
import CropCheck from '../components/CropCheck.jsx'
import { BRAND_NAME, BRAND_NAME_BN, BRAND_TAGLINE_BN } from '../branding.js'
import './home.css'

// The public front door (brand/BRAND-CORE.md). It leads with what Urbora is: one farm advisor
// for every question across the season, not a disease checker. Order: the promise (hero), the
// eight kinds of help on a real phone, why farmers need it (story), how to reach it from any
// phone, the crop-problem check working right here (CropCheck, the deterministic KB table),
// trust, market, try-it doors, closing blessing.
//
// Photos in public/img/ are AI-generated illustrations (Higgsfield, 2026-09-30; prompts in
// brand/IMAGE_PROMPTS.md) and are labelled প্রতীকী ছবি on the page. The phone screens are
// live HTML laid over the blank screens in those photos, so they can change on click.

const ADVISOR_URL = '/?guest=1#/app'
const ILLUSTRATIVE = 'প্রতীকী ছবি'

// Example conversations for the eight kinds of help. Numbers appear only where they are the
// system's real output or a cited public figure: the pest dose is the real reply from
// backend/kb/triage.py (boro + deadheart + 2 bigha); ৳27/kg urea is the government-notified
// price (data/prices.md); the sell command is the real SMS syntax (backend/market/sms_commands.py).
const TOPICS = [
  {
    id: 'crop', icon: 'seed', label: 'কী চাষ করব',
    ask: 'রাজশাহী, ২ বিঘা দোআঁশ জমি, নলকূপ আছে। এবার রবিতে কী লাগাব?',
    reply: ['জেলার ফলনের রেকর্ড আর আবহাওয়া মিলিয়ে কোন ফসল মানাবে, সেটা সাজিয়ে দিলাম।',
      'প্রতিটার খরচ, ফলন আর লাভের হিসাব SMS-এ পাঠালাম।'],
  },
  {
    id: 'soil', icon: 'soil', label: 'মাটি ও সার',
    ask: 'বোরো ধানে ইউরিয়া কখন, কতটুকু দেব?',
    reply: ['তিন কিস্তিতে দেবেন, কোনটা কবে তা আপনার প্ল্যানে তারিখসহ বসিয়ে দিলাম।',
      'মোট পরিমাণ আপনার জমির মাপে, BRRI-র নির্দেশিকা থেকে হিসাব করা।'],
  },
  {
    id: 'pest', icon: 'bug', label: 'রোগ ও পোকা',
    ask: 'বোরো ধানের মাঝের ডগা শুকিয়ে যাচ্ছে। ২ বিঘা জমি।',
    reply: ['হতে পারে: মাজরা পোকা। আক্রমণ দেখা দিলে কীটনাশক দিন।',
      'মাত্রা: ভিরতাকো 40WG, হেক্টরে 75 গ্রাম (আপনার 2 বিঘায় মোট 20 গ্রাম)।',
      'স্প্রের আগে স্থানীয় কৃষি অফিসার (SAAO)-কে দেখান।'],
    real: true,
  },
  {
    id: 'water', icon: 'drop', label: 'সেচ',
    ask: 'আলুতে সেচ কবে কবে দেব?',
    reply: ['লাগানোর তারিখ ধরে সেচের দিনগুলো আপনার প্ল্যানে বসিয়ে দিলাম।',
      'সামনে বৃষ্টি থাকলে সেই সেচ বাদ দিতে আগেই জানাব।'],
  },
  {
    id: 'weather', icon: 'rain', label: 'আবহাওয়া',
    ask: 'কাল ইউরিয়া দেওয়ার কথা। দেব?',
    reply: ['কাল বৃষ্টির পূর্বাভাস আছে (Open-Meteo)।',
      'ইউরিয়া আজ দেবেন না, পরের শুকনো দিনে দিন। বৃষ্টিতে সার ধুয়ে যায়।'],
  },
  {
    id: 'money', icon: 'coin', label: 'খরচ ও লাভ',
    ask: 'আলু করলে খরচ কত, লাভ থাকবে?',
    reply: ['বীজ, সার, সেচ আর মজুরি ধরে খরচ; জেলার গড় ফলন আর বাজারদর ধরে আয়।',
      'খারাপ, স্বাভাবিক আর ভালো মৌসুম, তিনটা হিসাবই দিলাম। প্রতিটা সংখ্যার পাশে তথ্যসূত্র।'],
  },
  {
    id: 'buy', icon: 'cart', label: 'সার-বীজ কেনা',
    ask: 'কাছে ইউরিয়া কোথায় পাব?',
    reply: ['কাছের ৩টা দোকান পেলাম, দাম আর দূরত্ব দেখে সাজানো। ইউরিয়া সরকারি দর ৳27/কেজি।',
      'অর্ডার দিতে 1 চাপুন। দাম দোকানে নগদে।'],
    demo: true,
  },
  {
    id: 'sell', icon: 'sack', label: 'ফসল বেচা',
    ask: 'বিক্রি আলু 500 কেজি 22 টাকা',
    reply: ['আপনার 500 কেজি আলু বিক্রির তালিকায় উঠেছে।',
      'ক্রেতা দাম দিলে SMS পাবেন। পছন্দ হলে "গ্রহণ" লিখে রাজি হবেন।'],
    demo: true,
  },
]

// The real first two USSD screens (backend/channels/ussd.py main_menu, MAIN_ITEMS).
const USSD_PAGES = [
  [BRAND_NAME, '1. ফসল পরামর্শ', '2. ফসলের সমস্যা', '3. আমার প্ল্যান', '4. আবহাওয়া', '9. আরও'],
  ['5. সার-বালাইনাশক কিনুন', '6. ফসল বিক্রি', '7. শেষ উত্তর', '8. প্রশ্ন লিখুন', '0. পিছনে'],
]

const TRUTHS = [
  {
    head: 'একই জমি, কম ফলন',
    big: <><s>৫০ মণ</s> → ৩০ মণ</>,
    text: 'হাইব্রিড আসার পর ফলন বেড়েছিল। গত দশ বছরে একই জমিতে ফলন কমছে, আর সার-ওষুধের খরচ বাড়ছে।',
    cite: 'দিনাজপুরের এক কৃষকের নিজের হিসাব, আমাদের সাক্ষাৎকারে',
  },
  {
    head: 'কী হয়েছে, বোঝা যায় না',
    big: '“কী হইছে?”',
    text: 'রোগ, পোকা, না মাটির পুষ্টির অভাব? কোন ফসল মানাবে, কবে সার, কোথায় বেচলে দাম বেশি? প্রশ্ন অনেক, উত্তর দেওয়ার লোক কম।',
    cite: 'একই সাক্ষাৎকার: কৃষকের সবচেয়ে বড় সমস্যা',
  },
  {
    head: 'সবাই বলে আলাদা কথা',
    big: 'দোকান, পড়শি, অভ্যাস',
    text: 'দোকানদার এক কথা বলেন, প্রতিবেশী আরেক। বাবা যা দিতেন, অনেকে তা-ই দেন। কৃষক চেষ্টা করেন, কিন্তু ঠিক উত্তরটা মেলে না।',
    cite: 'একই সাক্ষাৎকার',
  },
  {
    head: 'বিশেষজ্ঞ অনেক দূরে',
    big: 'কৃষি অফিস দূরে',
    text: 'উপজেলা কৃষি অফিসে বিশেষজ্ঞ আছেন, কিন্তু যেতে-আসতে পুরো দিন চলে যায়। সবার পক্ষে সবসময় যাওয়া হয়ে ওঠে না।',
    cite: 'একই সাক্ষাৎকার',
  },
]

const STATS = [
  { n: '69%', text: 'কৃষক কীটনাশকের পরামর্শ নেন বিক্রেতার কাছ থেকে', src: 'Rahaman et al., 2018' },
  { n: '18.98 কোটি', text: 'মোবাইল সংযোগ, দেশের জনসংখ্যার চেয়েও বেশি', src: 'BTRC, জুন 2026; জনশুমারি 2022' },
  { n: '28%', text: 'গ্রামের মানুষ (৭ বছরের বেশি) পড়তে-লিখতে পারেন না, তাই কল আর বাটনও চলে', src: 'জনশুমারি, 2022' },
]

const Icon = {
  call: <path d="M7 4h3l1.5 4-2 1.5a11 11 0 0 0 5 5L16 12.5l4 1.5v3a2 2 0 0 1-2 2A15 15 0 0 1 5 6a2 2 0 0 1 2-2z" />,
  keys: <><circle cx="7" cy="6" r="1.6" /><circle cx="12" cy="6" r="1.6" /><circle cx="17" cy="6" r="1.6" /><circle cx="7" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="17" cy="12" r="1.6" /><circle cx="7" cy="18" r="1.6" /><circle cx="12" cy="18" r="1.6" /><circle cx="17" cy="18" r="1.6" /></>,
  sms: <path d="M4 5h16v11H9l-5 4z" />,
  leaf: <><path d="M12 21V11" /><path d="M12 14c-4 0-6-2.5-6-6 4 0 6 2.5 6 6z" /><path d="M12 11c4 0 6-2.5 6-6-4 0-6 2.5-6 6z" /></>,
  seed: <><path d="M12 20v-7" /><path d="M12 13c0-4 3-7 7-7 0 4-3 7-7 7z" /><path d="M12 15c0-3-2.5-5-6-5 0 3 2.5 5 6 5z" /><path d="M6 20h12" /></>,
  soil: <><path d="M3 9h18" /><path d="M3 14h18M3 19h18" /><path d="M12 9V4M9 6l3-2 3 2" /></>,
  bug: <><ellipse cx="12" cy="13" rx="4.5" ry="6" /><path d="M12 7V19M7.5 11H4M7.5 15H4M16.5 11H20M16.5 15H20M9.5 5l-1.5-2M14.5 5l1.5-2" /></>,
  drop: <path d="M12 3c3 4.5 6 7.6 6 11a6 6 0 0 1-12 0c0-3.4 3-6.5 6-11z" />,
  rain: <><path d="M7 15a4 4 0 1 1 1-7.9A5 5 0 0 1 17.5 9 3.5 3.5 0 0 1 17 16H7" /><path d="M9 19l-1 2M13 19l-1 2M17 19l-1 2" /></>,
  coin: <><ellipse cx="12" cy="6.5" rx="7" ry="2.5" /><path d="M5 6.5v5c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-5" /><path d="M5 11.5v5c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-5" /></>,
  cart: <><path d="M3 4h2l2 11h11l2-8H6" /><circle cx="9" cy="19" r="1.5" /><circle cx="17" cy="19" r="1.5" /></>,
  sack: <><path d="M8 4h8l-1.5 3.5c3 1.5 4.5 4.5 4.5 8A4.5 4.5 0 0 1 14.5 20h-5A4.5 4.5 0 0 1 5 15.5c0-3.5 1.5-6.5 4.5-8z" /><path d="M9.5 7.5h5" /></>,
  calendar: <><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M4 10h16M9 3v4M15 3v4" /></>,
  live: <><circle cx="12" cy="12" r="3" /><path d="M6.5 6.5a8 8 0 0 0 0 11M17.5 6.5a8 8 0 0 1 0 11" /></>,
  bank: <><path d="M3 10l9-6 9 6" /><path d="M5 10v8M9 10v8M15 10v8M19 10v8M3 20h18" /></>,
  phone: <><rect x="7" y="3" width="10" height="18" rx="2" /><path d="M11 18h2" /></>,
}
function Glyph({ name }) {
  return <svg className="glyph" viewBox="0 0 24 24" aria-hidden="true">{Icon[name]}</svg>
}

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Smartphone photo with the chat for the chosen topic laid over its blank screen.
function SmartPhone({ topic }) {
  return (
    <figure className="photo-phone phone-android">
      <img src="/img/phone-android.webp" width="1040" height="1620" loading="lazy"
        alt="কৃষকের হাতে একটা সাধারণ অ্যান্ড্রয়েড ফোন" />
      <div className="phone-screen chat-screen" aria-live="polite">
        <div className="chat-bar"><BrandMark size={22} /><b>{BRAND_NAME_BN}</b></div>
        <div className="chat-body" key={topic.id}>
          <p className="bubble bubble-me">{topic.ask}</p>
          <div className="bubble bubble-bot">
            {topic.reply.map((line) => <p key={line}>{line}</p>)}
          </div>
          {topic.demo && <p className="chat-note">দোকান ও ক্রেতা ডেমো তথ্য</p>}
        </div>
      </div>
      <figcaption>
        {topic.real ? 'এই উত্তরটা সিস্টেমের আসল উত্তর।' : 'উদাহরণ কথোপকথন।'} {ILLUSTRATIVE}।
      </figcaption>
    </figure>
  )
}

// Button-phone photo showing the real USSD main menu; tapping the screen turns the page (9 / 0).
function ButtonPhone() {
  const [page, setPage] = useState(0)
  return (
    <figure className="photo-phone phone-button">
      <img src="/img/phone-button.webp" width="860" height="1344" loading="lazy"
        alt="কৃষকের হাতে একটা বাটন ফোন" />
      <button type="button" className="phone-screen ussd-screen" onClick={() => setPage(1 - page)}
        aria-label={page ? 'আগের মেনু দেখুন' : 'মেনুর বাকি অংশ দেখুন'}>
        {USSD_PAGES[page].map((line, i) => <span key={line} className={i === 0 && !page ? 'ussd-head' : ''}>{line}</span>)}
      </button>
      <figcaption>*3700# ডায়াল করলে এই মেনু আসে। পর্দায় চাপ দিলে পরের পাতা। {ILLUSTRATIVE}।</figcaption>
    </figure>
  )
}

function Topics() {
  const [active, setActive] = useState(0)
  const [auto, setAuto] = useState(true)
  useEffect(() => {
    if (!auto || reducedMotion()) return undefined
    const t = setInterval(() => setActive((i) => (i + 1) % TOPICS.length), 5200)
    return () => clearInterval(t)
  }, [auto])
  const pick = (i) => { setAuto(false); setActive(i) }

  return (
    <section id="services" className="services" aria-labelledby="services-h">
      <div className="section-inner services-inner">
        <div className="services-copy reveal">
          <p className="eyebrow">সারা মৌসুমের পরামর্শ</p>
          <h2 id="services-h">একটা সমস্যা নয়,<br />চাষের সব প্রশ্নে পাশে</h2>
          <p className="section-lead">
            বীজ বোনার আগে থেকে ফসল বেচা পর্যন্ত, যেখানে আটকাবেন সেখানেই জিজ্ঞেস করুন।
            {' '}{BRAND_NAME_BN} আপনার জেলা, জমি আর মৌসুম মনে রাখে, তাই প্রতিবার শুরু থেকে বলতে হয় না।
          </p>
          <div className="topic-grid" role="group" aria-label="কোন বিষয়ে পরামর্শ">
            {TOPICS.map((t, i) => (
              <button key={t.id} type="button" className={`topic ${i === active ? 'on' : ''}`}
                aria-pressed={i === active} onClick={() => pick(i)}>
                <Glyph name={t.icon} /><span>{t.label}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="services-art reveal"><SmartPhone topic={TOPICS[active]} /></div>
      </div>
    </section>
  )
}

// Fade sections in as they scroll into view, and drift the hero photo a little slower than
// the page. The scroller is .home, not the window. Both are off under reduced motion.
function useMotion(rootRef) {
  useEffect(() => {
    const root = rootRef.current
    if (!root || reducedMotion()) return undefined
    root.classList.add('motion')
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target) } })
    }, { root, threshold: 0.12 })
    root.querySelectorAll('.reveal').forEach((el) => io.observe(el))
    let frame = 0
    const onScroll = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => root.style.setProperty('--scroll', `${Math.min(root.scrollTop, 1200)}px`))
    }
    root.addEventListener('scroll', onScroll, { passive: true })
    return () => { io.disconnect(); root.removeEventListener('scroll', onScroll); cancelAnimationFrame(frame) }
  }, [rootRef])
}

export default function HomePage() {
  const [menu, setMenu] = useState(false)
  const close = () => setMenu(false)
  const rootRef = useRef(null)
  useMotion(rootRef)

  return (
    <div className="home" ref={rootRef}>
      <header className="home-top">
        <a className="home-brand" href="#/" aria-label={`${BRAND_NAME_BN}, প্রথম পাতা`}><Lockup size={42} /></a>
        <nav className={`home-nav ${menu ? 'open' : ''}`} aria-label="পাতার অংশ">
          <a href="#services" onClick={close}>কী কী পারে</a>
          <a href="#how" onClick={close}>কীভাবে পাবেন</a>
          <a href="#check" onClick={close}>সমস্যা চিনুন</a>
          <a href="#/market" onClick={close}>বাজার</a>
        </nav>
        <div className="top-actions">
          <a className="btn btn-primary btn-small" href="#/phone">ফোনে চেষ্টা করুন</a>
          <button type="button" className="menu-btn" aria-expanded={menu} aria-label="মেনু" onClick={() => setMenu(!menu)}>
            <span /><span /><span />
          </button>
        </div>
      </header>

      <section className="hero">
        <picture className="hero-photo" aria-hidden="true">
          <source media="(max-width: 820px)" srcSet="/img/hero-field-1200.webp" />
          <img src="/img/hero-field.webp" alt="" width="2400" height="1357" fetchPriority="high" />
        </picture>
        <div className="hero-inner">
          <div className="hero-copy">
            <p className="kicker">বীজ থেকে বিক্রি, পুরো মৌসুম পাশে</p>
            <h1>চাষের যেকোনো প্রশ্নে<br /><span>কৃষি বিশেষজ্ঞ এখন আপনার ফোনে।</span></h1>
            <p className="lead">
              কী চাষ করবেন, কোন সার কতটুকু, রোগ না পোকা, কবে সেচ, বৃষ্টি আসছে কি না, খরচ আর লাভ কত,
              কোথায় কিনবেন, কোথায় বেচবেন। {BRAND_NAME_BN} আপনার জমির মাপে পরামর্শ দেয়, যেকোনো ফোনে, বাংলায়।
            </p>
            <div className="hero-actions">
              <a className="btn btn-primary" href="#services">কী কী পারে দেখুন</a>
              <a className="btn btn-quiet" href="#/phone">বাটন ফোনে চেষ্টা করুন</a>
            </div>
            <ul className="channels" aria-label="তিনভাবে পৌঁছানো যায়">
              <li><Glyph name="call" />কল করে বলুন</li>
              <li><Glyph name="keys" />বাটন চাপুন</li>
              <li><Glyph name="sms" />SMS পাঠান</li>
            </ul>
          </div>
        </div>
        <p className="photo-credit">{ILLUSTRATIVE}</p>
      </section>

      <Topics />

      <section id="story" className="story" aria-labelledby="story-h">
        <figure className="story-photo" aria-hidden="true">
          <picture>
            <source media="(max-width: 820px)" srcSet="/img/story-land-1200.webp" />
            <img src="/img/story-land.webp" alt="" width="2400" height="1029" loading="lazy" />
          </picture>
          <figcaption>{ILLUSTRATIVE}</figcaption>
        </figure>
        <div className="section-inner story-inner">
          <p className="eyebrow eyebrow-light">কেন দরকার</p>
          <h2 id="story-h">উর্বরতা আমাদের উপহার।<br />সেটা ধরে রাখার সময় এখন।</h2>
          <p className="section-lead">
            কৃষক চেষ্টা করছেন। জানতে চাইছেন, জিজ্ঞেস করছেন। কিন্তু ঠিক উত্তরটা সময়মতো পৌঁছাচ্ছে না।
          </p>
          <div className="truths">
            {TRUTHS.map((t) => (
              <article className="truth reveal" key={t.head}>
                <h3>{t.head}</h3>
                <p className="truth-big">{t.big}</p>
                <p>{t.text}</p>
                <cite>{t.cite}</cite>
              </article>
            ))}
          </div>
          <div className="analogy reveal">
            <div><Glyph name="bank" /><p><b>আগে ব্যাংক ছিল দূরে।</b> মোবাইল ব্যাংকিং সেটা হাতের মুঠোয় এনেছে।</p></div>
            <span className="analogy-arrow" aria-hidden="true">→</span>
            <div><Glyph name="phone" /><p><b>কৃষি বিশেষজ্ঞও দূরে।</b> {BRAND_NAME_BN} সেই পরামর্শ পৌঁছে দেয় কৃষকের ফোনে।</p></div>
          </div>
        </div>
      </section>

      <section id="how" className="how" aria-labelledby="how-h">
        <div className="section-inner how-inner">
          <div className="how-art reveal"><ButtonPhone /></div>
          <div className="how-copy">
            <p className="eyebrow">কীভাবে পাবেন</p>
            <h2 id="how-h">স্মার্টফোন লাগে না।<br />যেকোনো ফোনে, তিনভাবে।</h2>
            <ol className="steps">
              <li className="reveal">
                <span className="step-no">১</span>
                <div>
                  <h3><Glyph name="call" />ফোন করুন, বাটন চাপুন বা SMS দিন</h3>
                  <p>দিনে-রাতে যেকোনো সময়। কাউকে চেনা লাগে না, লাইনে দাঁড়াতে হয় না, পড়তে না পারলে কথা বলেই চলে।</p>
                </div>
              </li>
              <li className="reveal">
                <span className="step-no">২</span>
                <div>
                  <h3><Glyph name="leaf" />নিজের ভাষায় বলুন</h3>
                  <p>কোন ফসল, কবে লাগানো, কী দেখছেন বা কী জানতে চান। বুঝতে না পারলে দু-একটা প্রশ্ন করে নেয়, আন্দাজে কিছু বলে না।</p>
                </div>
              </li>
              <li className="reveal">
                <span className="step-no">৩</span>
                <div>
                  <h3><Glyph name="sms" />উত্তর আসে SMS-এও</h3>
                  <p>কী করবেন, কবে, আপনার জমিতে কতটুকু। SMS থেকে যায়, দোকানে দেখানো যায়, বাড়ির কেউ পড়ে দিতে পারে। পরে সময়মতো মনে করিয়েও দেয়।</p>
                </div>
              </li>
            </ol>
          </div>
        </div>
      </section>

      <section id="check" className="check-band" aria-labelledby="check-h">
        <div className="section-inner check-inner">
          <div className="check-intro">
            <p className="eyebrow">এখনই চেষ্টা করুন</p>
            <h2 id="check-h">ফসলের সমস্যা চিনুন</h2>
            <p className="section-lead">
              সাতটা সহজ প্রশ্ন, বাটন ফোনের মেনুতে যা জিজ্ঞেস করা হয় ঠিক তাই। উত্তর আসে যাচাই করা কৃষি
              তথ্য থেকে। তথ্য না থাকলে সোজা বলে দেয়, আন্দাজে কিছু বলে না।
            </p>
            <ul className="check-points">
              <li>ধান, আলু, সরিষা, মসুর</li>
              <li>ওষুধ বা সারের মাত্রা আপনার জমির মাপে, কোড দিয়ে হিসাব</li>
              <li>প্রতিটা সংখ্যার পাশে তথ্যসূত্র</li>
            </ul>
          </div>
          <CropCheck />
        </div>
      </section>

      <section className="trust" aria-labelledby="trust-h">
        <div className="section-inner trust-inner">
          <div className="reveal">
            <p className="eyebrow">কেন ভরসা করবেন</p>
            <h2 id="trust-h">সংখ্যা আন্দাজে নয়, হিসাব করে</h2>
            <p>
              AI শোনে, বোঝে আর সহজ বাংলায় বুঝিয়ে বলে। কিন্তু মাত্রা, খরচ, লাভ বা ফসলের তালিকা AI বানায় না।
              সেগুলো আসে পরীক্ষিত কোড থেকে, নির্দিষ্ট তথ্যসূত্র ধরে। আমাদের কিছু বিক্রি করার নেই, আর টাকা দিয়ে
              কেউ তালিকায় আগে আসতে পারে না।
            </p>
            <p className="trust-quote">তথ্য না থাকলে সোজা বলে দেয়: <b>“তথ্য যথেষ্ট নয়”</b>।</p>
          </div>
          <ul className="sources reveal">
            <li><b>রোগ, পোকা ও সার</b><span>BRRI, BARC ও AIS-এর গাইড</span></li>
            <li><b>আবহাওয়া</b><span>Open-Meteo, ১৬ দিনের পূর্বাভাস</span></li>
            <li><b>ফলন ও দাম</b><span>বাংলাদেশ পরিসংখ্যান ব্যুরো (BBS)</span></li>
            <li><b>আপনার ফোন নম্বর</b><span>গোপন থাকে, রেকর্ডে শুধু শেষ ৩ অঙ্ক</span></li>
          </ul>
        </div>
        <dl className="section-inner stats">
          {STATS.map((s) => (
            <div className="stat reveal" key={s.n}>
              <dt>{s.n}</dt>
              <dd>{s.text}<cite>{s.src}</cite></dd>
            </div>
          ))}
        </dl>
      </section>

      <section id="market" className="market-band" aria-labelledby="market-h">
        <div className="section-inner">
          <p className="eyebrow">বাজার</p>
          <h2 id="market-h">সার-বীজ কেনা, ফসল বেচা</h2>
          <p className="section-lead">পরামর্শ যেখানে শেষ, কেনাবেচা সেখান থেকে শুরু। একই ফোনে।</p>
          <div className="job-grid job-grid-2">
            <a className="job job-link reveal" href="#/market">
              <Glyph name="cart" />
              <h3>কাছের দোকান, ঠিক দামে</h3>
              <p>দাম, দূরত্ব আর মজুদ দেখে দোকান সাজানো। টাকা দিয়ে কেউ তালিকায় আগে আসতে পারে না।</p>
            </a>
            <a className="job job-link reveal" href="#/market">
              <Glyph name="sack" />
              <h3>ফসল তুলে SMS-এ বিক্রি</h3>
              <p>কত কেজি, কোন দামে, SMS-এ জানান। ক্রেতার দাম দেখে পছন্দ হলে রাজি হন।</p>
            </a>
          </div>
          <p className="demo-note">বাজারের দোকান, ক্রেতা আর ফসলের তালিকা ডেমো তথ্য।</p>
        </div>
      </section>

      <section className="try" aria-labelledby="try-h">
        <div className="section-inner">
          <p className="eyebrow">নিজে চালিয়ে দেখুন</p>
          <h2 id="try-h">পুরো সিস্টেম, এক জায়গায়</h2>
          <div className="try-grid">
            <a className="try-card try-main reveal" href="#/phone">
              <Glyph name="keys" />
              <b>বাটন ফোন</b>
              <span>কল, USSD মেনু আর SMS, একটা বাটন ফোনের মতো করে।</span>
              <em className="tag tag-sim">সিমুলেটর</em>
            </a>
            <a className="try-card reveal" href={ADVISOR_URL}>
              <Glyph name="leaf" />
              <b>ওয়েবে পরামর্শ</b>
              <span>লিখে বা বলে প্রশ্ন করুন, পাশে দেখুন কোন তথ্য থেকে কোন উত্তর।</span>
            </a>
            <a className="try-card reveal" href="#/market">
              <Glyph name="cart" />
              <b>বাজার</b>
              <span>সার-বীজের দোকান আর ফসল বিক্রির তালিকা।</span>
              <em className="tag tag-demo">ডেমো</em>
            </a>
            <a className="try-card reveal" href="#/monitor">
              <Glyph name="live" />
              <b>ফোনে যা চলছে</b>
              <span>কল আর SMS-এর কথোপকথন, সরাসরি।</span>
            </a>
          </div>
          <p className="partner-links">দোকানদার? <a href="#/dealer">ডিলারের পাতা</a> · ক্রেতা? <a href="#/buyer">ক্রেতার পাতা</a></p>
        </div>
      </section>

      <section className="closing" aria-labelledby="closing-h">
        <picture className="closing-photo" aria-hidden="true">
          <source media="(max-width: 820px)" srcSet="/img/closing-dawn-1200.webp" />
          <img src="/img/closing-dawn.webp" alt="" width="2400" height="1029" loading="lazy" />
        </picture>
        <div className="section-inner closing-inner reveal">
          <p className="closing-tag" id="closing-h">{BRAND_TAGLINE_BN}</p>
          <p className="closing-text">মাটি উর্বর থাকুক, ফলন ফিরুক, কৃষকের পরিশ্রমের দাম মিলুক।</p>
          <a className="btn btn-sun" href="#/phone">ফোনে চেষ্টা করুন</a>
        </div>
        <p className="photo-credit">{ILLUSTRATIVE}</p>
      </section>

      <footer className="home-foot">
        <div className="section-inner foot-inner">
          <div className="foot-brand">
            <BrandMark size={72} />
            <div>
              <p className="foot-name">{BRAND_NAME_BN}</p>
              <p className="foot-tag">{BRAND_TAGLINE_BN}</p>
            </div>
          </div>
          <div className="foot-meta">
            <p>Team Uplift · University of Dhaka · GP FutureMakers 2026</p>
            <p>প্রথম সংস্করণ তৈরি IUT 12th ICT Fest bdapps Agentic AI Hackathon-এ (জুলাই 2026)।</p>
            <p>পাতার ছবিগুলো প্রতীকী, AI দিয়ে তৈরি।</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
