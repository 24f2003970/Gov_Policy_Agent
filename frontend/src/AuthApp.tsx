import { useEffect, useState, type FormEvent } from 'react'
import Foundation from './App'
import DocumentAdmin from './DocumentAdmin'
import { authorized, login, logout, register, restoreSession, subscribe, type User } from './auth'

const inputClass = 'mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 focus:outline-teal-700'
const buttonClass = 'rounded-lg bg-teal-900 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50'
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'Request failed. Try again.'

export default function AuthApp() {
  const [user, setUser] = useState<User | null>(null)
  const [restoring, setRestoring] = useState(true)
  const [page, setPage] = useState(location.hash.slice(1) || 'home')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => subscribe(setUser), [])
  useEffect(() => {
    let disposed = false
    restoreSession().catch((failure: unknown) => { if (!disposed) setError(messageOf(failure)) })
      .finally(() => { if (!disposed) setRestoring(false) })
    return () => { disposed = true }
  }, [])
  useEffect(() => {
    const onHash = () => { setPage(location.hash.slice(1) || 'home'); setError('') }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  async function signOut() {
    setBusy(true); setError('')
    try { await logout(); location.hash = 'login' } catch (failure) { setError(`Logout not completed: ${messageOf(failure)}`) }
    finally { setBusy(false) }
  }
  return <>
    <nav aria-label="Account navigation" className="flex flex-wrap items-center gap-5 border-b border-slate-200 bg-white px-6 py-4 text-sm">
      <a href="#home">Foundation</a>
      {user ? <><a href="#account">Account</a>{user.role === 'admin' && <a href="#admin">Admin</a>}<button disabled={busy} onClick={() => void signOut()} className="ml-auto font-semibold text-teal-900">{busy ? 'Signing out…' : 'Logout'}</button></>
        : <><a href="#login">Login</a><a href="#register">Register</a></>}
    </nav>
    {error && <p role="alert" className="mx-auto mt-4 max-w-xl rounded-lg bg-amber-50 p-4 text-amber-900">{error}</p>}
    {page === 'home' ? <Foundation /> : <main className={`mx-auto ${page === 'admin' ? 'max-w-3xl' : 'max-w-xl'} px-6 py-12`}>
      {restoring ? <p role="status">Restoring your session…</p>
        : page === 'login' || page === 'register' ? <AuthForm kind={page} onLogin={() => { location.hash = 'account' }} />
        : user ? page === 'admin' ? <AdminPage /> : <AccountPage user={user} onUpdate={setUser} />
        : <div><h1 className="text-2xl font-semibold">Sign in required</h1><p className="mt-4">This page requires an active session.</p><a className="mt-4 inline-block text-teal-800 underline" href="#login">Go to login</a></div>}
    </main>}
  </>
}

function AuthForm({ kind, onLogin }: { kind: 'login' | 'register'; onLogin: () => void }) {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => { setPassword(''); setError(''); setNotice('') }, [kind])
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try {
      if (kind === 'register') {
        await register(email, username, password); setPassword('')
        setNotice('Account created. Use the Login page to sign in.')
      } else { await login(email, password); setPassword(''); onLogin() }
    } catch (failure) { setError(messageOf(failure)) }
    finally { setBusy(false) }
  }
  return <section className="rounded-2xl border border-slate-200 bg-white p-7">
    <h1 className="text-3xl font-semibold">{kind === 'register' ? 'Create your account' : 'Welcome back'}</h1>
    <p className="mt-3 text-sm text-slate-600">{kind === 'register' ? 'Public registration creates a normal user account.' : 'Sign in with your registered email and password.'}</p>
    <form onSubmit={(event) => void submit(event)} className="mt-6 space-y-5">
      <label className="block">Email<input className={inputClass} type="email" required maxLength={254} autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      {kind === 'register' && <label className="block">Username<input className={inputClass} required minLength={3} maxLength={32} pattern="[A-Za-z0-9_]{3,32}" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /><span className="text-xs text-slate-500">3–32 letters, digits or underscores. Stored in lowercase.</span></label>}
      <label className="block">Password<input className={inputClass} type="password" required minLength={kind === 'register' ? 12 : 1} maxLength={128} autoComplete={kind === 'register' ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} /><span className="text-xs text-slate-500">{kind === 'register' && '12–128 characters; passwords are never truncated.'}</span></label>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      {notice && <p role="status" className="text-sm text-teal-800">{notice} <a href="#login" className="underline">Login</a></p>}
      <button className={buttonClass} disabled={busy}>{busy ? 'Please wait…' : kind === 'register' ? 'Register' : 'Login'}</button>
    </form>
  </section>
}

function AccountPage({ user, onUpdate }: { user: User; onUpdate: (user: User) => void }) {
  const [language, setLanguage] = useState(user.preferred_language)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let disposed = false
    authorized<User>('/auth/me').then((result) => { if (!disposed) onUpdate(result) })
      .catch((failure: unknown) => { if (!disposed) setError(messageOf(failure)) })
    return () => { disposed = true }
  }, [onUpdate])
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try { const result = await authorized<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ preferred_language: language }) }); onUpdate(result); setNotice('Profile saved.') }
    catch (failure) { setError(messageOf(failure)) } finally { setBusy(false) }
  }
  return <section className="rounded-2xl border border-slate-200 bg-white p-7"><h1 className="text-3xl font-semibold">Your account</h1>
    <dl className="mt-6 space-y-3"><div><dt className="text-sm text-slate-500">Username</dt><dd>{user.username}</dd></div><div><dt className="text-sm text-slate-500">Email</dt><dd className="break-all">{user.email}</dd></div><div><dt className="text-sm text-slate-500">Role</dt><dd>{user.role}</dd></div></dl>
    <form className="mt-6 space-y-4" onSubmit={(event) => void save(event)}><label className="block">Preferred language<select className={inputClass} value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="hi">हिन्दी</option><option value="hinglish">Hinglish</option></select></label><button className={buttonClass} disabled={busy}>{busy ? 'Saving…' : 'Save preference'}</button></form>
    {error && <p role="alert" className="mt-4 text-red-800">{error}</p>}{notice && <p role="status" className="mt-4 text-teal-800">{notice}</p>}
  </section>
}

function AdminPage() {
  const [status, setStatus] = useState('Checking server authorization…')
  useEffect(() => {
    let disposed = false
    authorized<{ authorized: boolean; role: string }>('/auth/admin/access')
      .then((result) => { if (!disposed) setStatus(result.authorized ? 'Admin access confirmed by the backend.' : 'Access denied.') })
      .catch((failure: unknown) => { if (!disposed) setStatus(messageOf(failure)) })
    return () => { disposed = true }
  }, [])
  return <section><h1 className="text-3xl font-semibold">Admin access</h1><p role="status" className="mt-5">{status}</p>{status === 'Admin access confirmed by the backend.' && <DocumentAdmin />}</section>
}
