import { useEffect, useState } from 'react'
import { Lockup } from './BrandMark.jsx'
import './site-nav.css'

// The one navigation for every inner page (web advisor, market, dealer, buyer). Links are
// real buttons with an icon and a clear "you are here" state, so a farmer who does not read
// menus well still sees where each one goes. Hash routes, so it works on any static host.
export const ADVISOR_URL = '#/app'

const ICON = {
  home: <path d="M4 11l8-7 8 7M6 10v9h12v-9M10 19v-5h4v5" />,
  chat: <path d="M4 5h16v11H9l-5 4z" />,
  leaf: <><path d="M12 21V11" /><path d="M12 14c-4 0-6-2.5-6-6 4 0 6 2.5 6 6z" /><path d="M12 11c4 0 6-2.5 6-6-4 0-6 2.5-6 6z" /></>,
  cart: <><path d="M3 4h2l2 11h11l2-8H6" /><circle cx="9" cy="19" r="1.5" /><circle cx="17" cy="19" r="1.5" /></>,
}

export function NavIcon({ name }) {
  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true">{ICON[name]}</svg>
}

const LINKS = [
  { key: 'home', href: '#/', label: 'হোম', icon: 'home' },
  { key: 'app', href: ADVISOR_URL, label: 'পরামর্শ', icon: 'chat' },
  { key: 'check', href: '#check', label: 'ফসলের সমস্যা', icon: 'leaf' },
  { key: 'market', href: '#/market', label: 'বাজার', icon: 'cart' },
]

/** `active` is the key of the current page; `children` sit at the right end (status, account). */
export default function SiteNav({ active, children, brand = true, compact = false }) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const close = () => setOpen(false)
    window.addEventListener('hashchange', close)
    return () => window.removeEventListener('hashchange', close)
  }, [])
  return (
    <header className={`site-nav${compact ? ' site-nav-compact' : ''}`}>
      {brand && <a className="site-nav-brand" href="#/" aria-label="উর্বরা, প্রথম পাতা"><Lockup size={36} /></a>}
      <nav className={`site-nav-links${open ? ' open' : ''}`} aria-label="পাতা">
        {LINKS.map((link) => (
          <a key={link.key} href={link.key === 'check' ? '#/check' : link.href}
            className={`nav-pill${active === link.key ? ' is-active' : ''}`}
            aria-current={active === link.key ? 'page' : undefined}>
            <NavIcon name={link.icon} /><span>{link.label}</span>
          </a>
        ))}
      </nav>
      <div className="site-nav-end">
        {children}
        <button type="button" className="site-nav-menu" aria-expanded={open} aria-label="মেনু" onClick={() => setOpen(!open)}>
          <span /><span /><span />
        </button>
      </div>
    </header>
  )
}
