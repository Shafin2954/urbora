import { useEffect, useState } from 'react'
import App from './App.jsx'
import HomePage from './pages/HomePage.jsx'
import ChannelMonitor from './components/ChannelMonitor.jsx'
import MarketPage from './pages/MarketPage.jsx'
import { BuyerPage, DealerPage } from './pages/PartnerPages.jsx'
import SiteNav from './components/SiteNav.jsx'
import './pages/monitor.css'
import './pages/market.css'

// Hash routes work on any static host with no server-side fallback:
// #/app = the web advisor (chat, previous chats, provenance graph), #/check = the home page
// scrolled to the crop-problem check, #/market = farmer marketplace, #/dealer and #/buyer =
// partner pages, #/monitor = live phone conversations (SMS / USSD / voice, for judges).
// Anything else, including in-page anchors like #how, is the home page.
export default function Root() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onHash = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  if (hash.startsWith('#/market')) return <MarketPage />
  if (hash.startsWith('#/dealer')) return <DealerPage />
  if (hash.startsWith('#/buyer')) return <BuyerPage />
  if (hash.startsWith('#/monitor')) return <div className="page-shell"><SiteNav /><main className="monitor-page"><ChannelMonitor follow={false} /></main></div>
  if (hash.startsWith('#/app')) return <App />
  return <HomePage scrollTo={hash.startsWith('#/check') ? 'check' : null} />
}
