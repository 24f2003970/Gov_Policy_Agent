import { useEffect, useRef, useState, type FormEvent } from 'react'
import { authorized } from './auth'

type Evidence = {id: string; quote: string; quote_start_offset: number; quote_end_offset: number}
type Result = {status: string; language: string; answer: string; claims: {text: string; evidence: Evidence[]}[]; limitations: string[]; trust_score: null; grounding: string}
type Source = {chunk_id: string; version_id: string; title: string; issuer: string; source_url: string; pdf_page_number: number | null; start_offset: number; end_offset: number; text: string; verification: {applicability: string; scope: string}}
type Run = {id: string; question: string; language: string; state: string; status: string | null; error_code: string | null; created_at: string; result?: Result | null; sources?: Source[]; current_source_warnings?: {warning: string}[]; model?: {tag: string; digest: string}; timings?: {worker_total_ms: number}}
const input='mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2'
const button='rounded bg-teal-900 px-4 py-2 text-white disabled:opacity-50'
const failure=(e:unknown)=>e instanceof Error?e.message:'Request failed'

export default function Ask() {
  const [run,setRun]=useState<Run|null>(null),[history,setHistory]=useState<Run[]>([])
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[worker,setWorker]=useState<boolean|null>(null)
  const [historyPage,setHistoryPage]=useState(1)
  const live=useRef(true),active=useRef<string|null>(null)
  async function refresh(page=historyPage) {
    const [h,s]=await Promise.all([authorized<{items:Run[]}>(`/ask/history?page=${page}`),authorized<{worker_available:boolean}>('/ask/status')])
    if(live.current){setHistory(h.items);setWorker(s.worker_available)}
  }
  useEffect(()=>{live.current=true;void refresh().catch(e=>setError(failure(e)));return()=>{live.current=false;
    if(active.current)void authorized(`/ask/history/${active.current}/cancel`,{method:'POST'}).catch(()=>{})}},[])
  useEffect(()=>{
    if(!run || !['queued','processing'].includes(run.state)){active.current=null;return}
    active.current=run.id
    let polling=false
    const timer=setInterval(()=>{
      if(polling)return
      polling=true
      void authorized<Run>(`/ask/history/${run.id}`).then(v=>{if(live.current){setRun(v);if(!['queued','processing'].includes(v.state))void refresh().catch(e=>setError(failure(e)))}})
        .catch(e=>{if(live.current)setError(failure(e))})
        .finally(()=>{polling=false})
    },1000)
    return()=>clearInterval(timer)
  },[run?.id,run?.state])
  const pending=busy || !!run && ['queued','processing'].includes(run.state)
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();setBusy(true);setError('');const f=new FormData(event.currentTarget)
    const body={question:f.get('question'),language:f.get('language'),scheme:f.get('scheme')||null,issuer:f.get('issuer')||null,
      document_type:f.get('document_type')||null,published_after:f.get('published_after')||null,published_before:f.get('published_before')||null,unknown_dates:f.get('unknown_dates')}
    try{setRun(await authorized<Run>('/ask',{method:'POST',body:JSON.stringify(body)}));await refresh()}
    catch(e){setError(failure(e))}finally{setBusy(false)}
  }
  async function select(id:string){setError('');try{setRun(await authorized<Run>(`/ask/history/${id}`))}catch(e){setError(failure(e))}}
  async function cancel(){if(!run)return;setError('');try{setRun(await authorized<Run>(`/ask/history/${run.id}/cancel`,{method:'POST'}))}catch(e){setError(failure(e))}}
  async function changePage(page:number){setHistoryPage(page);try{await refresh(page)}catch(e){setError(failure(e))}}
  return <section className="space-y-6"><h1 className="text-3xl font-semibold">Ask from reviewed sources</h1>
    <p>Local generation uses eligible exact passages. Ask explicitly about a dated historical document; this corpus does not establish current entitlement or application advice. Final claims appear after validation. Trust score is unavailable.</p>
    <p>Answer worker: {worker===null?'checking…':worker?'available':'unavailable'} · one pending request globally</p>
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}
    <form onSubmit={e=>void submit(e)} className="space-y-3 rounded border bg-white p-4">
      <label className="block">Question<textarea className={input} name="question" minLength={2} maxLength={2000} required rows={3}/></label>
      <label className="block">Response language<select className={input} name="language"><option value="en">English</option><option value="hi">Hindi</option></select></label>
      {['scheme','issuer','document_type'].map(k=><label className="block" key={k}>{k==='scheme'?'Scheme filter':k==='issuer'?'Ministry / issuer filter':'Document type filter'}<input name={k} className={input} maxLength={k==='document_type'?80:200}/></label>)}
      <label className="block">Published on/after<input type="date" name="published_after" className={input}/></label>
      <label className="block">Published on/before<input type="date" name="published_before" className={input}/></label>
      <label className="block">Unknown publication dates<select name="unknown_dates" className={input}><option value="exclude">Exclude when filtering dates</option><option value="include">Include as unknown</option></select></label>
      <button className={button} disabled={pending}>{pending?'Working…':'Ask sources'}</button>
    </form>
    {run&&<section className="space-y-3 rounded border bg-white p-4"><h2 className="text-xl font-semibold">Request: {run.state}</h2><p>{run.question}</p>
      {['queued','processing'].includes(run.state)&&<><p role="status">Retrieving and checking local evidence. No unchecked claims are shown.</p><button className="underline" onClick={()=>void cancel()}>Cancel request</button></>}
      {run.state==='error'&&<p role="alert">Service or grounding error: {run.error_code}. No policy answer published.</p>}
      {run.state==='cancelled'&&<p>Request cancelled; no answer published.</p>}
      {run.result&&<><h3 className="font-semibold">{run.result.status}</h3><p className="whitespace-pre-wrap">{run.result.answer}</p>
        <ul className="list-disc pl-5">{run.result.limitations.map((t,i)=><li key={i}>{t}</li>)}</ul><p className="text-sm">{run.result.grounding}</p>
        {(run.current_source_warnings||[]).map((w,i)=><p className="rounded bg-amber-50 p-3" key={i}>{w.warning}</p>)}
        {run.result.claims.map((c,i)=><article className="border-t pt-3" key={i}><h4 className="font-semibold">Claim {i+1}</h4><p>{c.text}</p>
          {c.evidence.map((e,j)=>{const s=run.sources?.find(p=>p.chunk_id===e.id);return <div className="mt-2" key={j}>
            {s&&<><p>{s.title} · {s.issuer} · physical page {s.pdf_page_number} · {s.verification.applicability}</p><a className="break-all underline" href={s.source_url} target="_blank" rel="noreferrer">Official source</a>
              <p className="break-all text-xs">Version {s.version_id} · passage {s.chunk_id} · quote characters [{e.quote_start_offset}, {e.quote_end_offset})</p></>}
            <blockquote className="whitespace-pre-wrap border-l-2 border-teal-700 pl-3">{e.quote}</blockquote></div>})}</article>)}
        <p className="break-all text-xs">{run.model?.tag} · digest {run.model?.digest} · total {run.timings?.worker_total_ms} ms</p></>}
    </section>}
    <section className="rounded border bg-white p-4"><h2 className="text-xl font-semibold">Your query history</h2><p className="text-sm">Private to your account. Thirty-day retention; snapshots are not proof of ongoing source eligibility.</p>
      {!history.length&&<p>No records on this page.</p>}<ul>{history.map(r=><li key={r.id} className="mt-3"><button disabled={pending} className="text-left underline" onClick={()=>void select(r.id)}>{r.question}</button><p className="text-xs">{r.created_at} · {r.state} · {r.status || r.error_code}</p></li>)}</ul>
      <div className="mt-3 flex gap-4"><button disabled={pending || historyPage===1} onClick={()=>void changePage(historyPage-1)}>Previous history</button><span>Page {historyPage}</span><button disabled={pending || history.length<20} onClick={()=>void changePage(historyPage+1)}>Next history</button><button className="underline" onClick={()=>void refresh().catch(e=>setError(failure(e)))}>Refresh history</button></div>
    </section>
  </section>
}
