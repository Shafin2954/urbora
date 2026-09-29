import { useState } from 'react'
import BrandMark, { Lockup } from '../components/BrandMark.jsx'
import CropCheck from '../components/CropCheck.jsx'
import { BRAND_NAME_BN, BRAND_TAGLINE_BN } from '../branding.js'
import './home.css'

// The public front door (brand/BRAND-CORE.md). It tells the story in the order a farmer lives it:
// the soil is our gift, the same land gives less, nobody can say why, the expert is far away,
// and then the fix: the crop-problem check works right here on the page (CropCheck, the
// deterministic KB table), then every channel and the market. Every statistic carries its
// source; the SMS on the phone is the system's real reply for the example case
// (backend/kb/triage.py, boro + deadheart + 2 bigha), shortened only by leaving lines out.

const ADVISOR_URL = '/?guest=1#/app'

const SMS_EXAMPLE = [
  'বোরো ধান (কুশি), কাণ্ড/খোল: ডগা শুকানো।',
  'হতে পারে: মাজরা পোকা।',
  'আক্রমণ দেখা দিলে কীটনাশক দিন।',
  'মাত্রা: ভিরতাকো 40WG, হেক্টরে 75 গ্রাম (আপনার 2 বিঘায় মোট 20 গ্রাম)।',
  'স্প্রের আগে স্থানীয় কৃষি অফিসার (SAAO)-কে দেখান।',
]

const TRUTHS = [
  {
    head: 'একই জমি, কম ফলন',
    big: <><s>৫০ মণ</s> → ৩০ মণ</>,
    text: 'হাইব্রিড আসার পর ফলন বেড়েছিল। গত দশ বছরে একই জমিতে ফলন কমছে, আর সার-ওষুধের খরচ বাড়ছে।',
    cite: 'দিনাজপুরের এক কৃষকের নিজের হিসাব, আমাদের সাক্ষাৎকারে',
  },
  {
    head: 'কী রোগ, বোঝা যায় না',
    big: '“কী হইছে?”',
    text: 'রোগ, পোকা, না মাটির পুষ্টির অভাব? লক্ষণ দোকানে বুঝিয়ে বলাও কঠিন। তাই কোন সার বা ওষুধ দরকার, জানা যায় না।',
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
  calendar: <><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M4 10h16M9 3v4M15 3v4" /></>,
  chart: <><path d="M4 20V4" /><path d="M4 20h16" /><path d="M8 16v-4M12 16V8M16 16v-6" /></>,
  cart: <><path d="M3 4h2l2 11h11l2-8H6" /><circle cx="9" cy="19" r="1.5" /><circle cx="17" cy="19" r="1.5" /></>,
  live: <><circle cx="12" cy="12" r="3" /><path d="M6.5 6.5a8 8 0 0 0 0 11M17.5 6.5a8 8 0 0 1 0 11" /></>,
  rain: <><path d="M7 15a4 4 0 1 1 1-7.9A5 5 0 0 1 17.5 9 3.5 3.5 0 0 1 17 16H7" /><path d="M9 19l-1 2M13 19l-1 2M17 19l-1 2" /></>,
  bank: <><path d="M3 10l9-6 9 6" /><path d="M5 10v8M9 10v8M15 10v8M19 10v8M3 20h18" /></>,
  phone: <><rect x="7" y="3" width="10" height="18" rx="2" /><path d="M11 18h2" /></>,
}
function Glyph({ name }) {
  return <svg className="glyph" viewBox="0 0 24 24" aria-hidden="true">{Icon[name]}</svg>
}

function PhoneMock() {
  return (
    <figure className="bphone" aria-label="বাটন ফোনে আসা উত্তর">
      <div className="bphone-body">
        <div className="bphone-ear" />
        <div className="bphone-screen">
          <div className="bphone-status"><span>{BRAND_NAME_BN}</span><span>SMS</span></div>
          {SMS_EXAMPLE.map((line) => <p key={line}>{line}</p>)}
        </div>
        <div className="bphone-keys" aria-hidden="true">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((k) => <span key={k}>{k}</span>)}
        </div>
      </div>
      <figcaption>মাহমুদ ভাইয়ের ২ বিঘা বোরো, মাঝের ডগা শুকনো। সিস্টেমের আসল উত্তর (উদাহরণ চরিত্র)।</figcaption>
    </figure>
  )
}

export default function HomePage() {
  const [menu, setMenu] = useState(false)
  const close = () => setMenu(false)

  return (
    <div className="home">
      <header className="home-top">
        <a className="home-brand" href="#/" aria-label={`${BRAND_NAME_BN}, প্রথম পাতা`}><Lockup size={42} /></a>
        <nav className={`home-nav ${menu ? 'open' : ''}`} aria-label="পাতার অংশ">
          <a href="#story" onClick={close}>আমাদের কথা</a>
          <a href="#check" onClick={close}>সমস্যা চিনুন</a>
          <a href="#how" onClick={close}>কীভাবে কাজ করে</a>
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
        <div className="hero-inner">
          <div className="hero-copy">
            <p className="kicker">এ দেশের মাটি উর্বর। এটাই আমাদের উপহার।</p>
            <h1>ফসলের কী হয়েছে?<br /><span>জানুন ঘরে বসেই।</span></h1>
            <p className="lead">
              একই জমিতে ফলন কমছে। কারণ রোগ, পোকা, না মাটির পুষ্টির অভাব? {BRAND_NAME_BN} বিশেষজ্ঞের মতো
              ধাপে ধাপে জিজ্ঞেস করে সমস্যাটা চেনে, তারপর আপনার জমির মাপে সমাধান দেয়। যেকোনো ফোনে, বাংলায়।
            </p>
            <div className="hero-actions">
              <a className="btn btn-primary" href="#check">ফসলের সমস্যা চিনুন</a>
              <a className="btn btn-quiet" href="#/phone">বাটন ফোনে দেখুন</a>
            </div>
            <ul className="channels" aria-label="তিনভাবে পৌঁছানো যায়">
              <li><Glyph name="call" />কল করে বলুন</li>
              <li><Glyph name="keys" />বাটন চাপুন</li>
              <li><Glyph name="sms" />SMS পাঠান</li>
            </ul>
          </div>
          <div className="hero-art"><PhoneMock /></div>
        </div>
      </section>

      <section id="story" className="story" aria-labelledby="story-h">
        <div className="section-inner">
          <p className="eyebrow eyebrow-light">আমাদের কথা</p>
          <h2 id="story-h">উর্বরতা আমাদের উপহার।<br />সেটা ধরে রাখার সময় এখন।</h2>
          <p className="section-lead">
            কৃষক চেষ্টা করছেন। জানতে চাইছেন, জিজ্ঞেস করছেন। কিন্তু ঠিক উত্তরটা পৌঁছাচ্ছে না।
          </p>
          <div className="truths">
            {TRUTHS.map((t) => (
              <article className="truth" key={t.head}>
                <h3>{t.head}</h3>
                <p className="truth-big">{t.big}</p>
                <p>{t.text}</p>
                <cite>{t.cite}</cite>
              </article>
            ))}
          </div>
          <div className="analogy">
            <div><Glyph name="bank" /><p><b>আগে ব্যাংক ছিল দূরে।</b> মোবাইল ব্যাংকিং সেটা হাতের মুঠোয় এনেছে।</p></div>
            <span className="analogy-arrow" aria-hidden="true">→</span>
            <div><Glyph name="phone" /><p><b>কৃষি বিশেষজ্ঞও দূরে।</b> {BRAND_NAME_BN} সেই পরামর্শ পৌঁছে দেয় কৃষকের ফোনে।</p></div>
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

      <section id="how" className="how" aria-labelledby="how-h">
        <div className="section-inner">
          <p className="eyebrow">কীভাবে কাজ করে</p>
          <h2 id="how-h">যেকোনো ফোনে, তিনভাবে</h2>
          <ol className="steps">
            <li>
              <Glyph name="call" />
              <h3>ফোন করুন বা SMS দিন</h3>
              <p>স্মার্টফোন হোক বা বাটন ফোন, দিনে-রাতে যেকোনো সময়। কাউকে চেনা লাগে না, লাইনে দাঁড়াতে হয় না।</p>
            </li>
            <li>
              <Glyph name="leaf" />
              <h3>সমস্যাটা নিজের ভাষায় বলুন</h3>
              <p>কোন ফসল, কত দিন আগে লাগানো, গাছের কোথায় কী দেখছেন। বুঝতে না পারলে দু-একটা প্রশ্ন করে নেয়।</p>
            </li>
            <li>
              <Glyph name="sms" />
              <h3>উত্তর পান, SMS-এও</h3>
              <p>কী হয়েছে, কী দিতে হবে, আপনার জমিতে কতটুকু। SMS থেকে যায়, দোকানে দেখানো যায়, বাড়ির কেউ পড়ে দিতে পারে।</p>
            </li>
          </ol>
          <div className="job-grid">
            <article className="job">
              <Glyph name="rain" />
              <h3>বৃষ্টির আগে কী করবেন</h3>
              <p>সার দেওয়ার দিনে বৃষ্টির পূর্বাভাস থাকলে আগেই SMS: “ইউরিয়া আজ দেবেন না, পরের শুকনো দিনে দিন।”</p>
            </article>
            <article className="job">
              <Glyph name="calendar" />
              <h3>এই সপ্তাহে কী কাজ</h3>
              <p>লাগানোর তারিখ থেকে কোন কাজ কবে: সার, সেচ, আগাছা, কোন পোকার সময়।</p>
            </article>
            <article className="job">
              <Glyph name="chart" />
              <h3>কী চাষ করব, লাভ কত</h3>
              <p>জমি আর এলাকার আবহাওয়া মিলিয়ে কোন ফসল মানাবে, খরচ, ফলন আর লাভের হিসাব, তথ্যসূত্রসহ।</p>
            </article>
          </div>
        </div>
      </section>

      <section className="trust" aria-labelledby="trust-h">
        <div className="section-inner trust-inner">
          <div>
            <p className="eyebrow">কেন ভরসা করবেন</p>
            <h2 id="trust-h">সংখ্যা আন্দাজে নয়, হিসাব করে</h2>
            <p>
              AI শোনে, বোঝে আর সহজ বাংলায় বুঝিয়ে বলে। কিন্তু মাত্রা, খরচ, লাভ বা ফসলের তালিকা AI বানায় না।
              সেগুলো আসে পরীক্ষিত কোড থেকে, নির্দিষ্ট তথ্যসূত্র ধরে। আমাদের কিছু বিক্রি করার নেই, আর টাকা দিয়ে
              কেউ তালিকায় আগে আসতে পারে না।
            </p>
            <p className="trust-quote">তথ্য না থাকলে সোজা বলে দেয়: <b>“তথ্য যথেষ্ট নয়”</b>।</p>
          </div>
          <ul className="sources">
            <li><b>রোগ, পোকা ও সার</b><span>BRRI, BARC ও AIS-এর গাইড</span></li>
            <li><b>আবহাওয়া</b><span>Open-Meteo, ১৬ দিনের পূর্বাভাস</span></li>
            <li><b>ফলন ও দাম</b><span>বাংলাদেশ পরিসংখ্যান ব্যুরো (BBS)</span></li>
            <li><b>আপনার ফোন নম্বর</b><span>গোপন থাকে, রেকর্ডে শুধু শেষ ৩ অঙ্ক</span></li>
          </ul>
        </div>
        <dl className="section-inner stats">
          {STATS.map((s) => (
            <div className="stat" key={s.n}>
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
          <div className="job-grid job-grid-2">
            <a className="job job-link" href="#/market">
              <Glyph name="cart" />
              <h3>কাছের দোকান, ঠিক দামে</h3>
              <p>দাম, দূরত্ব আর মজুদ দেখে দোকান সাজানো। টাকা দিয়ে কেউ তালিকায় আগে আসতে পারে না।</p>
            </a>
            <a className="job job-link" href="#/market">
              <Glyph name="sms" />
              <h3>ফসল তুলে SMS-এ বিক্রি</h3>
              <p>কত মণ, কোন দামে, SMS-এ জানান। ক্রেতার দাম দেখে পছন্দ হলে রাজি হন।</p>
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
            <a className="try-card try-main" href="#/phone">
              <Glyph name="keys" />
              <b>বাটন ফোন</b>
              <span>কল, USSD মেনু আর SMS, একটা বাটন ফোনের মতো করে।</span>
              <em className="tag tag-sim">সিমুলেটর</em>
            </a>
            <a className="try-card" href={ADVISOR_URL}>
              <Glyph name="leaf" />
              <b>ওয়েবে পরামর্শ</b>
              <span>লিখে বা বলে প্রশ্ন করুন, পাশে দেখুন কোন তথ্য থেকে কোন উত্তর।</span>
            </a>
            <a className="try-card" href="#/market">
              <Glyph name="cart" />
              <b>বাজার</b>
              <span>সার-বীজের দোকান আর ফসল বিক্রির তালিকা।</span>
              <em className="tag tag-demo">ডেমো</em>
            </a>
            <a className="try-card" href="#/monitor">
              <Glyph name="live" />
              <b>ফোনে যা চলছে</b>
              <span>কল আর SMS-এর কথোপকথন, সরাসরি।</span>
            </a>
          </div>
          <p className="partner-links">দোকানদার? <a href="#/dealer">ডিলারের পাতা</a> · ক্রেতা? <a href="#/buyer">ক্রেতার পাতা</a></p>
        </div>
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
          </div>
        </div>
      </footer>
    </div>
  )
}
