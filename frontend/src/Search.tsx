import { useEffect, useState, type FormEvent } from 'react'
import { authorized, type User } from './auth'
type Source = { version_id: string; title: string; eligible: boolean; reasons: string[]; applicability: string }
type Status = { state: string; active_generation: string | null; latest_job: {state: string; processed: number; total: number; error_code: string | null} | null; sources: Source[]; model: {model: string; revision: string; chunk_profile: string} }
type Passage = { extraction_method?:string; extraction_revision_id?:string; ocr_notice?:string; chunk_id: string; version_id: string; title: string; issuer: string; source_url: string; page_ordinal: number; pdf_page_number: number | null; start_offset: number; end_offset: number; text: string; cosine_similarity: number; cosine_distance: number; verification: {applicability: string; scope: string; provenance: string} }
type Results = { query_normalization?:{retrieval_question:string;transformations:string[];selection:string}; status: string; items: Passage[]; generation?: string; notice?: string; heuristic_min_similarity?: number; timings_ms?: {embedding: number; total: number} }
const input = 'mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2'
const button = 'rounded bg-teal-900 px-4 py-2 text-white disabled:opacity-50'
const message = (e: unknown) => e instanceof Error ? e.message : 'Request failed'

export default function Search({ user }: { user: User }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [results, setResults] = useState<Results | null>(null)
  const [error, setError] = useState(''), [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [inspection, setInspection] = useState<Passage | null>(null)
  const [page, setPage] = useState<{text: string; offset: number; total_characters: number} | null>(null)
  async function refresh() { setStatus(await authorized<Status>('/search/status')) }
  useEffect(() => { let disposed = false; authorized<Status>('/search/status').then(v => {if (!disposed) setStatus(v)})
    .catch(e => {if (!disposed) setError(message(e))}); return () => {disposed = true} }, [])
  async function action(task: () => Promise<unknown>) {
    setBusy(true); setError(''); setNotice('')
    try {await task(); await refresh()} catch(e) {setError(message(e))} finally {setBusy(false)}
  }
  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    const body = {question: form.get('question'), count: Number(form.get('count')),
      scheme: form.get('scheme') || null, issuer: form.get('issuer') || null, document_type: form.get('document_type') || null,
      published_after: form.get('published_after') || null, published_before: form.get('published_before') || null,
      unknown_dates: form.get('unknown_dates')}
    setResults(null); setPage(null); setInspection(null)
    await action(async () => setResults(await authorized<Results>('/search', {method:'POST',body:JSON.stringify(body),signal:AbortSignal.timeout(25000)})))
  }
  async function inspect(p: Passage, offset=0) {
    setInspection(p); setPage(null)
    await action(async () => setPage(await authorized(`/search/versions/${p.version_id}/pages/${p.page_ordinal}?offset=${offset}`)))
  }
  async function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    const body = Object.fromEntries(['decision','reuse_status','applicability','reason','evidence_url','scope'].map(k => [k,form.get(k)]))
    await action(async () => {await authorized(`/admin/documents/versions/${form.get('version')}/reviews`,{method:'POST',body:JSON.stringify(body)}); setNotice('Append-only review recorded. Rebuild explicitly for newly eligible sources.')})
  }
  return <section className="space-y-6"><h1 className="text-3xl font-semibold">Search source passages</h1>
    <p>Hindi and English questions share one multilingual index. These are candidate excerpts, not generated answers or confirmed eligibility advice. Similarity is relevance, not correctness.</p>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}{notice && <p role="status">{notice}</p>}
    <section className="rounded border bg-white p-4"><h2 className="text-xl font-semibold">Index status</h2>
      {status ? <><p>Active: {status.state} · generation {status.active_generation || 'none'}</p>
        <p className="break-all">{status.model.model} · {status.model.revision} · {status.model.chunk_profile}</p>
        <p>{status.sources.filter(s=>s.eligible).length} eligible / {status.sources.length} sources</p>
        {status.latest_job && <p>Latest job: {status.latest_job.state} · {status.latest_job.processed}/{status.latest_job.total} passages {status.latest_job.error_code}</p>}
        <ul>{status.sources.map(s=><li className="mt-2" key={s.version_id}>{s.title}: {s.eligible?'eligible':s.reasons.join(', ')} · applicability {s.applicability}</li>)}</ul></> : <p role="status">Loading index status…</p>}
      <button disabled={busy} className="mt-3 underline" onClick={()=>void action(refresh)}>Refresh index status</button>
      {user.role==='admin' && <button disabled={busy} className="ml-4 underline" onClick={()=>void action(async()=>{await authorized('/admin/index/rebuild',{method:'POST'});setNotice('Generation queued; index service must run.')})}>Queue index rebuild</button>}
    </section>
    <form onSubmit={e=>void search(e)} className="space-y-3 rounded border bg-white p-4">
      <label className="block">Question (Hindi / English)<textarea name="question" required minLength={2} maxLength={2000} rows={3} className={input}/></label>
      <p className="text-sm">Maximum 512 tokenizer tokens including prefix; oversized questions are rejected without truncation.</p>
      <label className="block">Result count<input name="count" type="number" min={1} max={10} defaultValue={5} className={input}/></label>
      {['scheme','issuer','document_type'].map(name=><label className="block" key={name}>{name==='issuer'?'Ministry / issuer filter':name==='scheme'?'Scheme filter':'Document type filter'}<input name={name} maxLength={name==='document_type'?80:200} className={input}/></label>)}
      <label className="block">Published on/after<input name="published_after" type="date" className={input}/></label>
      <label className="block">Published on/before<input name="published_before" type="date" className={input}/></label>
      <label className="block">Unknown publication dates<select name="unknown_dates" className={input}><option value="exclude">Exclude when filtering dates</option><option value="include">Include as unknown</option></select></label>
      <button disabled={busy} className={button}>{busy?'Searching…':'Search passages'}</button>
    </form>
    {results && <section className="space-y-4"><h2 className="text-xl font-semibold">Retrieval: {results.status}</h2><p>{results.notice}</p>
      {results.query_normalization&&<p className="text-sm">Retrieval query: {results.query_normalization.retrieval_question}. Changes: {results.query_normalization.transformations.join(', ')||'none'} · selection {results.query_normalization.selection}. Original-query retrieval is retained for comparison/fallback.</p>}
      {results.timings_ms && <p>Embedding {results.timings_ms.embedding} ms · total {results.timings_ms.total} ms · heuristic minimum similarity {results.heuristic_min_similarity}</p>}
      {results.status==='unavailable' && <p>No coherent index active. Prepare model, queue rebuild and run index service.</p>}
      {results.status==='empty' && <p>No eligible candidate exceeded the heuristic threshold with these filters. This does not prove an answer or policy does not exist.</p>}
      {results.items.map(p=><article key={p.chunk_id} className="rounded border bg-white p-4"><h3 className="font-semibold">{p.title}</h3>
        <p>{p.issuer} · {p.pdf_page_number?`Physical PDF page ${p.pdf_page_number}`:`TXT section ${p.page_ordinal}`} · characters [{p.start_offset}, {p.end_offset})</p>
        <a className="break-all underline" href={p.source_url} target="_blank" rel="noreferrer">Official source</a>
        <p>Provenance {p.verification.provenance} · applicability {p.verification.applicability}. {p.verification.scope}</p>
        <p>Extraction: {p.extraction_method||'digital'} · revision {p.extraction_revision_id||'original'}. {p.ocr_notice}</p><p>Cosine similarity {p.cosine_similarity.toFixed(4)} · distance {p.cosine_distance.toFixed(4)}</p>
        <p className="break-all text-xs">Version {p.version_id} · chunk {p.chunk_id} · index {results.generation}</p>
        <pre className="mt-3 whitespace-pre-wrap break-words text-sm">{p.text}</pre>
        <button disabled={busy} className="mt-3 underline" onClick={()=>void inspect(p)}>Inspect extracted source page</button></article>)}
    </section>}
    {page && inspection && <section className="rounded border bg-white p-4"><h2>Extracted source page {inspection.page_ordinal}</h2>
      <p>Characters [{page.offset}, {page.offset+page.text.length}) of {page.total_characters}. Original text order; images/graphics excluded.</p>
      <pre className="whitespace-pre-wrap break-words">{page.text}</pre>
      <button disabled={busy || page.offset===0} onClick={()=>void inspect(inspection,Math.max(0,page.offset-20000))}>Previous text</button>
      <button disabled={busy || page.offset+page.text.length>=page.total_characters} onClick={()=>void inspect(inspection,page.offset+20000)}>Next text</button>
    </section>}
    {user.role==='admin' && status && <details className="rounded border bg-white p-4"><summary>Audited eligibility review (admin)</summary>
      <p>Append a decision without changing originals/history. Evidence and scope required; partial extraction cannot be overridden.</p>
      <form onSubmit={e=>void review(e)} className="space-y-3">
        <label className="block">Source version<select name="version" className={input}>{status.sources.map(s=><option value={s.version_id} key={s.version_id}>{s.title}</option>)}</select></label>
        <label className="block">Decision<select name="decision" className={input}><option value="verified">Verified</option><option value="rejected">Rejected</option></select></label>
        <label className="block">Reuse status<select name="reuse_status" className={input}><option value="not_assessed">Not assessed</option><option value="local_reference_only">Local reference only</option><option value="permission_recorded">Permission evidence recorded</option></select></label>
        <label className="block">Applicability<select name="applicability" className={input}><option value="unknown">Unknown</option><option value="historical">Historical snapshot</option><option value="current_verified">Current verified by evidence</option></select></label>
        <label className="block">Review reason<textarea name="reason" minLength={20} maxLength={2000} required className={input}/></label>
        <label className="block">Evidence URL<input name="evidence_url" type="url" maxLength={1500} required className={input}/></label>
        <label className="block">Intended-use scope<textarea name="scope" minLength={20} maxLength={2000} required className={input}/></label>
        <button disabled={busy} className={button}>Record review</button>
      </form></details>}
  </section>
}
