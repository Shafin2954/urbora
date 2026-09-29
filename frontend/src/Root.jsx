import { useEffect, useState } from 'react'
import App from './App.jsx'
import HomePage from './pages/HomePage.jsx'
import PhonePage from './pages/PhonePage.jsx'
import ChannelMonitor from './components/ChannelMonitor.jsx'
import MarketPage from './pages/MarketPage.jsx'
import { BuyerPage, DealerPage } from './pages/PartnerPages.jsx'
import './pages/phone.css'
import './pages/market.css'

// Hash routes work on any static host with no server-side fallback:
// #/app = the web advisor (chat + provenance graph), #/phone = the
// button-phone emulator, #/monitor = live phone conversations, #/market =
// farmer marketplace, #/dealer and #/buyer = partner pages. Anything else,
// including in-page anchors like #how, is the home page.
export default function Root() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onHash = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  if (hash.startsWith('#/phone')) return <PhonePage />
  if (hash.startsWith('#/market')) return <MarketPage />
  if (hash.startsWith('#/dealer')) return <DealerPage />
  if (hash.startsWith('#/buyer')) return <BuyerPage />
  if (hash.startsWith('#/monitor')) return <main className="monitor-page"><ChannelMonitor follow={false} /></main>
  if (hash.startsWith('#/app')) return <App />
  return <HomePage />
}
