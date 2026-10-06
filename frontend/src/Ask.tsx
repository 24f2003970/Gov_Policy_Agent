import { useEffect, useRef, useState, type FormEvent } from 'react'
import { authorized, type User } from './auth'
import { type Assessment } from './EvidenceQuality'
import AnswerDetail, { type Answer } from './AnswerDetail'
import { translate, statusLabel } from './ui'

type Evidence = {id: string; quote: string; quote_start_offset: number; quote_end_offset: number}
type Support = {outcome:string; method:string|null; reason:string; judge_called?:boolean; independent_verification:boolean}
type Citation = {citation_id:string; claim_id:string; claim_position:number; marker:number; claim_text:string|null; quote:string|null; start_offset:number; end_offset:number;
  metadata:{extraction_method?:string;extraction_revision_id?:string;ocr_notice?:string;title:string; issuer:string; source_url:string; version_id:string; version_number?:number; pdf_page_number:number|null; page_ordinal:number; publication_date:string|null; effective_date:string|null; section_label:string|null; section_is_heuristic:boolean; clause:null; review:{applicability:string}};
  provenance:{status:string; method:string; reason:string}; support:Support; current_access:{allowed:boolean; reasons:string[]; applicability?:string}}
type Result = {status: string; language: string; answer: string; claims: {claim_id?:string; text: string; evidence: Evidence[]; support?:Support; citation_markers?:number[]}[]; limitations: string[]; trust_score: null; grounding: string}
type Source = {chunk_id: string; version_id: string; title: string; issuer: string; source_url: string; pdf_page_number: number | null; start_offset: number; end_offset: number; text: string|null; verification: {applicability: string; scope: string}}
type Run = {saved:boolean;can_save:boolean;evidence_quality?:Assessment;retrieval_question?:string;query_normalization?:{transformations:string[];selection?:string};id: string; question: string; language: string; state: string; status: string | null; error_code: string | null; created_at: string; result?: Result | null; sources?: Source[]; citations?:Citation[]; claim_checks?:{position:number;retained:boolean;assessment:Support}[]; source_access_withheld?:boolean; current_support_method?:string; current_source_warnings?: {warning: string}[]; model?: {tag: string; digest: string}; timings?: {worker_total_ms: number;verification?:{total_ms:number}}}
const input='mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2'
const button='rounded bg-teal-900 px-4 py-2 text-white disabled:opacity-50'
const failure=(e:unknown)=>e instanceof Error?e.message:'Request failed'

export default function Ask({user}:{user:User}) {
  const t=translate(user)
  const [run,setRun]=useState<Run|null>(null)
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[worker,setWorker]=useState<boolean|null>(null)
  const live=useRef(true),active=useRef<string|null>(null)
  async function refresh() {
    const s=await authorized<{worker_available:boolean}>('/ask/status')
    if(live.current){setWorker(s.worker_available)}
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
  async function cancel(){if(!run)return;setError('');try{setRun(await authorized<Run>(`/ask/history/${run.id}/cancel`,{method:'POST'}))}catch(e){setError(failure(e))}}
  return <section className="space-y-6"><h1>{t('Ask','प्रश्न पूछें')}</h1>
    <p className="notice">{t('Ask about a dated historical document. These sources do not establish current entitlement or application advice. Final claims appear after checks; evidence coverage is not correctness.','किसी तिथि वाले ऐतिहासिक दस्तावेज़ पर प्रश्न पूछें। ये स्रोत वर्तमान पात्रता या आवेदन की सलाह साबित नहीं करते। जाँच के बाद उत्तर दिखता है; साक्ष्य कवरेज सही होने की गारंटी नहीं है।')}</p>
    <p className="muted" role="status">{worker===null?t('Checking service…','सेवा की जाँच…'):worker?t('Ready for a question','प्रश्न के लिए तैयार'):t('Answer service unavailable. Start the local service, then retry.','उत्तर सेवा उपलब्ध नहीं। स्थानीय सेवा शुरू करके फिर कोशिश करें।')} <button onClick={()=>void refresh().catch(e=>setError(failure(e)))}>{t('Retry','फिर कोशिश करें')}</button></p>
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}
    <form onSubmit={e=>void submit(e)} className="space-y-3 rounded border bg-white p-4">
      <label className="block">{t('Question','प्रश्न')}<textarea className={input} name="question" minLength={2} maxLength={2000} required rows={3}/></label>
      <label className="block">{t('Response language','उत्तर की भाषा')}<select className={input} name="language" defaultValue={user.preferred_language==='en'?'en':'hi'}><option value="en">English</option><option value="hi">Hindi</option></select></label>
      <details><summary>{t('Optional filters','वैकल्पिक फ़िल्टर')}</summary>{['scheme','issuer','document_type'].map(k=><label className="block" key={k}>{k==='scheme'?'Scheme filter':k==='issuer'?'Ministry / issuer filter':'Document type filter'}<input name={k} className={input} maxLength={k==='document_type'?80:200}/></label>)}
      <label className="block">Published on/after<input type="date" name="published_after" className={input}/></label>
      <label className="block">Published on/before<input type="date" name="published_before" className={input}/></label>
      <label className="block">Unknown publication dates<select name="unknown_dates" className={input}><option value="exclude">Exclude when filtering dates</option><option value="include">Include as unknown</option></select></label>
      </details><button className={button} disabled={pending}>{pending?t('Checking…','जाँच चल रही है…'):t('Ask sources','स्रोत से पूछें')}</button>
    </form>
    {run&&<section className="space-y-3 rounded border bg-white p-4"><h2 className="text-xl font-semibold">{statusLabel(run.status||run.state,user.preferred_language!=='en')}</h2><p>{run.question}</p>{run.query_normalization&&<details><summary>{t('Retrieval details','खोज का विवरण')}</summary><p className="text-sm">Retrieval query: {run.retrieval_question}. Changes: {run.query_normalization.transformations.join(', ')||'none'}. Input detection never changes your selected response language.</p></details>}
      {['queued','processing'].includes(run.state)&&<><p role="status">{t('Checking source evidence. No unchecked claims are shown.','स्रोत के साक्ष्य जाँचे जा रहे हैं। बिना जाँच दावे नहीं दिखते।')}</p><button className="underline" onClick={()=>void cancel()}>{t('Cancel request','प्रश्न रद्द करें')}</button></>}
      {run.state==='error'&&<p role="alert">Service or grounding error: {run.error_code}. No policy answer published.</p>}
      {run.state==='cancelled'&&<p>Request cancelled; no answer published.</p>}
      <AnswerDetail key={run.id} user={user} run={run as Answer} onUpdate={v=>setRun(v as Run)}/>
    </section>}
    <a href="#history">{t('View your history','अपना इतिहास देखें')}</a>
  </section>
}
