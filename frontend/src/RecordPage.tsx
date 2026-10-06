import { useEffect, useState } from 'react'
import { authorized, type User } from './auth'
import AnswerDetail, { type Answer } from './AnswerDetail'
import { translate, statusLabel } from './ui'
export default function RecordPage({user,id,library,backPage=1}:{user:User;id:string;library:string;backPage?:number}) {
  const t=translate(user),[run,setRun]=useState<Answer|null>(null),[error,setError]=useState(false),[retry,setRetry]=useState(0)
  useEffect(()=>{let disposed=false;setRun(null);setError(false);authorized<Answer>(`/ask/history/${id}`).then(v=>{if(!disposed)setRun(v)}).catch(()=>{if(!disposed)setError(true)});return()=>{disposed=true}},[id,retry])
  return <section className="space-y-4"><a href={`#${library}?page=${backPage}`}>{t('Back to records','रिकॉर्ड पर लौटें')}</a><h1>{t('Answer detail','उत्तर का विवरण')}</h1>
    {error?<div role="alert" className="notice">{t('Record unavailable. It may have expired or belong to another account.','रिकॉर्ड उपलब्ध नहीं। इसकी अवधि समाप्त हो सकती है या यह दूसरे खाते का हो सकता है।')} <button onClick={()=>setRetry(v=>v+1)}>{t('Retry','फिर कोशिश करें')}</button></div>:!run?<p role="status">{t('Loading answer…','उत्तर खुल रहा है…')}</p>:<><h2>{run.question}</h2><p>{statusLabel(run.status||run.state,user.preferred_language!=='en')}</p><AnswerDetail user={user} run={run} onUpdate={setRun}/></>}
  </section>
}
