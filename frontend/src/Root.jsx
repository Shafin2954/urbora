import { useEffect, useState } from 'react'
import App from './App.jsx'
import PhonePage from './pages/PhonePage.jsx'
import ChannelMonitor from './components/ChannelMonitor.jsx'
import './pages/phone.css'

// Hash routes work on any static host with no server-side fallback:
// #/phone = the button-phone emulator, #/monitor = live phone conversations.
export default function Root() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onHash = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  if (hash.startsWith('#/phone')) return <PhonePage />
  if (hash.startsWith('#/monitor')) return <main className="monitor-page"><ChannelMonitor follow={false} /></main>
  return <App />
}
