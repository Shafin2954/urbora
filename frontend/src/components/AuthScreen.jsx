import { useState } from 'react'
import BrandMark from './BrandMark.jsx'
import { BRAND_NAME_BN, BRAND_TAGLINE_BN } from '../branding.js'

// Sign in / sign up for the web advisor. An account keeps the farmer's chats and land
// details across devices; "continue as guest" keeps them in this browser only.
export default function AuthScreen({ auth, onGuest }) {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    const { error } = mode === 'signin' ? await auth.signIn(email, password) : await auth.signUp(email, password)
    setBusy(false)
    setNotice(error?.message ?? (mode === 'signin' ? '' : 'অ্যাকাউন্ট খোলা হয়েছে। ইমেইলে নিশ্চিতকরণ চাইলে সেটা দেখুন।'))
  }
  return (
    <main className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <BrandMark size={64} />
        <h1>{BRAND_NAME_BN}</h1>
        <p className="auth-tag">{BRAND_TAGLINE_BN}</p>
        <p className="auth-lead">{mode === 'signin'
          ? 'লগইন করলে আপনার আলাপ আর জমির তথ্য মনে থাকে, যেকোনো ফোন বা কম্পিউটারে।'
          : 'একটা ইমেইল আর পাসওয়ার্ড দিলেই অ্যাকাউন্ট খুলে যাবে।'}</p>
        <label>ইমেইল<input className="field" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>পাসওয়ার্ড<input className="field" type="password" autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} minLength="6" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        {notice && <p className="error" role="alert">{notice}</p>}
        <button disabled={busy}>{mode === 'signin' ? 'লগইন' : 'অ্যাকাউন্ট খুলুন'}</button>
        <button type="button" className="text-button" onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}>
          {mode === 'signin' ? 'নতুন? অ্যাকাউন্ট খুলুন' : 'আগেই অ্যাকাউন্ট আছে? লগইন'}
        </button>
        {onGuest && <>
          <div className="auth-or"><span>অথবা</span></div>
          <button type="button" className="secondary" onClick={onGuest}>অতিথি হিসেবে শুরু করুন</button>
        </>}
      </form>
    </main>
  )
}
