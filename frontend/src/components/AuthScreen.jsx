import { useState } from 'react'
import { BRAND_NAME } from '../branding.js'

export default function AuthScreen({ auth }) {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [notice, setNotice] = useState('')
  const submit = async (event) => {
    event.preventDefault()
    const { error } = mode === 'signin' ? await auth.signIn(email, password) : await auth.signUp(email, password)
    setNotice(error?.message ?? (mode === 'signin' ? '' : 'Account created. Check email confirmation if enabled.'))
  }
  return <main className="auth-screen"><form className="auth-card" onSubmit={submit}>
    <img src="/icon.svg" alt="" width="42" height="42" /><h1>{BRAND_NAME}</h1><p>আপনার ফসলের পরামর্শ, এক জায়গায়।</p>
    <label>ইমেইল<input className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    <label>পাসওয়ার্ড<input className="field" type="password" minLength="6" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
    {notice && <p className="error">{notice}</p>}<button>{mode === 'signin' ? 'সাইন ইন' : 'অ্যাকাউন্ট খুলুন'}</button>
    <button type="button" className="text-button" onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}>{mode === 'signin' ? 'নতুন? অ্যাকাউন্ট খুলুন' : 'আগেই অ্যাকাউন্ট আছে? সাইন ইন'}</button>
  </form></main>
}
