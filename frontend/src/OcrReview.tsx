import { useEffect, useState } from 'react'
import { authorized, authorizedResponse } from './auth'

type Page = { id:string; ordinal:number; method:string; characters:number; quality_flags:string[]; review:string|null; signals:Record<string,unknown> }
type Revision = { id:string; state:string; attempts:number; processed:number; total:number; error_code:string|null; pages:Page[] }
type Text = { text:string; method:string; total_characters:number; offset:number; signals:Record<string,unknown>; quality_flags:string[]; boxes:unknown[] }

export default function OcrReview({ versionId }: {versionId:string}) {
  const [revisions,setRevisions]=useState<Revision[]>([]),[selected,setSelected]=useState<Page|null>(null)
  const [text,setText]=useState<Text|null>(null),[offset,setOffset]=useState(0),[preview,setPreview]=useState('')
  const [reason,setReason]=useState(''),[checked,setChecked]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const latest=revisions[0]
  async function refresh(){const response=await authorized<{items:Revision[]}>(`/admin/ocr/versions/${versionId}`);setRevisions(response.items);setError('')}
  useEffect(()=>{let disposed=false;setRevisions([]);setError('');setSelected(null);setText(null);setPreview('');
    void authorized<{items:Revision[]}>(`/admin/ocr/versions/${versionId}`).then(r=>{if(!disposed)setRevisions(r.items)}).catch(e=>{if(!disposed)setError(String(e))});
    return()=>{disposed=true}},[versionId])
  useEffect(()=>{if(!latest||!['queued','processing'].includes(latest.state))return;let count=0,inFlight=false;
    const timer=setInterval(()=>{if(inFlight)return;if(++count>120){clearInterval(timer);return}inFlight=true;
      void refresh().catch(e=>setError(String(e))).finally(()=>{inFlight=false})},3000);return()=>clearInterval(timer)},[versionId,latest?.id,latest?.state])
  useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview)},[preview])
  useEffect(()=>{if(!selected)return;let disposed=false;void authorized<Text>(`/admin/ocr/pages/${selected.id}/text?offset=${offset}`)
    .then(r=>{if(!disposed)setText(r)}).catch(e=>{if(!disposed)setError(String(e))});return()=>{disposed=true}},[selected?.id,offset])
  async function action(path:string,body?:unknown){setBusy(true);setError('');try{await authorized(path,{method:'POST',...(body?{body:JSON.stringify(body)}:{})});await refresh()}
    catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}}
  async function original(){if(!selected)return;setError('');try{const response=await authorizedResponse(`/admin/documents/versions/${versionId}/preview/${selected.ordinal}`);
    setPreview(URL.createObjectURL(await response.blob()))}catch(e){setError(String(e))}}
  return <section className="space-y-3 rounded border p-4"><h4 className="font-semibold">OCR extraction and review</h4>
    <p className="text-sm">English/Hindi OCR processes flagged low-text pages. Digital text and old citations remain intact. All OCR pages need comparison with the original; OCR signals do not establish accuracy. Rights and source eligibility need separate approval. Rebuild the index explicitly after a completed review.</p>
    {error&&<p role="alert" className="text-red-800">{error}</p>}
    <div className="flex flex-wrap gap-3"><button disabled={busy} className="underline" onClick={()=>void action(`/admin/ocr/versions/${versionId}/queue`)}>Queue OCR revision</button>
      <button className="underline" onClick={()=>void refresh().catch(e=>setError(String(e)))}>Refresh OCR</button>
      {latest&&['failed','partial'].includes(latest.state)&&<button disabled={busy||latest.attempts>=3} className="underline" onClick={()=>void action(`/admin/ocr/${latest.id}/retry`)}>Retry OCR</button>}
      {latest&&['queued','processing'].includes(latest.state)&&<button disabled={busy} className="underline" onClick={()=>void action(`/admin/ocr/${latest.id}/cancel`)}>Cancel OCR</button>}</div>
    {latest&&<><p role="status">Revision {latest.id}: {latest.state} · {latest.processed}/{latest.total} pages · attempt {latest.attempts}/3 {latest.error_code}</p>
      <label className="block">Extraction revision<select className="w-full border p-2" value={selected?revisions.find(r=>r.pages.some(p=>p.id===selected.id))?.id:latest.id}
        onChange={e=>{const r=revisions.find(r=>r.id===e.target.value);setSelected(r?.pages[0]||null);setOffset(0);setPreview('')}}>{revisions.map(r=><option key={r.id} value={r.id}>{r.id} · {r.state}</option>)}</select></label>
      <label className="block">OCR source page<select className="w-full border p-2" value={selected?.id||''} onChange={e=>{const p=revisions.flatMap(r=>r.pages).find(p=>p.id===e.target.value);setSelected(p||null);setOffset(0);setText(null);setPreview('');setChecked(false);setReason('')}}>
        <option value="">Choose a physical page</option>{(selected?revisions.find(r=>r.pages.some(p=>p.id===selected.id))?.pages:latest.pages)?.map(p=><option key={p.id} value={p.id}>Page {p.ordinal} · {p.method} · {p.characters} characters · {p.review||p.quality_flags.join(', ')}</option>)}</select></label></>}
    {selected&&text&&<><p>Physical page {selected.ordinal} · {text.method} · {text.quality_flags.join(', ')}</p>
      <button className="underline" onClick={()=>void original()}>Compare original page</button>
      {preview&&<img alt={`Protected original page ${selected.ordinal}`} src={preview} className="w-full border"/>}
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words bg-slate-50 p-3">{text.text||'No readable OCR text'}</pre>
      <p className="text-sm">Characters [{offset}, {Math.min(offset+20000,text.total_characters)}) of {text.total_characters}</p>
      <button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-20000))}>Previous text</button>{' '}
      <button disabled={offset+20000>=text.total_characters} onClick={()=>setOffset(offset+20000)}>Next text</button>
      <details><summary>OCR signals and word boxes</summary><pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify({signals:text.signals,boxes:text.boxes},null,2)}</pre></details>
      {text.method==='ocr'&&<><label className="block"><input type="checkbox" checked={checked} onChange={e=>setChecked(e.target.checked)}/> I compared amounts, dates, installment counts, names, categories, conditions and negation with the original.</label>
        <label className="block">Review reason<textarea className="w-full border p-2" value={reason} onChange={e=>setReason(e.target.value)} maxLength={2000}/></label>
        <div className="flex gap-3">{(['accepted','rejected'] as const).map(decision=><button className="underline" key={decision} disabled={busy||!checked||reason.trim().length<20||(decision==='accepted'&&text.quality_flags.includes('low_quality'))}
          onClick={()=>void action(`/admin/ocr/pages/${selected.id}/reviews`,{decision,reason,checked_values_dates_categories_negation:true})}>{decision==='accepted'?'Accept transcription':'Reject transcription'}</button>)}</div></>}
      <p className="text-sm">Raw OCR is preserved. Text editing/correction is deferred; never guess a replacement value.</p></>}
  </section>
}
