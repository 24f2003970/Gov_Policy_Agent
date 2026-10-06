import { useEffect, useRef, useState, type FormEvent } from 'react'
import { authorized, type User } from './auth'
import EvidenceQuality, { type Assessment } from './EvidenceQuality'

type Evidence = {id: string; quote: string; quote_start_offset: number; quote_end_offset: number}
type Support = {outcome:string; method:string|null; reason:string; judge_called?:boolean; independent_verification:boolean}
type Citation = {citation_id:string; claim_id:string; claim_position:number; marker:number; claim_text:string|null; quote:string|null; start_offset:number; end_offset:number;
  metadata:{extraction_method?:string;extraction_revision_id?:string;ocr_notice?:string;title:string; issuer:string; source_url:string; version_id:string; version_number?:number; pdf_page_number:number|null; page_ordinal:number; publication_date:string|null; effective_date:string|null; section_label:string|null; section_is_heuristic:boolean; clause:null; review:{applicability:string}};
  provenance:{status:string; method:string; reason:string}; support:Support; current_access:{allowed:boolean; reasons:string[]; applicability?:string}}
type Result = {status: string; language: string; answer: string; claims: {claim_id?:string; text: string; evidence: Evidence[]; support?:Support; citation_markers?:number[]}[]; limitations: string[]; trust_score: null; grounding: string}
type Source = {chunk_id: string; version_id: string; title: string; issuer: string; source_url: string; pdf_page_number: number | null; start_offset: number; end_offset: number; text: string|null; verification: {applicability: string; scope: string}}
type Run = {evidence_quality?:Assessment;retrieval_question?:string;query_normalization?:{transformations:string[];selection?:string};id: string; question: string; language: string; state: string; status: string | null; error_code: string | null; created_at: string; result?: Result | null; sources?: Source[]; citations?:Citation[]; claim_checks?:{position:number;retained:boolean;assessment:Support}[]; source_access_withheld?:boolean; current_support_method?:string; current_source_warnings?: {warning: string}[]; model?: {tag: string; digest: string}; timings?: {worker_total_ms: number;verification?:{total_ms:number}}}
const input='mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2'
const button='rounded bg-teal-900 px-4 py-2 text-white disabled:opacity-50'
const failure=(e:unknown)=>e instanceof Error?e.message:'Request failed'

export default function Ask({user}:{user:User}) {
  const [run,setRun]=useState<Run|null>(null),[history,setHistory]=useState<Run[]>([])
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[worker,setWorker]=useState<boolean|null>(null)
  const [historyPage,setHistoryPage]=useState(1)
  const [citation,setCitation]=useState<Citation|null>(null),[inspection,setInspection]=useState<{text:string;offset:number;pdf_page_number:number|null;total_characters:number}|null>(null)
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
    event.preventDefault();setBusy(true);setError('');setCitation(null);setInspection(null);const f=new FormData(event.currentTarget)
    const body={question:f.get('question'),language:f.get('language'),scheme:f.get('scheme')||null,issuer:f.get('issuer')||null,
      document_type:f.get('document_type')||null,published_after:f.get('published_after')||null,published_before:f.get('published_before')||null,unknown_dates:f.get('unknown_dates')}
    try{setRun(await authorized<Run>('/ask',{method:'POST',body:JSON.stringify(body)}));await refresh()}
    catch(e){setError(failure(e))}finally{setBusy(false)}
  }
  async function select(id:string){setError('');setCitation(null);setInspection(null);try{setRun(await authorized<Run>(`/ask/history/${id}`))}catch(e){setError(failure(e))}}
  async function inspect(){if(!run||!citation)return;setError('');setInspection(null);try{setInspection(await authorized(`/ask/history/${run.id}/citations/${citation.citation_id}/text`))}catch(e){
    setError(failure(e));setCitation(null)
    try{setRun(await authorized<Run>(`/ask/history/${run.id}`))}catch{setRun(null)}
  }}
  function openCitation(c:Citation){setCitation(c);setInspection(null)}
  async function cancel(){if(!run)return;setError('');try{setRun(await authorized<Run>(`/ask/history/${run.id}/cancel`,{method:'POST'}))}catch(e){setError(failure(e))}}
  async function changePage(page:number){setHistoryPage(page);try{await refresh(page)}catch(e){setError(failure(e))}}
  return <section className="space-y-6"><h1 className="text-3xl font-semibold">Ask from reviewed sources</h1>
    <p>Local generation uses eligible exact passages. Ask explicitly about a dated historical document; this corpus does not establish current entitlement or application advice. Final claims appear after validation. Evidence quality describes available support; overall trust score is unavailable.</p>
    <p>Answer worker: {worker===null?'checking…':worker?'available':'unavailable'} · one pending request globally</p>
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}
    <form onSubmit={e=>void submit(e)} className="space-y-3 rounded border bg-white p-4">
      <label className="block">Question<textarea className={input} name="question" minLength={2} maxLength={2000} required rows={3}/></label>
      <label className="block">Response language<select className={input} name="language" defaultValue={user.preferred_language==='en'?'en':'hi'}><option value="en">English</option><option value="hi">Hindi</option></select></label>
      {['scheme','issuer','document_type'].map(k=><label className="block" key={k}>{k==='scheme'?'Scheme filter':k==='issuer'?'Ministry / issuer filter':'Document type filter'}<input name={k} className={input} maxLength={k==='document_type'?80:200}/></label>)}
      <label className="block">Published on/after<input type="date" name="published_after" className={input}/></label>
      <label className="block">Published on/before<input type="date" name="published_before" className={input}/></label>
      <label className="block">Unknown publication dates<select name="unknown_dates" className={input}><option value="exclude">Exclude when filtering dates</option><option value="include">Include as unknown</option></select></label>
      <button className={button} disabled={pending}>{pending?'Working…':'Ask sources'}</button>
    </form>
    {run&&<section className="space-y-3 rounded border bg-white p-4"><h2 className="text-xl font-semibold">Request: {run.state}</h2><p>{run.question}</p>{run.query_normalization&&<p className="text-sm">Retrieval query: {run.retrieval_question}. Changes: {run.query_normalization.transformations.join(', ')||'none'}. Input detection never changes your selected response language.</p>}
      {['queued','processing'].includes(run.state)&&<><p role="status">Retrieving and checking local evidence. No unchecked claims are shown.</p><button className="underline" onClick={()=>void cancel()}>Cancel request</button></>}
      {run.state==='error'&&<p role="alert">Service or grounding error: {run.error_code}. No policy answer published.</p>}
      {run.state==='cancelled'&&<p>Request cancelled; no answer published.</p>}
      {run.result&&<><h3 className="font-semibold">{run.result.status}</h3><p className="whitespace-pre-wrap">{run.result.answer}</p>
        <ul className="list-disc pl-5">{run.result.limitations.map((t,i)=><li key={i}>{t}</li>)}</ul><p className="text-sm">{run.result.grounding}</p>
        {(run.current_source_warnings||[]).map((w,i)=><p className="rounded bg-amber-50 p-3" key={i}>{w.warning}</p>)}
        {run.result.claims.map((c,i)=><article className="border-t pt-3" key={c.claim_id||i}><h4 className="font-semibold">Claim {i+1}</h4><p>{c.text}</p>
          <p>Support: {c.support?.outcome||'not_evaluated'} · automated check, no truth guarantee</p>
          {(run.citations||[]).filter(v=>v.claim_id===c.claim_id).map(v=><button className="mr-3 underline" key={v.citation_id} aria-label={`Citation ${v.marker}`} onClick={()=>openCitation(v)}>[{v.marker}] Source evidence</button>)}</article>)}
        {(run.claim_checks||[]).filter(c=>!c.retained).map(c=><p className="rounded bg-amber-50 p-3" key={c.position}>Candidate {c.position} omitted: {c.assessment.outcome}. {c.assessment.reason}</p>)}
        {run.source_access_withheld&&(run.citations||[]).map(c=><button className="mr-3 underline" key={c.citation_id} onClick={()=>openCitation(c)}>Citation [{c.marker}] metadata; text withheld</button>)}
        {citation&&<aside aria-label="Citation panel" className="space-y-3 rounded border p-3"><h3 className="font-semibold">Citation [{citation.marker}]</h3><p>{citation.claim_text||'Claim text withheld under current source-access policy.'}</p>
          <p>Provenance: {citation.provenance.status} · {citation.provenance.method}</p><p>{citation.provenance.reason}</p>
          <p>Support: {citation.support.outcome} · {citation.support.method||'No Part 6 assessment'}</p><p>{citation.support.reason}</p>
          {citation.support.method&&run.current_support_method&&citation.support.method!==run.current_support_method&&<p className="rounded bg-amber-50 p-3">Recorded assessment uses an earlier method. It has not been reassessed by {run.current_support_method}.</p>}
          <p className="text-sm">The support judge uses the same model as the generator; this is not independent fact verification. Trust score is unavailable.</p>
          <p>{citation.metadata.title} · {citation.metadata.issuer}</p><p>Version {citation.metadata.version_number||'recorded'} · physical page {citation.metadata.pdf_page_number??'TXT'} · source characters [{citation.start_offset}, {citation.end_offset})</p>
          <p>Extraction: {citation.metadata.extraction_method||'digital'} · revision {citation.metadata.extraction_revision_id||'original'}. {citation.metadata.ocr_notice}</p><p>Published: {citation.metadata.publication_date||'unknown'} · effective date: {citation.metadata.effective_date||'unknown'} · recorded applicability: {citation.metadata.review.applicability}. Historical sources do not establish current entitlement.</p>
          {citation.metadata.section_label&&<p>Detected section (heuristic): {citation.metadata.section_label}</p>}
          <a className="break-all underline" href={citation.metadata.source_url} target="_blank" rel="noreferrer">Official source</a>
          <p>Current access: {citation.current_access.allowed?'eligible under the recorded review':`withheld (${citation.current_access.reasons.join(', ')})`}</p>
          <blockquote className="whitespace-pre-wrap border-l-2 pl-3">{citation.quote||'Exact excerpt withheld; private snapshot is preserved.'}</blockquote>
          <button className="underline" disabled={!citation.current_access.allowed} onClick={()=>void inspect()}>Open cited source text</button>
          {inspection&&<div><p>Original extracted text · physical page {inspection.pdf_page_number??'TXT'} · window begins at {inspection.offset} / {inspection.total_characters} characters</p><pre className="whitespace-pre-wrap">{inspection.text}</pre></div>}
        </aside>}
        <p className="break-all text-xs">{run.model?.tag} · digest {run.model?.digest} · total {run.timings?.worker_total_ms} ms</p></>}
      {run.evidence_quality&&<EvidenceQuality assessment={run.evidence_quality} language={run.language}/>}
    </section>}
    <section className="rounded border bg-white p-4"><h2 className="text-xl font-semibold">Your query history</h2><p className="text-sm">Private to your account. Thirty-day retention; snapshots are not proof of ongoing source eligibility.</p>
      {!history.length&&<p>No records on this page.</p>}<ul>{history.map(r=><li key={r.id} className="mt-3"><button disabled={pending} className="text-left underline" onClick={()=>void select(r.id)}>{r.question}</button><p className="text-xs">{r.created_at} · {r.state} · {r.status || r.error_code}</p></li>)}</ul>
      <div className="mt-3 flex gap-4"><button disabled={pending || historyPage===1} onClick={()=>void changePage(historyPage-1)}>Previous history</button><span>Page {historyPage}</span><button disabled={pending || history.length<20} onClick={()=>void changePage(historyPage+1)}>Next history</button><button className="underline" onClick={()=>void refresh().catch(e=>setError(failure(e)))}>Refresh history</button></div>
    </section>
  </section>
}
