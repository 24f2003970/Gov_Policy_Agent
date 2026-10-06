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

  return <section className="space-y-4"><h1>System status</h1><p>Connection diagnostics for this local academic prototype. Readiness does not measure answer correctness or source eligibility.</p>
    {connection.state==='loading'?<p role="status">Checking connection…</p>:connection.state==='disconnected'?<p role="alert" className="notice">{connection.message}</p>:<div className="card"><h2>Backend ready</h2><p>{connection.health.project_id} · phase {connection.health.phase} · checked {connection.checkedAt}</p><dl>{Object.entries(connection.health.required_dependencies).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl><details><summary>Technical connection details</summary><p>{healthUrl}</p><p>Request {connection.requestId}</p><pre>{JSON.stringify(connection.health.optional_services,null,2)}</pre></details></div>}
    <button onClick={()=>setAttempt(v=>v+1)}>Retry connection</button>
  </section>
}
