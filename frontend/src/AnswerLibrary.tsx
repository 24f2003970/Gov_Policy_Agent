import { useEffect, useState } from 'react'
import { authorized, type User } from './auth'
import { translate, statusLabel } from './ui'

type Item = {id:string;question:string;created_at:string;state:string;status:string|null;available?:boolean}
type Page = {items:Item[];page:number;has_next:boolean;total:number}
export default function AnswerLibrary({user,saved,initialPage=1}:{user:User;saved:boolean;initialPage?:number}) {
  const t=translate(user),hi=user.preferred_language!=='en'
  const [page,setPage]=useState(initialPage),[data,setData]=useState<Page|null>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0)
  useEffect(()=>setPage(initialPage),[initialPage])
  useEffect(()=>{
    let disposed=false;setData(null);setError('')
    authorized<Page>(`/ask/${saved?'saved':'history'}?page=${page}`).then(v=>{if(!disposed)setData(v)})
      .catch(()=>{if(!disposed)setError(t('Could not load your records. Try again.','आपके रिकॉर्ड नहीं खुल पाए। फिर कोशिश करें।'))})
    return()=>{disposed=true}
  },[saved,page,retry,user.preferred_language])
  return <section className="space-y-5"><h1>{saved?t('Saved answers','सहेजे गए उत्तर'):t('History','इतिहास')}</h1>
    <p className="muted">{t('Private to your account. Records expire 30 days after the original question, including saved answers. Source access is checked when you open a record.','सिर्फ आपके खाते के लिए। सहेजे गए उत्तर भी मूल प्रश्न के 30 दिन बाद हटते हैं। रिकॉर्ड खोलते समय स्रोत की अनुमति फिर जाँची जाती है।')}</p>
    {error?<div role="alert" className="notice">{error} <button onClick={()=>setRetry(v=>v+1)}>{t('Retry','फिर कोशिश करें')}</button></div>:!data?<p role="status">{t('Loading records…','रिकॉर्ड खुल रहे हैं…')}</p>:<>
      {!data.items.length?<div className="card space-y-3"><h2>{saved?t('No saved answers yet','अभी कोई सहेजा गया उत्तर नहीं'):t('No questions on this page','इस पृष्ठ पर कोई प्रश्न नहीं')}</h2>
        <p>{saved?t('Open an answered or partial result and choose Save answer. Clarifications and empty results cannot be saved.','उत्तर या आंशिक उत्तर खोलें और “उत्तर सहेजें” चुनें। स्पष्टीकरण और खाली परिणाम नहीं सहेजे जा सकते।'):t('Ask a question about a reviewed historical source to get started.','शुरू करने के लिए जाँचे गए ऐतिहासिक स्रोत पर प्रश्न पूछें।')}</p><a href="#ask">{t('Go to Ask','प्रश्न पूछें')}</a></div>:
        <ul className="space-y-3">{data.items.map(r=><li className="card" key={r.id}><a className="text-lg font-semibold" href={`#${saved?'saved':'history'}/${r.id}?page=${page}`} >{r.question}</a>
          <p className="muted mt-2">{statusLabel(r.status||r.state,hi)} · <time dateTime={r.created_at}>{new Date(r.created_at).toLocaleString(hi?'hi-IN':'en-IN')}</time></p>
          {r.available===false&&<p className="notice mt-2">{t('Source unavailable. The bookmark remains, but answer text and evidence are withheld.','स्रोत उपलब्ध नहीं है। बुकमार्क मौजूद है, लेकिन उत्तर और साक्ष्य नहीं दिखाए जा सकते।')}</p>}</li>)}</ul>}
      <div className="flex flex-wrap items-center gap-3"><button disabled={page===1} onClick={()=>{location.hash=`${saved?'saved':'history'}?page=${page-1}`}}>{t('Previous','पिछला')}</button><span>{t('Page','पृष्ठ')} {page} · {data.total} {t('records','रिकॉर्ड')}</span><button disabled={!data.has_next} onClick={()=>{location.hash=`${saved?'saved':'history'}?page=${page+1}`}}>{t('Next','अगला')}</button><button onClick={()=>setRetry(v=>v+1)}>{t('Refresh','ताज़ा करें')}</button></div>
    </>}
  </section>
}
