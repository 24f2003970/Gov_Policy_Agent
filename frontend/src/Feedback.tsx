import { useEffect, useRef, useState, type FormEvent } from 'react'
import { authorized, type User } from './auth'
import { translate } from './ui'
export type Selection={vote:'helpful'|'not_helpful';reason:string|null;comment:string|null}
const reasons=[['unclear_wording','Unclear wording','अस्पष्ट शब्द'],['incomplete_answer','Incomplete answer','अधूरा उत्तर'],['citation_issue','Citation issue','संदर्भ की समस्या'],['language_issue','Language issue','भाषा की समस्या'],['suspected_factual_error','Suspected factual error','तथ्य गलत होने का संदेह']]
export default function Feedback({user,id,current,onUpdate,onRefresh}:{user:User;id:string;current:Selection|null;onUpdate:(v:Selection|null)=>void;onRefresh:()=>Promise<void>}) {
  const t=translate(user),[vote,setVote]=useState(current?.vote||''),[reason,setReason]=useState(current?.reason||''),[comment,setComment]=useState(current?.comment||'')
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('')
  const live=useRef(true)
  useEffect(()=>{live.current=true;return()=>{live.current=false}},[])
  useEffect(()=>{setVote(current?.vote||'');setReason(current?.reason||'');setComment(current?.comment||'')},[current?.vote,current?.reason,current?.comment])
  async function write(remove=false){setBusy(true);setError('');setNotice('')
    try{const v=await authorized<{feedback:Selection|null}>(`/ask/history/${id}/feedback`,{method:remove?'DELETE':'PUT',...(remove?{}:{body:JSON.stringify({vote,reason:reason||null,comment:comment||null})})});if(!live.current)return;onUpdate(v.feedback);setNotice(t(remove?'Feedback removed.':'Feedback saved.',remove?'प्रतिक्रिया हटाई गई।':'प्रतिक्रिया सहेजी गई।'))}
    catch{if(!live.current)return;setError(t('Feedback could not be updated. Source access may have changed; refresh and try again.','प्रतिक्रिया नहीं बदल पाई। स्रोत की अनुमति बदल सकती है; ताज़ा करके फिर कोशिश करें।'));await onRefresh()}
    finally{setBusy(false)}
  }
  function submit(e:FormEvent){e.preventDefault();void write()}
  return <section className="card space-y-3" aria-label={t('Private answer feedback','उत्तर पर निजी प्रतिक्रिया')}><h2>{t('Your feedback','आपकी प्रतिक्रिया')}</h2>
    <p className="muted text-sm">{t('Private to your account. Feedback helps improve the application; a helpful vote does not verify policy correctness. Answers and feedback expire after 30 days.','सिर्फ आपके खाते के लिए। प्रतिक्रिया ऐप सुधारने में मदद करती है; उपयोगी वोट नीति के सही होने की पुष्टि नहीं है। उत्तर और प्रतिक्रिया 30 दिन बाद हटते हैं।')}</p>
    <p>{t('Current feedback:','वर्तमान प्रतिक्रिया:')} {current?t(current.vote==='helpful'?'Helpful':'Not helpful',current.vote==='helpful'?'उपयोगी':'उपयोगी नहीं'):t('None','कोई नहीं')}</p>
    <form onSubmit={submit} className="space-y-3"><fieldset disabled={busy}><legend>{t('Was this answer helpful?','क्या यह उत्तर उपयोगी था?')}</legend><div className="flex flex-wrap gap-5">{(['helpful','not_helpful'] as const).map(v=><label className="flex gap-2 items-center" key={v}><input type="radio" name={`feedback-${id}`} value={v} checked={vote===v} onChange={()=>setVote(v)} required/>{t(v==='helpful'?'Helpful':'Not helpful',v==='helpful'?'उपयोगी':'उपयोगी नहीं')}</label>)}</div></fieldset>
      <label className="block">{t('Optional reason','वैकल्पिक कारण')}<select disabled={busy} className="mt-1 w-full rounded border p-2" value={reason} onChange={e=>setReason(e.target.value)}><option value="">{t('No reason selected','कोई कारण नहीं चुना')}</option>{reasons.map(([v,en,hi])=><option key={v} value={v}>{t(en,hi)}</option>)}</select></label>
      <label className="block">{t('Optional comment (500 characters maximum)','वैकल्पिक टिप्पणी (अधिकतम 500 अक्षर)')}<textarea disabled={busy} className="mt-1 w-full rounded border p-2" rows={2} maxLength={500} value={comment} onChange={e=>setComment(e.target.value)}/></label>
      <div className="flex flex-wrap gap-3"><button disabled={busy||!vote} aria-busy={busy}>{busy?t('Saving…','सहेज रहा है…'):t(current?'Update feedback':'Save feedback',current?'प्रतिक्रिया बदलें':'प्रतिक्रिया सहेजें')}</button>{current&&<button type="button" disabled={busy} onClick={()=>void write(true)}>{t('Remove feedback','प्रतिक्रिया हटाएँ')}</button>}</div>
    </form>{error&&<p role="alert" className="notice">{error}</p>}{notice&&<p role="status">{notice}</p>}
  </section>
}
