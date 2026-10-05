import { useEffect, useState } from 'react'
import { fetchHealth, healthUrl, type Health } from './health'

type Connection =
  | { state: 'loading' }
  | { state: 'connected'; health: Health; checkedAt: string; requestId: string }
  | { state: 'disconnected'; message: string }

export default function App() {
  const [attempt, setAttempt] = useState(0)
  const [connection, setConnection] = useState<Connection>({ state: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    let disposed = false
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    setConnection({ state: 'loading' })
    fetchHealth(controller.signal)
      .then(({ health, requestId }) => {
        if (!disposed) setConnection({ state: 'connected', health, requestId,
          checkedAt: new Date().toLocaleTimeString() })
      })
      .catch((error: unknown) => {
        if (!disposed) setConnection({ state: 'disconnected', message: controller.signal.aborted
          ? 'Health check timed out after 5 seconds.'
          : error instanceof Error ? error.message : 'Health check failed.' })
      })
      .finally(() => window.clearTimeout(timeout))
    return () => { disposed = true; window.clearTimeout(timeout); controller.abort() }
  }, [attempt])

  const connected = connection.state === 'connected'
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-7">
        <a href="/" className="flex items-center gap-3 text-sm font-semibold tracking-tight">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-900 text-white" aria-hidden="true">GP</span>
          Policy Assistant
        </a>
        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">GOV-CS-028 · Part 5</span>
      </header>
      <main className="mx-auto max-w-6xl px-6 pb-14 pt-8 md:pt-16">
        <div className="grid gap-12 lg:grid-cols-[1.2fr_1fr] lg:gap-16">
          <section>
            <p className="eyebrow">A B.Tech project · Local-first foundation</p>
            <h1 className="mt-5 max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-slate-900 md:text-6xl">Government policies.<br /><span className="text-teal-800">Clearer understanding.</span></h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-600">Building a multilingual government policy assistant with retrieval-augmented generation, explainable citations and transparent evidence-quality scoring.</p>
            <div className="mt-7 flex flex-wrap gap-2" aria-label="Planned languages">
              {['English', 'हिन्दी', 'Hinglish'].map((language) => <span key={language} className="rounded-full bg-teal-50 px-4 py-2 text-sm text-teal-900">{language}</span>)}
            </div>
            <p className="mt-8 max-w-xl border-l-2 border-teal-700 pl-4 text-sm leading-relaxed text-slate-600">Accounts, document ingestion, multilingual passage search and local grounded historical answers are available. Full claim-support validation, OCR and trust scoring remain deferred.</p>
          </section>
          <section className="self-start rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8" aria-labelledby="connection-title">
            <p className="eyebrow">Live system check</p>
            <h2 id="connection-title" className="mt-3 text-2xl font-semibold text-slate-900">Backend connection</h2>
            <div role="status" aria-live="polite" className="mt-6">
              <div className={`flex items-center gap-3 rounded-xl px-4 py-4 ${connected ? 'bg-teal-50 text-teal-900' : connection.state === 'loading' ? 'bg-slate-100 text-slate-700' : 'bg-amber-50 text-amber-900'}`}>
                <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-teal-600' : connection.state === 'loading' ? 'animate-pulse bg-slate-400' : 'bg-amber-600'}`} />
                <strong>{connected ? 'Connected · Foundation ready' : connection.state === 'loading' ? 'Checking backend…' : 'Disconnected'}</strong>
              </div>
              {connection.state === 'connected' && <div className="mt-5 space-y-3 text-sm text-slate-600">
                <p>PostgreSQL connected and the application schema is current. Search uses a separately started local index service.</p>
                <p>Last checked: <span className="font-medium text-slate-800">{connection.checkedAt}</span></p>
                <p className="break-all text-xs">Request ID: {connection.requestId}</p>
              </div>}
              {connection.state === 'disconnected' && <div className="mt-5 space-y-3 text-sm text-slate-600"><p>{connection.message}</p><p>Check backend startup, private configuration, PostgreSQL and migrations. Confirm the API URL and allowed CORS origin, then retry.</p></div>}
              {connection.state === 'loading' && <p className="mt-5 text-sm text-slate-600">Contacting the actual backend readiness endpoint.</p>}
            </div>
            <p className="mt-6 break-all rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-500">GET {healthUrl}</p>
            <button onClick={() => setAttempt((value) => value + 1)} disabled={connection.state === 'loading'} className="mt-5 w-full rounded-xl bg-teal-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700 disabled:cursor-wait disabled:opacity-50">{connection.state === 'loading' ? 'Checking…' : 'Check connection again'}</button>
          </section>
        </div>
        <section className="mt-16 border-t border-slate-200 pt-8" aria-label="Project direction">
          <p className="eyebrow">Designed for the next phases</p>
          <div className="mt-5 grid gap-6 md:grid-cols-3">
            {[['Official evidence', 'A curated corpus of verified government documents.'], ['Traceable answers', 'Planned citations to exact pages and source passages.'], ['Honest uncertainty', 'Clarification and abstention when evidence is insufficient.']].map(([title, detail]) => <div key={title}><h2 className="font-semibold text-slate-800">{title}</h2><p className="mt-2 text-sm leading-relaxed text-slate-600">{detail}</p></div>)}
          </div>
        </section>
      </main>
      <footer className="mx-auto max-w-6xl px-6 pb-8 text-xs text-slate-500">Academic prototype · Authentication, ingestion and retrieval · Not an official government service</footer>
    </div>
  )
}
