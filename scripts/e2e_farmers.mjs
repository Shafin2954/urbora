// End-to-end simulation of the web advisor with three farmers: `npm run e2e`.
//
// Drives the real site in a browser (Playwright/Chromium), so it exercises everything a
// farmer touches: sign-in, the welcome page, sending messages one by one, the streamed
// reply, the provenance graph, and the previous-chats list (each chat is reopened from the
// sidebar at the end to prove history comes back). Each reply is screenshotted and the
// text is written to e2e-report/REPORT.md.
//
// Needs the app running (`npm run dev`) with a working OPENAI_API_KEY on the backend.
// Environment:
//   BASE_URL        default http://localhost:5000
//   E2E_EMAIL, E2E_PASSWORD   sign in to this account (needs Supabase configured);
//                   without them the run uses guest mode
//   E2E_TIMEOUT_S   max seconds to wait for one reply (default 150)
//   E2E_HEADED=1    watch it run
//   E2E_OUT         report folder (default e2e-report/)
//   E2E_NO_WEBFONTS=1  skip Google Fonts (for machines that cannot reach them)
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const out = process.env.E2E_OUT || join(root, 'e2e-report')
const BASE = process.env.BASE_URL || 'http://localhost:5000'
const TIMEOUT = Number(process.env.E2E_TIMEOUT_S || 150) * 1000

// Three farmers, three different kinds of problem. Messages go one at a time; each waits
// for the full reply. Later messages are written so they still make sense if the advisor
// asked a question in between.
const FARMERS = [
  {
    key: 'rahim',
    who: 'রহিম, রাজশাহী: কী চাষ করবেন',
    messages: [
      'আসসালামু আলাইকুম। আমি রাজশাহীর পবা থেকে বলছি। আমার ২ বিঘা দোআঁশ জমি, নলকূপের পানি আছে। এবার রবি মৌসুমে কী চাষ করলে ভালো হবে?',
      'বাজেট ৩০ হাজার টাকার মতো। নভেম্বরের মাঝামাঝি লাগাতে চাই।',
      'আলু করলে খরচ আর লাভ কত হতে পারে?',
    ],
  },
  {
    key: 'karim',
    who: 'করিম, বগুড়া: ধানে পোকা',
    messages: [
      'আমার বোরো ধানের মাঝের ডগা শুকিয়ে যাচ্ছে, গাছ এখন কুশি অবস্থায়। জমি ২ বিঘা, বগুড়ায়। কী হয়েছে, কী করব?',
      'কোন ওষুধ কতটুকু দেব? আমার জমি ২ বিঘা।',
      'স্প্রে করার আগে সামনের কয়েক দিন বগুড়ায় বৃষ্টি হবে কি?',
    ],
  },
  {
    key: 'salma',
    who: 'সালমা, দিনাজপুর: সার, কেনা আর বেচা',
    messages: [
      'দিনাজপুরে আমার ১ বিঘা বেলে দোআঁশ জমিতে আলু লাগিয়েছি ১৫ নভেম্বর, সেচ নলকূপে। কোন সার কবে দেব?',
      'কাছে কোথায় ইউরিয়া পাব, দাম কত?',
      'আলু তুলে বিক্রি করতে চাই। এখন দাম কেমন পাওয়া যায়?',
    ],
  },
]

async function waitForReply(page, before) {
  // A reply is done when a new assistant bubble (or an error) exists and nothing streams.
  await page.waitForFunction((n) => {
    const done = !document.querySelector('.caret')
    const count = document.querySelectorAll('.msg-assistant').length
    return done && (count > n || document.querySelector('.chat .error'))
  }, before, { timeout: TIMEOUT })
  await page.waitForTimeout(600)
}

async function send(page, text) {
  const before = await page.locator('.msg-assistant').count()
  await page.fill('.composer-input', text)
  await page.click('.composer-send')
  const started = Date.now()
  await waitForReply(page, before)
  const seconds = ((Date.now() - started) / 1000).toFixed(1)
  // Read what is on screen now; an element that is absent reads as '' (no auto-wait).
  const read = async (sel, last = false) => {
    const loc = page.locator(sel)
    if (!(await loc.count())) return ''
    return (last ? loc.last() : loc.first()).innerText({ timeout: 2000 }).catch(() => '')
  }
  const reply = await read('.msg-assistant', true)
  const error = await read('.chat .error')
  const widget = await read('.input-request')
  const tools = await read('.tab-trace')
  return { reply: reply.trim(), error: error.trim(), widget: widget.trim(), tools: tools.trim(), seconds }
}

async function signIn(page) {
  const email = process.env.E2E_EMAIL
  const password = process.env.E2E_PASSWORD
  await page.goto(`${BASE}/#/app`)
  await page.waitForLoadState('networkidle')
  if (!email) {
    const guest = page.locator('text=অতিথি হিসেবে শুরু করুন')
    if (await guest.count()) await guest.click()
    return 'guest'
  }
  await page.fill('input[type=email]', email)
  await page.fill('input[type=password]', password)
  await page.click('.auth-card button:not(.text-button):not(.secondary)')
  await page.waitForSelector('.sidebar-new', { timeout: 20000 })
  return email.replace(/(.).+(@.+)/, '$1***$2')
}

const main = async () => {
  mkdirSync(out, { recursive: true })
  const browser = await chromium.launch({ headless: !process.env.E2E_HEADED })
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
  if (process.env.E2E_NO_WEBFONTS) await page.route(/fonts\.(googleapis|gstatic)\.com/, (route) => route.abort())
  const who = await signIn(page)
  const lines = [
    '# End-to-end run: three farmers on the web advisor',
    '',
    `- When: ${new Date().toISOString()}`,
    `- Site: ${BASE}`,
    `- Signed in as: ${who}`,
    '',
  ]
  let failures = 0
  const titles = []

  for (const farmer of FARMERS) {
    await page.click('.sidebar-new')
    await page.waitForTimeout(800)
    lines.push(`## ${farmer.who}`, '')
    for (const [i, text] of farmer.messages.entries()) {
      const r = await send(page, text)
      const shot = `${farmer.key}-${i + 1}.png`
      await page.screenshot({ path: join(out, shot) })
      if (r.error || !r.reply) failures += 1
      lines.push(`### ${i + 1}. কৃষক`, '', `> ${text}`, '', `**উর্বরা** (${r.seconds} s${r.tools ? `, ${r.tools}` : ''}):`, '')
      lines.push(r.reply ? r.reply.split('\n').map((l) => `> ${l}`).join('\n') : '> (no reply text)', '')
      if (r.widget) lines.push(`Question widget shown: ${r.widget.replace(/\n+/g, ' / ')}`, '')
      if (r.error) lines.push(`**Error shown:** ${r.error.replace(/\n+/g, ' / ')}`, '')
      lines.push(`![${farmer.key} ${i + 1}](${shot})`, '')
    }
    titles.push(await page.locator('.chat-row.is-active strong').innerText({ timeout: 2000 }).catch(() => ''))
  }

  // Previous chats: reload, then open each farmer's chat from the sidebar.
  lines.push('## Previous chats (history)', '')
  await page.reload()
  await page.waitForSelector('.sidebar-new')
  const rows = await page.locator('.sidebar-recent .chat-row .chat-select').allInnerTexts()
  lines.push(`Sidebar after reload lists ${rows.length} chat(s):`, '', ...rows.map((r) => `- ${r.replace(/\n+/g, ' · ')}`), '')
  for (const [i, farmer] of FARMERS.entries()) {
    const row = page.locator('.sidebar-recent .chat-row .chat-select').nth(FARMERS.length - 1 - i)
    await row.click()
    await page.waitForTimeout(1500)
    const count = await page.locator('.msg').count()
    const shot = `${farmer.key}-history.png`
    await page.screenshot({ path: join(out, shot) })
    lines.push(`- ${farmer.who}: reopened with ${count} message bubbles (title: "${titles[i]}")`, '', `![${farmer.key} history](${shot})`, '')
    if (count < farmer.messages.length * 2) failures += 1
  }

  lines.push('## Result', '', failures ? `${failures} problem(s) found; see above.` : 'All replies arrived and every chat reopened from history.', '')
  writeFileSync(join(out, 'REPORT.md'), lines.join('\n'))
  await browser.close()
  console.log(`Report: ${join(out, 'REPORT.md')} (${failures} problem(s))`)
  process.exit(failures ? 1 : 0)
}

main().catch((err) => { console.error(err); process.exit(2) })
