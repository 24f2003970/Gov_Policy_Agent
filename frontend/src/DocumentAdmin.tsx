import { useEffect, useState, type FormEvent } from 'react'
import { authorized, authorizedResponse } from './auth'

type Job = { state: string; progress: number; attempts: number; processed_pages: number; total_pages: number; error_code: string | null }
type Version = { id: string; document_id: string; version_number: number; checksum: string; original_name: string; format: string;
  size_bytes: number; source_url: string; provenance_status: string; metadata_snapshot: Record<string, unknown>;
  extraction_revision: string | null; chunk_profile: string | null; eligible_for_future_retrieval: boolean; job: Job }
type Item = { id: string; title: string; issuer: string; archived: boolean; latest_version: Version }
type Page = { ordinal: number; pdf_page_number: number | null; character_count: number; quality_flags: string[] }
type TextPage = { text: string; offset: number; total_characters: number; paragraphs: { start: number; end: number; section_label: string | null }[]; quality_flags: string[] }
const base = '/admin/documents'
const input = 'mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2'
const button = 'rounded bg-teal-900 px-4 py-2 text-white disabled:opacity-50'
const message = (error: unknown) => error instanceof Error ? error.message : 'Request failed'

export default function DocumentAdmin() {
  const [items, setItems] = useState<Item[]>([])
  const [total, setTotal] = useState(0)
  const [listPage, setListPage] = useState(1)
  const [selected, setSelected] = useState<Version | null>(null)
  const [versions, setVersions] = useState<Version[]>([])
  const [pages, setPages] = useState<Page[]>([])
  const [pageTotal, setPageTotal] = useState(0)
  const [pageList, setPageList] = useState(1)
  const [ordinal, setOrdinal] = useState(1)
  const [text, setText] = useState<TextPage | null>(null)
  const [offset, setOffset] = useState(0)
  const [inspectionRevision, setInspectionRevision] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState('')
  const [originalUrl, setOriginalUrl] = useState('')
  const [pollStopped, setPollStopped] = useState(false)
  const [verification, setVerification] = useState('')
  const [newVersion, setNewVersion] = useState(false)

  async function loadList(page = listPage) {
    const result = await authorized<{ items: Item[]; total: number }>(`${base}?page=${page}`)
    setItems(result.items); setTotal(result.total)
  }
  async function choose(version: Version) {
    setSelected(version); setText(null); setOrdinal(1); setOffset(0); setPageList(1); setPreview(''); setOriginalUrl(''); setError(''); setVerification('')
    setInspectionRevision(previous => previous + 1)
    const detail = await authorized<{ versions: Version[] }>(`${base}/${version.document_id}`)
    setVersions(detail.versions)
  }
  useEffect(() => { let disposed = false; authorized<{ items: Item[]; total: number }>(`${base}?page=${listPage}`)
    .then(result => { if (!disposed) { setItems(result.items); setTotal(result.total) } })
    .catch(failure => { if (!disposed) setError(message(failure)) }); return () => { disposed = true } }, [listPage])
  useEffect(() => {
    if (!selected) return
    let disposed = false
    authorized<{ items: Page[]; total: number }>(`${base}/versions/${selected.id}/pages?page=${pageList}`)
      .then(result => { if (!disposed) { setPages(result.items); setPageTotal(result.total) } })
      .catch(failure => { if (!disposed) setError(message(failure)) })
    return () => { disposed = true }
  }, [selected?.id, selected?.job.state, pageList, inspectionRevision])
  useEffect(() => {
    if (!selected || !pages.length) return
    let disposed = false
    authorized<TextPage>(`${base}/versions/${selected.id}/pages/${ordinal}?offset=${offset}`)
      .then(result => { if (!disposed) setText(result) }).catch(failure => { if (!disposed) setError(message(failure)) })
    return () => { disposed = true }
  }, [selected?.id, pages, ordinal, offset])
  useEffect(() => {
    setPollStopped(false)
    if (!selected || !['queued', 'processing'].includes(selected.job.state)) return
    let disposed = false, count = 0, inFlight = false
    const timer = window.setInterval(() => {
      if (inFlight) return
      if (++count > 120) { window.clearInterval(timer); setPollStopped(true); return }
      inFlight = true
      authorized<Version>(`${base}/versions/${selected.id}/status`).then(result => {
        if (!disposed) setSelected(result)
      }).catch(failure => { if (!disposed) { setError(message(failure)); window.clearInterval(timer); setPollStopped(true) } })
        .finally(() => { inFlight = false })
    }, 3000)
    return () => { disposed = true; window.clearInterval(timer) }
  }, [selected?.id, selected?.job.state])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  useEffect(() => { setPreview('') }, [ordinal])
  useEffect(() => () => { if (originalUrl) URL.revokeObjectURL(originalUrl) }, [originalUrl])
  useEffect(() => { if (selected) setItems(previous => previous.map(item => item.latest_version.id === selected.id ? { ...item, latest_version: selected } : item)) }, [selected])

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    const form = new FormData(event.currentTarget)
    const file = form.get('file') as File
    if (!file?.size || file.size > 50 * 1024 * 1024) { setError('Choose a non-empty PDF/TXT up to 50 MiB.'); setBusy(false); return }
    const metadata = { title: form.get('title'), issuer: form.get('issuer'), scheme: form.get('scheme') || null,
      document_type: form.get('document_type'), source_url: form.get('source_url'), language: form.get('language'),
      publication_date: form.get('publication_date') || null, effective_date: form.get('effective_date') || null,
      reuse_status: form.get('reuse_status'),
      document_id: newVersion ? selected?.document_id : null }
    try {
      const result = await authorized<{ duplicate: boolean; version: Version }>(`${base}/upload?filename=${encodeURIComponent(file.name)}`,
        { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'X-Document-Metadata': encodeURIComponent(JSON.stringify(metadata)) }, body: file, signal: AbortSignal.timeout(100000) })
      await loadList(); await choose(result.version)
      setNotice(result.duplicate ? 'Identical content and metadata already exist. Existing version returned.' : 'Upload saved. Job queued; start the separate worker to extract it.')
    } catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  async function action(operation: () => Promise<unknown>) {
    setBusy(true); setError('')
    try { await operation(); await loadList(); if (selected) setSelected(await authorized<Version>(`${base}/versions/${selected.id}/status`)) }
    catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  async function original() {
    if (!selected) return
    setBusy(true); setError('')
    try {
      const response = await authorizedResponse(`${base}/versions/${selected.id}/original`); setOriginalUrl(URL.createObjectURL(await response.blob()))
      if (selected.format === 'pdf') { const image = await authorizedResponse(`${base}/versions/${selected.id}/preview/${ordinal}`); setPreview(URL.createObjectURL(await image.blob())) }
    }
    catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  const document = items.find(item => item.id === selected?.document_id)
  return <section className="mt-8 space-y-6">
    <h2 className="text-2xl font-semibold">Document ingestion</h2>
    <p className="text-sm text-slate-600">PDF/UTF-8 TXT, up to 50 MiB. Uploads start unverified. OCR, HTML/DOCX, embeddings and answers are deferred. Virus scanning is unavailable.</p>
    <p className="rounded bg-slate-100 p-3 text-sm">Separate worker: from project root run <code>.\.venv\Scripts\python.exe backend\worker.py</code>. Jobs remain queued until it runs.</p>
    <form onSubmit={event => void upload(event)} className="space-y-4 rounded-xl border bg-white p-5">
      <h3 className="text-lg font-semibold">Upload source</h3>
      <label className="block">Source file<input name="file" type="file" accept=".pdf,.txt" required className={input} /></label>
      {(['title', 'issuer', 'scheme', 'document_type', 'source_url'] as const).map(name => <label className="block" key={name}>{({ title: 'Title', issuer: 'Ministry / issuer', scheme: 'Scheme (optional)', document_type: 'Document type', source_url: 'Claimed official source URL' })[name]}<input name={name} className={input} required={name !== 'scheme'} type={name === 'source_url' ? 'url' : 'text'} defaultValue={name === 'document_type' ? 'guidelines' : ''} maxLength={name === 'source_url' ? 1500 : name === 'title' ? 300 : 200} /></label>)}
      <label className="block">Language<select name="language" className={input}><option value="unknown">Unknown</option><option value="en">English</option><option value="hi">Hindi</option><option value="mixed">Mixed</option><option value="hinglish">Hinglish</option></select></label>
      <label className="block">Reuse rights<select name="reuse_status" className={input}><option value="local_reference_only">Local reference only (no redistribution permission)</option><option value="not_assessed">Not assessed</option><option value="permission_recorded">Permission recorded (describe evidence in verification note)</option></select></label>
      <label className="block">Publication date (leave unknown blank)<input type="date" name="publication_date" className={input} /></label>
      <label className="block">Effective date (leave unknown blank)<input type="date" name="effective_date" className={input} /></label>
      {selected && <label className="block"><input type="checkbox" checked={newVersion} onChange={event => setNewVersion(event.target.checked)} /> Add version to selected document; retain title, issuer, scheme and type</label>}
      <button disabled={busy} className={button}>{busy ? 'Working…' : 'Upload and queue'}</button>
    </form>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}{notice && <p role="status" className="rounded bg-teal-50 p-3">{notice}</p>}
    <div><h3 className="text-lg font-semibold">Documents ({total})</h3><button className="my-2 underline" onClick={() => void action(() => loadList())}>Refresh list</button>
      {!items.length && <p>No documents yet. Upload an official source to begin.</p>}
      <ul className="space-y-2">{items.map(item => <li key={item.id} className="rounded border p-3"><button className="text-left font-semibold text-teal-900 underline" onClick={() => void choose(item.latest_version).catch(failure => setError(message(failure)))}>{item.title}</button><p className="text-sm">{item.latest_version.job.state} · provenance {item.latest_version.provenance_status} · {item.archived ? 'archived' : 'active'}</p></li>)}</ul>
      <div className="mt-3 flex gap-4"><button disabled={listPage === 1} onClick={() => setListPage(listPage - 1)}>Previous documents</button><span>Page {listPage}</span><button disabled={listPage * 20 >= total} onClick={() => setListPage(listPage + 1)}>Next documents</button></div>
    </div>
    {selected && <section className="space-y-4 rounded-xl border bg-white p-5"><h3 className="text-xl font-semibold">Version inspection</h3>
      <label className="block">Version (latest 20)<select className={input} value={selected.id} onChange={event => { const value = versions.find(v => v.id === event.target.value); if (value) void choose(value) }}>{versions.map(v => <option key={v.id} value={v.id}>Version {v.version_number}: {v.original_name}</option>)}</select></label>
      <p role="status">Job: {selected.job.state} · {selected.job.progress}% · {selected.job.processed_pages}/{selected.job.total_pages} pages/sections · attempt {selected.job.attempts}/3</p>
      {selected.job.error_code && <p>Failure reason: {selected.job.error_code}</p>}
      {['partial', 'needs_ocr'].includes(selected.job.state) && <p className="rounded bg-amber-50 p-3">Incomplete extraction: low-text/scanned pages need OCR in Part 7. Digital text remains available; this version is not ready for retrieval.</p>}
      {pollStopped && <p>Automatic polling stopped. Use Refresh status.</p>}
      <button className="underline" onClick={() => void action(async () => { setSelected(await authorized<Version>(`${base}/versions/${selected.id}/status`)); setInspectionRevision(previous => previous + 1) })}>Refresh status</button>
      <p className="break-all text-sm">SHA256: {selected.checksum}</p><p className="text-sm">Extraction: {selected.extraction_revision || 'pending'} · Chunk profile: {selected.chunk_profile || 'pending'}</p>
      <p>Provenance: {selected.provenance_status} · Future retrieval eligible: {String(selected.eligible_for_future_retrieval)}</p>
      <details><summary>Source metadata</summary><pre className="overflow-auto whitespace-pre-wrap break-all text-xs">{JSON.stringify(selected.metadata_snapshot, null, 2)}</pre></details>
      <div className="flex flex-wrap gap-3"><button disabled={busy} className={button} onClick={() => void original()}>Load original preview</button>
        <button disabled={busy} className={button} onClick={() => void action(() => authorized(`${base}/versions/${selected.id}/retry`, { method: 'POST' }))}>Retry failed job</button>
        <button disabled={busy || !document} className={button} onClick={() => void action(() => authorized(`${base}/${selected.document_id}/archive`, { method: 'PATCH', body: JSON.stringify({ archived: !document?.archived }) }))}>{document?.archived ? 'Unarchive' : 'Archive'}</button></div>
      {originalUrl && <div><a href={originalUrl} download={`source.${selected.format}`} className="underline">Download authenticated original</a>{preview && <><p className="text-sm">Rendered original PDF page {ordinal}; changing source page requires Load original preview again.</p><img alt="Original PDF page preview" src={preview} className="mt-3 w-full border" /></>}{selected.format === 'txt' && <p>TXT original downloads as plain text; extracted text is below.</p>}</div>}
      {selected.provenance_status === 'unverified' && <div><label className="block">Verification note (official origin, title, rights and limitations)<textarea value={verification} onChange={event => setVerification(event.target.value)} className={input} minLength={20} maxLength={2000} /></label><button disabled={busy || verification.length < 20} className={button} onClick={() => void action(() => authorized(`${base}/versions/${selected.id}/provenance`, { method: 'PATCH', body: JSON.stringify({ status: 'verified', note: verification }) }))}>Record manual verification</button></div>}
      <h4 className="font-semibold">Extracted pages / TXT sections ({pageTotal})</h4>
      {!!pages.length && <><label className="block">Source page/section<select className={input} value={ordinal} onChange={event => { setOrdinal(Number(event.target.value)); setOffset(0) }}>{pages.map(p => <option key={p.ordinal} value={p.ordinal}>{p.pdf_page_number ? `PDF page ${p.pdf_page_number}` : `TXT section ${p.ordinal}`} · {p.character_count} characters · {p.quality_flags.join(', ')}</option>)}</select></label>
        <div className="flex gap-3"><button disabled={pageList === 1} onClick={() => { setPageList(pageList - 1); setOrdinal((pageList - 2) * 50 + 1); setOffset(0) }}>Previous source pages</button><button disabled={pageList * 50 >= pageTotal} onClick={() => { setPageList(pageList + 1); setOrdinal(pageList * 50 + 1); setOffset(0) }}>Next source pages</button></div></>}
      {text && <><p className="text-sm">Exact characters [{text.offset}, {Math.min(text.offset + 20000, text.total_characters)}) of {text.total_characters}. {text.quality_flags.join(', ')}</p><pre className="max-h-[500px] overflow-auto whitespace-pre-wrap break-words rounded bg-slate-50 p-4 text-sm">{text.text || 'No digital text. OCR pending.'}</pre><div className="flex gap-4"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20000))}>Previous text</button><button disabled={offset + 20000 >= text.total_characters} onClick={() => setOffset(offset + 20000)}>Next text</button></div><details><summary>Detected paragraph spans</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(text.paragraphs, null, 2)}</pre></details></>}
    </section>}
  </section>
}
