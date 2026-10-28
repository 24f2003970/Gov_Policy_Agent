import { useEffect, useRef, useState, type FormEvent } from 'react'
import { authorized, type User } from './auth'
import { type Assessment } from './EvidenceQuality'
import AnswerDetail, { type Answer } from './AnswerDetail'
import { translate, statusLabel } from './ui'
import PolicyQuote from './PolicyQuote'

type Evidence = {id: string; quote: string; quote_start_offset: number; quote_end_offset: number}
type Support = {outcome:string; method:string|null; reason:string; judge_called?:boolean; independent_verification:boolean}
type Citation = {citation_id:string; claim_id:string; claim_position:number; marker:number; claim_text:string|null; quote:string|null; start_offset:number; end_offset:number;
  metadata:{extraction_method?:string;extraction_revision_id?:string;ocr_notice?:string;title:string; issuer:string; source_url:string; version_id:string; version_number?:number; pdf_page_number:number|null; page_ordinal:number; publication_date:string|null; effective_date:string|null; section_label:string|null; section_is_heuristic:boolean; clause:null; review:{applicability:string}};
  provenance:{status:string; method:string; reason:string}; support:Support; current_access:{allowed:boolean; reasons:string[]; applicability?:string}}
type Result = {status: string; language: string; answer: string; claims: {claim_id?:string; text: string; evidence: Evidence[]; support?:Support; citation_markers?:number[]}[]; limitations: string[]; trust_score: null; grounding: string}
type Source = {chunk_id: string; version_id: string; title: string; issuer: string; source_url: string; pdf_page_number: number | null; start_offset: number; end_offset: number; text: string|null; verification: {applicability: string; scope: string}}
type Run = {saved:boolean;can_save:boolean;evidence_quality?:Assessment;retrieval_question?:string;query_normalization?:{transformations:string[];selection?:string};id: string; question: string; language: string; state: string; status: string | null; error_code: string | null; created_at: string; result?: Result | null; sources?: Source[]; citations?:Citation[]; claim_checks?:{position:number;retained:boolean;assessment:Support}[]; source_access_withheld?:boolean; current_support_method?:string; current_source_warnings?: {warning: string}[]; model?: {tag: string; digest: string}; timings?: {worker_total_ms: number;verification?:{total_ms:number}}}
type LibrarySource={version_id:string;title:string;eligible:boolean;applicability:string;reasons:string[]}
type RecentRun={id:string;question:string;created_at:string;status:string|null;state:string}
const input='field-control'
const failure=(e:unknown)=>e instanceof Error?e.message:'Request failed'

export default function Ask({user}:{user:User}) {
  const t=translate(user)
  const initialQuestion=new URLSearchParams(location.hash.split('?')[1]||'').get('question')||''
  const [question,setQuestion]=useState(initialQuestion),[sources,setSources]=useState<LibrarySource[]>([]),[recent,setRecent]=useState<RecentRun[]>([])
  const [run,setRun]=useState<Run|null>(null)
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[worker,setWorker]=useState<boolean|null>(null)
  const live=useRef(true),active=useRef<string|null>(null)
  async function refresh() {
    const s=await authorized<{worker_available:boolean}>('/ask/status')
    if(live.current){setWorker(s.worker_available)}
  }
  useEffect(()=>{live.current=true;void refresh().catch(e=>setError(failure(e)));return()=>{live.current=false;
    if(active.current)void authorized(`/ask/history/${active.current}/cancel`,{method:'POST'}).catch(()=>{})}},[])
  useEffect(()=>{let disposed=false;Promise.all([authorized<{sources:LibrarySource[]}>('/search/status'),authorized<{items:RecentRun[]}>('/ask/history?page=1')]).then(([s,h])=>{if(!disposed){setSources(s.sources);setRecent(h.items.slice(0,3))}}).catch(()=>{});return()=>{disposed=true}},[])
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
  return <section className="page-stack ask-page"><div className="ask-dashboard-grid"><div className="ask-main-column">
    <section className="ask-hero"><img src="/images/policy-hero-watercolor.png" alt="" className="ask-hero-art"/><div className="ask-hero-copy"><p className="eyebrow">{t('EVIDENCE FROM REVIEWED DOCUMENTS','जाँचे गए दस्तावेज़ों से साक्ष्य')}</p><h1>{t('Ask. Explore.','पूछें। खोजें।')}<br/><em>{t('Understand.','समझें।')}</em></h1><p>{t('Get clear answers about historical government policies with citations you can inspect.','ऐतिहासिक सरकारी नीतियों पर साफ जवाब पाएँ और उनके citations खुद जाँचें।')}</p><span className={`service-pill ${worker?'is-ready':''}`}><i/>{worker===null?t('Checking answer service','उत्तर सेवा जाँच रहे हैं'):worker?t('Answer service ready','उत्तर सेवा तैयार'):t('Answer service offline','उत्तर सेवा बंद है')}</span></div></section>
    <p className="notice ask-caution">{t('Historical sources do not establish current eligibility or application advice. Final claims appear after checks; evidence coverage is not correctness.','पुराने स्रोत आज की पात्रता या आवेदन सलाह तय नहीं करते। जाँच के बाद दावे दिखते हैं; evidence coverage correctness की गारंटी नहीं है।')}</p>
    <p className="ask-service-line" role="status">{worker===null?t('Checking answer worker…','Answer worker जाँच रहे हैं…'):worker?t('Ready to check source evidence','स्रोत साक्ष्य जाँचने के लिए तैयार'):t('Answer worker is offline. Start the local service, then retry.','Answer worker बंद है। Local service चालू करें, फिर कोशिश करें।')} <button onClick={()=>void refresh().catch(e=>setError(failure(e)))}>{t('Retry','फिर कोशिश करें')}</button></p>
    {error&&<p role="alert" className="error-banner">{error}</p>}
    <form onSubmit={e=>void submit(e)} className="panel ask-composer">
      <div className="ask-composer-heading"><div><p className="eyebrow">{t('POLICY RESEARCH','नीति शोध')}</p><h2>{t('Start with a question','सवाल से शुरुआत करें')}</h2></div><span className="ask-token-count">{question.length}/2000</span></div>
      <label className="sr-only" htmlFor="ask-question">{t('Your question','आपका सवाल')}</label><div className="ask-question-row"><textarea id="ask-question" className={`${input} ask-question-input`} name="question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder={t('Ask about a scheme, policy, benefit, or government document…','किसी योजना, नीति, लाभ या सरकारी दस्तावेज़ के बारे में पूछें…')} minLength={2} maxLength={2000} required rows={3}/><button className="ask-send-button" disabled={pending} aria-label={pending?t('Checking','जाँच जारी है'):t('Ask sources','स्रोत से पूछें')}>{pending?'…':'➤'}</button></div>
      <div className="ask-composer-options"><label><span>◎</span><select className={input} name="language" defaultValue={user.preferred_language==='en'?'en':'hi'} aria-label={t('Answer language','जवाब की भाषा')}><option value="en">English</option><option value="hi">Hindi</option></select></label><details className="ask-filter-details"><summary>⚑ {t('Optional filters','वैकल्पिक filters')}</summary><div className="ask-filter-grid">{['scheme','issuer','document_type'].map(k=><label key={k}>{k==='scheme'?t('Scheme','योजना'):k==='issuer'?t('Ministry / issuer','मंत्रालय / जारीकर्ता'):t('Document type','दस्तावेज़ प्रकार')}<input name={k} className={input} maxLength={k==='document_type'?80:200}/></label>)}<label>{t('Published from','प्रकाशन शुरू')}<input type="date" name="published_after" className={input}/></label><label>{t('Published to','प्रकाशन अंत')}<input type="date" name="published_before" className={input}/></label><label>{t('Undated sources','बिना तारीख के स्रोत')}<select name="unknown_dates" className={input}><option value="exclude">{t('Exclude when filtering dates','तारीख filter पर हटाएँ')}</option><option value="include">{t('Include unknown dates','बिना तारीख के भी रखें')}</option></select></label></div></details><span className="ask-token-note">{t('Ask one specific thing at a time for the clearest evidence.','साफ evidence के लिए एक बार में एक बात पूछें।')}</span></div>
      <button className="sr-only" disabled={pending}>{pending?t('Checking…','जाँच चल रही है…'):t('Ask sources','स्रोत से पूछें')}</button>
    </form>
    <section className="ask-prompt-section"><div className="ask-section-heading"><h2>{t('Try a question','इनमें से पूछें')}</h2><a href="#search">{t('Search passages','स्रोत खोजें')} →</a></div><div className="ask-prompt-grid">{[
      t('What benefits does PM-KISAN describe for eligible farmers?','PM-KISAN में पात्र किसानों के लिए कौन से लाभ बताए गए हैं?'),t('Which eligibility conditions appear in the Ayushman Bharat documents?','आयुष्मान भारत दस्तावेज़ों में कौन सी पात्रता शर्तें हैं?'),t('What does the source say about PM Awas Yojana assistance?','PM आवास योजना की सहायता के बारे में स्रोत क्या कहता है?'),t('Which documents are mentioned in the Ujjwala scheme guidance?','उज्ज्वला योजना के निर्देशों में कौन से दस्तावेज़ बताए गए हैं?')
    ].map(q=><button key={q} type="button" onClick={()=>{setQuestion(q);document.getElementById('ask-question')?.focus()}}>{q}<span>→</span></button>)}</div></section>
    <section className="ask-category-section"><div className="ask-section-heading"><div><p className="eyebrow">{t('EXPLORE BY TOPIC','विषय के अनुसार खोजें')}</p><h2>{t('Government policy areas','सरकारी नीति के क्षेत्र')}</h2></div><a href="#search">{t('Browse passages','अंश देखें')} →</a></div><div className="ask-category-grid">{[
      ['🌱',t('Agriculture & farmers','कृषि और किसान'),t('Ask about farmer schemes and support.','किसान योजनाओं और सहायता के बारे में पूछें。'),'agriculture'],['♡',t('Health & insurance','स्वास्थ्य और बीमा'),t('Ask about health coverage and eligibility.','स्वास्थ्य कवरेज और पात्रता पूछें。'),'health'],['⌂',t('Housing','आवास'),t('Ask about housing policy documents.','आवास नीति दस्तावेज़ों के बारे में पूछें。'),'housing'],['♧',t('Social welfare','सामाजिक कल्याण'),t('Ask about public support programmes.','सार्वजनिक सहायता योजनाओं के बारे में पूछें。'),'welfare']
    ].map(([icon,title,desc,kind])=><button key={kind} type="button" className={`ask-category-card category-${kind}`} onClick={()=>{setQuestion(String(title)+' — '+String(desc));document.getElementById('ask-question')?.focus()}}><span>{icon}</span><strong>{title}</strong><small>{desc}</small><i>→</i></button>)}</div></section>
    {recent.length>0&&<section className="card ask-recent-section"><div className="ask-section-heading"><div><p className="eyebrow">{t('YOUR WORKSPACE','आपका कार्यक्षेत्र')}</p><h2>{t('Recently asked','हाल में पूछे गए')}</h2></div><a href="#history">{t('View history','इतिहास देखें')} →</a></div><div className="ask-recent-grid">{recent.map(r=><a key={r.id} href={`#history/${r.id}`}><span>◷</span><strong>{r.question}</strong><small>{new Date(r.created_at).toLocaleDateString(user.preferred_language==='en'?'en-IN':'hi-IN')} · {statusLabel(r.status||r.state,user.preferred_language!=='en')}</small></a>)}</div></section>}
    </div><aside className="ask-sidebar"><section className="card ask-source-panel"><div className="ask-section-heading"><div><p className="eyebrow">{t('REVIEWED LIBRARY','जाँची लाइब्रेरी')}</p><h2>{t('Available sources','उपलब्ध स्रोत')}</h2></div><a href="#search">{t('View all','सभी देखें')} →</a></div>{sources.filter(s=>s.eligible).slice(0,4).map((s,i)=><a className="ask-source-row" key={s.version_id} href={`#search?query=${encodeURIComponent(s.title)}`}><span className={`ask-source-icon source-tone-${i%3}`}>▤</span><span><strong>{s.title}</strong><small>{s.applicability}</small></span><i>›</i></a>)}{!sources.some(s=>s.eligible)&&<p className="muted">{t('No eligible reviewed sources are available in the active index yet.','Active index में अभी कोई पात्र जाँचा हुआ source नहीं है।')}</p>}<p className="ask-sidebar-footnote">{t('Only sources in the active reviewed index appear here.','यहाँ सिर्फ active reviewed index के sources दिखते हैं।')}</p></section>
      <section className="card ask-quick-stats"><p className="eyebrow">{t('AT A GLANCE','एक नज़र में')}</p><h2>{t('Workspace status','कार्यक्षेत्र स्थिति')}</h2><div><span className="quick-icon">▤</span><strong>{sources.filter(s=>s.eligible).length}</strong><small>{t('eligible sources','पात्र स्रोत')}</small></div><div><span className="quick-icon">◎</span><strong>2</strong><small>{t('answer languages','जवाब की भाषाएँ')}</small></div><div><span className={`quick-icon ${worker?'quick-icon-ready':''}`}>◉</span><strong>{worker===null?'…':worker?t('Ready','तैयार'):t('Offline','बंद')}</strong><small>{t('local answer worker','local answer worker')}</small></div></section><p className="ask-sidebar-caution">ⓘ {t('Always check the cited document date and page.','हमेशा citation वाले दस्तावेज़ की तारीख और पेज जाँचें।')}</p><PolicyQuote hindi={user.preferred_language!=='en'}/></aside></div>
    {run&&<section className="panel answer-card"><h2>{statusLabel(run.status||run.state,user.preferred_language!=='en')}</h2><p>{run.question}</p>{run.query_normalization&&<details><summary>{t('Retrieval details','खोज का विवरण')}</summary><p className="text-sm">Retrieval query: {run.retrieval_question}. Changes: {run.query_normalization.transformations.join(', ')||'none'}. Input detection never changes your selected response language.</p></details>}
      {['queued','processing'].includes(run.state)&&<><p role="status">{t('Checking source evidence. No unchecked claims are shown.','स्रोत के साक्ष्य जाँचे जा रहे हैं। बिना जाँच दावे नहीं दिखते।')}</p><button className="underline" onClick={()=>void cancel()}>{t('Cancel request','प्रश्न रद्द करें')}</button></>}
      {run.state==='error'&&<div role="alert" className="error-banner"><strong>{t('No checked answer was available for this question.','Is sawaal ke liye jaancha hua jawab nahi mil saka.')}</strong><p>{t('Try asking one specific thing at a time, or open Search to inspect matching passages.','Ek baar mein ek specific baat poochhein, ya passages dekhne ke liye Search kholein.')}</p><details><summary>{t('Technical details','तकनीकी जानकारी')}</summary><code>{run.error_code||'request_failed'}</code></details></div>}
      {run.state==='cancelled'&&<p>Request cancelled; no answer published.</p>}
      <AnswerDetail key={run.id} user={user} run={run as Answer} onUpdate={v=>setRun(v as Run)}/>
    </section>}
    <a href="#history">{t('View your history','अपना इतिहास देखें')}</a>
  </section>
}
