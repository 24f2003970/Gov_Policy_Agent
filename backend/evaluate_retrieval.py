"""Read-only development checks against eligible real corpus; no synthetic corpus substitution."""
import json
import statistics
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from filelock import FileLock
from app.config import ROOT, Settings
from app.database import make_engine
from app.document_models import DocumentVersion, ExtractedPage
from app.vector_index import Runtime


def evaluate(runtime, engine):
    dev=json.loads((ROOT/'docs/retrieval_devset.json').read_text('utf-8'))
    with Session(engine) as db:
        version=db.scalar(select(DocumentVersion).where(DocumentVersion.checksum==dev['source_sha256']))
        if not version: raise ValueError('eligible_real_source_missing')
        from app.eligibility import eligibility
        if not eligibility(db,version)['eligible']: raise ValueError('real_source_ineligible')
        gold={}
        for case in dev['cases']:
            if case['kind']=='grounded':
                page=db.scalar(select(ExtractedPage).where(ExtractedPage.version_id==version.id,
                    ExtractedPage.pdf_page_number==case['expected_page']))
                offset=page.text.index(case['anchor'])
                gold[case['id']]=(offset,offset+len(case['anchor']))
        version_id=str(version.id)
    results=[]
    for case in dev['cases']:
        response=runtime.search(case['question'],count=5)
        if response['status']=='unavailable':raise ValueError('real_index_unavailable')
        items=response['items']; hit=None
        if case['kind']=='grounded':
            start,end=gold[case['id']]
            hit=any(p['version_id']==version_id and p['pdf_page_number']==case['expected_page'] and
                p['start_offset']<=start and p['end_offset']>=end for p in items)
        results.append({'id':case['id'],'language':case['language'],'kind':case['kind'],'hit_at_5':hit,
            'status':response['status'],'returned':len(items),'top_pages':[p['pdf_page_number'] for p in items],
            'top_similarity':items[0]['cosine_similarity'] if items else None,'timings_ms':response.get('timings_ms')})
    aggregate={}
    for language in ['en','hi']:
        rows=[r for r in results if r['language']==language and r['kind']=='grounded']
        aggregate[language]={'hits':sum(r['hit_at_5'] for r in rows),'denominator':len(rows),
            'median_total_ms':statistics.median(r['timings_ms']['total'] for r in rows)}
    return {'review_status':dev['review_status'],'metric':'Gold span hit@5 over four source-checked questions per language; not P@5',
        'aggregate':aggregate,'results':results}


if __name__=='__main__':
    settings=Settings();engine=make_engine(settings)
    directory=settings.data_dir.parent/'vectors';directory.mkdir(parents=True,exist_ok=True)
    with FileLock(str(directory/'owner.lock'),timeout=0):
        import time,ctypes
        begin=time.perf_counter();runtime=Runtime(settings,engine);loaded=time.perf_counter()
        result=evaluate(runtime,engine)
        class Memory(ctypes.Structure):
            _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in
                ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                 'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        memory=Memory();memory.cb=ctypes.sizeof(memory)
        process=ctypes.windll.kernel32.GetCurrentProcess
        process.restype=ctypes.c_void_p
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),ctypes.c_ulong]
        ctypes.windll.psapi.GetProcessMemoryInfo(process(),ctypes.byref(memory),memory.cb)
        result['resources']={'device':'cpu','torch_threads':2,'model_runtime_load_seconds':round(loaded-begin,3),
            'process_working_set_mib':round(memory.WorkingSetSize/1024**2,1),'process_peak_working_set_mib':round(memory.PeakWorkingSetSize/1024**2,1),
            'gpu_inference':'not measured; CPU-only torch stack'}
        output=ROOT/'runtime/retrieval-results.json';output.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        print(json.dumps(result,ensure_ascii=True,indent=2))
