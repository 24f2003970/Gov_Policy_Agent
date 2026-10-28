import { useEffect, useState, type FormEvent } from 'react'
import { authorized, authorizedResponse } from './auth'
import OcrReview from './OcrReview'

type Job = { state: string; progress: number; attempts: number; processed_pages: number; total_pages: number; error_code: string | null }
type Version = { id: string; document_id: string; version_number: number; checksum: string; original_name: string; format: string;
  size_bytes: number; source_url: string; provenance_status: string; metadata_snapshot: Record<string, unknown>;
  publication_date: string | null; effective_date: string | null; original_publication_date?: string | null; original_effective_date?: string | null;
  metadata_correction?: { id: string; reason: string; evidence_url: string; created_at: string } | null;
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
  const [documentQuery, setDocumentQuery] = useState('')

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
  async function correctMetadata(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return
    const form = new FormData(event.currentTarget)
    const body = Object.fromEntries(['publication_date','effective_date','reason','evidence_url'].map(key => [key, form.get(key) || null]))
    await action(async () => {
      await authorized(`${base}/versions/${selected.id}/metadata-corrections`, { method: 'POST', body: JSON.stringify(body) })
      setSelected(await authorized<Version>(`${base}/versions/${selected.id}/status`))
      setInspectionRevision(previous => previous + 1)
      setNotice('Evidence-backed metadata correction recorded. Original upload metadata remains preserved.')
    })
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
  const counts = items.reduce((acc, item) => { const state = item.latest_version.job.state; acc[state] = (acc[state] || 0) + 1; if (item.latest_version.provenance_status !== 'verified') acc.unverified += 1; return acc }, { unverified: 0 } as Record<string, number>)
  const filteredItems = items.filter(item => `${item.title} ${item.issuer}`.toLocaleLowerCase().includes(documentQuery.trim().toLocaleLowerCase()))
  return <section className="admin-workspace">
    <header className="admin-page-heading">
      <div><p className="eyebrow">SOURCE MANAGEMENT</p><h2>Document library</h2><p>Upload official sources, track extraction, and review documents before they become searchable.</p></div>
      <span className="admin-access-pill"><i aria-hidden="true"/> Admin access active</span>
    </header>
    <div className="admin-summary-grid" aria-label="Document processing summary">
      <article><span>Documents</span><strong>{total}</strong><small>In this library</small></article>
      <article><span>Extracted</span><strong>{counts.completed || 0}</strong><small>Text extraction complete</small></article>
      <article><span>Needs review</span><strong>{(counts.partial || 0) + (counts.needs_ocr || 0)}</strong><small>OCR or page checks pending</small></article>
      <article><span>Failed</span><strong>{counts.failed || 0}</strong><small>Processing needs attention</small></article>
      <article><span>Provenance</span><strong>{counts.unverified || 0}</strong><small>Awaiting source verification</small></article>
    </div>
    <details className="admin-worker-note"><summary>Upload and processing notes</summary><p>PDF or UTF-8 TXT, maximum 50 MiB. Uploads begin unverified. Only reviewed, eligible text is available to Search and historical-source Ask. OCR pages require manual comparison with the original.</p><p>Worker command from project root: <code>.\.venv\Scripts\python.exe backend\worker.py</code>. HTML/DOCX and virus scanning are unavailable.</p></details>
    <form onSubmit={event => void upload(event)} className="admin-upload-card">
      <div className="admin-card-heading"><div><p className="eyebrow">ADD TO LIBRARY</p><h3>Upload a source</h3><p>Enter the details shown on the official document. Leave dates blank when they are unknown.</p></div><span className="admin-file-mark" aria-hidden="true">＋</span></div>
      <div className="admin-upload-grid">
        <label className="admin-file-field">PDF or TXT file<input name="file" type="file" accept=".pdf,.txt" required className={input} /></label>
        <label>Document title<input name="title" className={input} required maxLength={300} placeholder="e.g. Scheme operational guidelines" /></label>
        <label>Ministry / issuer<input name="issuer" className={input} required maxLength={200} placeholder="Department or ministry" /></label>
        <label>Scheme name <span>(optional)</span><input name="scheme" className={input} maxLength={200} placeholder="Scheme associated with this source" /></label>
        <label>Document type<input name="document_type" className={input} required maxLength={80} defaultValue="guidelines" /></label>
        <label className="admin-url-field">Official source URL<input name="source_url" className={input} required type="url" maxLength={1500} placeholder="https://..." /></label>
        <label>Document language<select name="language" className={input}><option value="unknown">Select language</option><option value="en">English</option><option value="hi">Hindi</option><option value="mixed">Hindi and English</option><option value="hinglish">Hinglish</option></select></label>
        <label>Reuse rights<select name="reuse_status" className={input}><option value="local_reference_only">Local reference only</option><option value="not_assessed">Not assessed</option><option value="permission_recorded">Permission recorded</option></select><small>Choose “Permission recorded” only when you have evidence.</small></label>
        <label>Publication date<input type="date" name="publication_date" className={input} /></label>
        <label>Effective date<input type="date" name="effective_date" className={input} /></label>
      </div>
      {selected && <label className="admin-version-toggle"><input type="checkbox" checked={newVersion} onChange={event => setNewVersion(event.target.checked)} /> Add as a new version of <strong>{document?.title || selected.metadata_snapshot.title as string}</strong></label>}
      <div className="admin-upload-footer"><span>Uploads are private to this workspace and start unverified.</span><button disabled={busy} className={button}>{busy ? 'Uploading…' : 'Upload and process'}</button></div>
    </form>
    {error && <p role="alert" className="admin-feedback admin-feedback-error">{error}</p>}{notice && <p role="status" className="admin-feedback admin-feedback-success">{notice}</p>}
    <section className="admin-documents-card">
      <div className="admin-card-heading admin-documents-heading"><div><p className="eyebrow">WORKSPACE SOURCES</p><h3>Documents <span>{total}</span></h3><p>Choose a document to inspect extraction, source details, and review actions.</p></div><div className="admin-documents-tools"><label className="admin-document-search"><span aria-hidden="true">⌕</span><input aria-label="Filter documents" value={documentQuery} onChange={event => setDocumentQuery(event.target.value)} placeholder="Filter by title or ministry" /></label><button className="admin-refresh-button" onClick={() => void action(() => loadList())}>Refresh</button></div></div>
      {!items.length && <p className="admin-empty-state">No documents yet. Upload an official source to begin.</p>}
      {!!items.length && !filteredItems.length && <p className="admin-empty-state">No documents match “{documentQuery}”.</p>}
      <ul className="admin-document-list">{filteredItems.map(item => <li key={item.id} className={selected?.document_id === item.id ? 'is-selected' : ''}><button className="admin-document-row" onClick={() => void choose(item.latest_version).catch(failure => setError(message(failure)))}><span className="admin-document-icon" aria-hidden="true">{item.latest_version.format.toUpperCase()}</span><span className="admin-document-main"><strong>{item.title}</strong><small>{item.issuer}</small></span><span className={`admin-state-badge admin-state-${item.latest_version.job.state}`}>{item.latest_version.job.state.replace('_', ' ')}</span><span className={`admin-provenance ${item.latest_version.provenance_status}`}>{item.latest_version.provenance_status === 'verified' ? 'Verified source' : 'Unverified source'}</span><span className="admin-row-arrow" aria-hidden="true">›</span></button></li>)}</ul>
      <div className="admin-pagination"><span>Page {listPage} · {total} documents</span><div><button disabled={listPage === 1} onClick={() => setListPage(listPage - 1)}>Previous</button><button disabled={listPage * 20 >= total} onClick={() => setListPage(listPage + 1)}>Next</button></div></div>
    </section>
    {selected && <section className="admin-inspection-card"><div className="admin-card-heading"><div><p className="eyebrow">DOCUMENT REVIEW</p><h3>{document?.title || selected.metadata_snapshot.title as string}</h3><p>{document?.issuer || selected.metadata_snapshot.issuer as string}</p></div><button className="admin-refresh-button" onClick={() => void action(async () => { setSelected(await authorized<Version>(`${base}/versions/${selected.id}/status`)); setInspectionRevision(previous => previous + 1) })}>Refresh status</button></div>
      <div className="admin-job-overview"><div><span>Extraction</span><strong className={`admin-state-badge admin-state-${selected.job.state}`}>{selected.job.state.replace('_', ' ')}</strong></div><div><span>Progress</span><strong>{selected.job.progress}% · {selected.job.processed_pages}/{selected.job.total_pages || '—'} pages</strong></div><div><span>Provenance</span><strong>{selected.provenance_status}</strong></div><div><span>Search eligible</span><strong>{selected.eligible_for_future_retrieval ? 'Yes' : 'Not yet'}</strong></div></div>
      {selected.job.error_code && <p className="admin-feedback admin-feedback-error">Processing stopped: {selected.job.error_code}. You can inspect the source and available recovery actions below.</p>}
      {['partial', 'needs_ocr'].includes(selected.job.state) && <p className="admin-feedback admin-feedback-warning">Some pages have little or no extractable text. Queue OCR and compare every OCR page with the original before accepting it.</p>}
      {pollStopped && <p className="admin-feedback admin-feedback-warning">Automatic status refresh stopped. Use Refresh status to check again.</p>}
      <details className="admin-advanced-details"><summary>Version, metadata and extraction details</summary>
      <label className="block">Version (latest 20)<select className={input} value={selected.id} onChange={event => { const value = versions.find(v => v.id === event.target.value); if (value) void choose(value) }}>{versions.map(v => <option key={v.id} value={v.id}>Version {v.version_number}: {v.original_name}</option>)}</select></label>
      <p className="break-all text-sm">Version reference: {selected.id}</p><p className="break-all text-sm">SHA256: {selected.checksum}</p><p className="text-sm">Extraction: {selected.extraction_revision || 'pending'} · Chunk profile: {selected.chunk_profile || 'pending'}</p>
      <p>Provenance: {selected.provenance_status} · Future retrieval eligible: {String(selected.eligible_for_future_retrieval)}</p>
      <details><summary>Source metadata</summary><pre className="overflow-auto whitespace-pre-wrap break-all text-xs">{JSON.stringify(selected.metadata_snapshot, null, 2)}</pre></details>
      <details className="rounded border p-3"><summary>Audited date correction</summary>
        <p className="my-2 text-sm">Original uploaded dates are preserved. A correction is append-only and requires source evidence; the latest correction is used in citations and date filters.</p>
        <p className="text-sm">Original publication date: {selected.original_publication_date || 'unknown'} · Current publication date: {selected.publication_date || 'unknown'}</p>
        <form onSubmit={event => void correctMetadata(event)} className="mt-3 space-y-3">
          <label className="block">Correct publication date<input type="date" name="publication_date" defaultValue={selected.publication_date || ''} className={input}/></label>
          <label className="block">Effective date (leave blank if unknown)<input type="date" name="effective_date" defaultValue={selected.effective_date || ''} className={input}/></label>
          <label className="block">Correction reason<textarea name="reason" required minLength={20} maxLength={2000} defaultValue={selected.metadata_correction?.reason || ''} className={input}/></label>
          <label className="block">Date evidence URL<input type="url" name="evidence_url" required maxLength={1500} defaultValue={selected.metadata_correction?.evidence_url || selected.source_url} className={input}/></label>
          <button disabled={busy} className={button}>Record date correction</button>
        </form>
        {selected.metadata_correction&&<p className="mt-2 text-sm">Latest correction recorded: {selected.metadata_correction.created_at}. Original metadata remains in the audit trail.</p>}
      </details>
      <div className="flex flex-wrap gap-3"><button disabled={busy} className={button} onClick={() => void original()}>Load original preview</button>
        <button disabled={busy} className={button} onClick={() => void action(() => authorized(`${base}/versions/${selected.id}/retry`, { method: 'POST' }))}>Retry failed job</button>
        <button disabled={busy || !document} className={button} onClick={() => void action(() => authorized(`${base}/${selected.document_id}/archive`, { method: 'PATCH', body: JSON.stringify({ archived: !document?.archived }) }))}>{document?.archived ? 'Unarchive' : 'Archive'}</button></div>
      {originalUrl && <div><a href={originalUrl} download={`source.${selected.format}`} className="underline">Download authenticated original</a>{preview && <><p className="text-sm">Rendered original PDF page {ordinal}; changing source page requires Load original preview again.</p><img alt="Original PDF page preview" src={preview} className="mt-3 w-full border" /></>}{selected.format === 'txt' && <p>TXT original downloads as plain text; extracted text is below.</p>}</div>}
      {selected.provenance_status === 'unverified' && <div><label className="block">Verification note (official origin, title, rights and limitations)<textarea value={verification} onChange={event => setVerification(event.target.value)} className={input} minLength={20} maxLength={2000} /></label><button disabled={busy || verification.length < 20} className={button} onClick={() => void action(() => authorized(`${base}/versions/${selected.id}/provenance`, { method: 'PATCH', body: JSON.stringify({ status: 'verified', note: verification }) }))}>Record manual verification</button></div>}
      <h4 className="font-semibold">Extracted pages / TXT sections ({pageTotal})</h4>
      {selected.format==='pdf'&&<OcrReview key={selected.id} versionId={selected.id}/>}
      {!!pages.length && <><label className="block">Source page/section<select className={input} value={ordinal} onChange={event => { setOrdinal(Number(event.target.value)); setOffset(0) }}>{pages.map(p => <option key={p.ordinal} value={p.ordinal}>{p.pdf_page_number ? `PDF page ${p.pdf_page_number}` : `TXT section ${p.ordinal}`} · {p.character_count} characters · {p.quality_flags.join(', ')}</option>)}</select></label>
        <div className="flex gap-3"><button disabled={pageList === 1} onClick={() => { setPageList(pageList - 1); setOrdinal((pageList - 2) * 50 + 1); setOffset(0) }}>Previous source pages</button><button disabled={pageList * 50 >= pageTotal} onClick={() => { setPageList(pageList + 1); setOrdinal(pageList * 50 + 1); setOffset(0) }}>Next source pages</button></div></>}
      {text && <><p className="text-sm">Exact characters [{text.offset}, {Math.min(text.offset + 20000, text.total_characters)}) of {text.total_characters}. {text.quality_flags.join(', ')}</p><pre className="max-h-[500px] overflow-auto whitespace-pre-wrap break-words rounded bg-slate-50 p-4 text-sm">{text.text || 'No digital text. OCR pending.'}</pre><div className="flex gap-4"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20000))}>Previous text</button><button disabled={offset + 20000 >= text.total_characters} onClick={() => setOffset(offset + 20000)}>Next text</button></div><details><summary>Detected paragraph spans</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(text.paragraphs, null, 2)}</pre></details></>}
      </details>
    </section>}
  </section>
}
