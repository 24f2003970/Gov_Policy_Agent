"""Read-only paired real E5/Qwen comparison. Stop index.py/rag.py owners first."""
import ast
import argparse
import asyncio
import json
import subprocess
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from filelock import FileLock
from app.config import Settings,ROOT
from app.database import make_engine
from app.document_models import DocumentVersion,ExtractedPage
from app.vector_index import Runtime
from app.rag_engine import LocalGenerator,pipeline
from app.support import SupportVerifier
from app.ollama_local import OllamaHost
from app import grounding,language
from app import rag_engine
from types import MethodType


class DirectRetriever:
    def __init__(self,runtime,changed):self.runtime,self.changed=runtime,changed
    async def retrieve(self,question,filters):return self.runtime.search(question,normalize_query=self.changed,**filters)


async def evaluate(settings,engine,runtime,changed_only=False,ids=None):
    dev=json.loads((ROOT/'docs/language_devset.json').read_text('utf-8'))
    generator=LocalGenerator(settings);verifier=SupportVerifier(engine,generator)
    source=subprocess.check_output(['git','show','31f64fdbfdbb7696f3fcc656634dc8588f0ad59d:backend/app/grounding.py'],cwd=ROOT).decode('utf-8')
    baseline=next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM' for t in n.targets))
    current,normalizer=grounding.SYSTEM,language.normalize
    baseline_ns={**grounding.__dict__,'SYSTEM':baseline}
    functions=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('raw_prompt','precheck','quote_options')]
    exec(compile(ast.Module(body=functions,type_ignores=[]),'part6-grounding-baseline','exec'),baseline_ns)
    engine_source=subprocess.check_output(['git','show','31f64fdbfdbb7696f3fcc656634dc8588f0ad59d:backend/app/rag_engine.py'],cwd=ROOT).decode('utf-8')
    nodes=ast.parse(engine_source).body
    baseline_engine={**rag_engine.__dict__,'precheck':baseline_ns['precheck'],'raw_prompt':baseline_ns['raw_prompt']}
    old_pipeline=next(n for n in nodes if isinstance(n,ast.AsyncFunctionDef) and n.name=='pipeline')
    old_budget=next(m for n in nodes if isinstance(n,ast.ClassDef) and n.name=='LocalGenerator' for m in n.body if isinstance(m,ast.FunctionDef) and m.name=='budget')
    exec(compile(ast.Module(body=[old_pipeline,old_budget],type_ignores=[]),'part6-pipeline-baseline','exec'),baseline_engine)
    current_budget=generator.budget
    with Session(engine) as db:
        version=db.scalar(select(DocumentVersion).where(DocumentVersion.checksum==dev['source_sha256']))
        if not version:raise RuntimeError('Reviewed real source missing')
        gold={}
        for c in dev['cases']:
            if c['kind']=='grounded':
                page=db.scalar(select(ExtractedPage).where(ExtractedPage.version_id==version.id,ExtractedPage.ordinal==c['expected_page']))
                start=page.text.index(c['anchor']);gold[c['id']]=(str(version.id),start,start+len(c['anchor']))
    rows=[r for r in json.loads((ROOT/'runtime/language-results.json').read_text('utf-8')) if r['variant']=='baseline' or (ids and r['id'] not in ids)] if changed_only else []
    try:
        for c in dev['cases']:
            if ids and c['id'] not in ids:continue
            for changed in ((True,) if changed_only else (False,True)):
                generator.budget=current_budget if changed else MethodType(baseline_engine['budget'],generator)
                retriever=DirectRetriever(runtime,changed)
                response=await retriever.retrieve(c['question'],{})
                hit=None;rank=None
                if c['id'] in gold:
                    v,start,end=gold[c['id']]
                    hit=any(p['version_id']==v and p['pdf_page_number']==c['expected_page'] and p['start_offset']<=start and p['end_offset']>=end for p in response['items'])
                    rank=next((i for i,p in enumerate(response['items'],1) if p['version_id']==v and p['pdf_page_number']==c['expected_page'] and p['start_offset']<=start and p['end_offset']>=end),None)
                try:
                    runner=pipeline if changed else baseline_engine['pipeline']
                    result,passages,generation,timings=await runner(c['question'],c['language'],{},retriever,generator,verifier)
                    status=result['status'];error=None
                except grounding.RagError as exc:result=None;timings={};status='error';error=exc.code
                rows.append({'id':c['id'],'variant':'changed' if changed else 'baseline','kind':c['kind'],
                    'expected':c['expected_status'],'hit_at_5':hit,'rank':rank,'status':status,'error':error,
                    'result':result,'normalization':response.get('query_normalization'),'timings':timings})
                print(c['id'],rows[-1]['variant'],status,'hit',hit,flush=True)
                (ROOT/'runtime/language-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    finally:grounding.SYSTEM=current;language.normalize=normalizer
    for variant in ('baseline','changed'):
        selected=[r for r in rows if r['variant']==variant];grounded=[r for r in selected if r['kind']=='grounded']
        print(variant,'grounded retrieval hits',sum(r['hit_at_5'] for r in grounded),'/',len(grounded),
            'retained answers',sum(r['status'] in ('answered','partial') for r in grounded),'/',len(grounded),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--changed-only',action='store_true');parser.add_argument('--ids',nargs='+');args=parser.parse_args()
    settings=Settings();engine=make_engine(settings)
    root=settings.data_dir.parent
    with FileLock(str(root/'vectors/owner.lock'),timeout=0),FileLock(str(root/'ollama/owner.lock'),timeout=0):
        runtime=Runtime(settings,engine)
        with OllamaHost(settings):asyncio.run(evaluate(settings,engine,runtime,args.changed_only,args.ids))
    engine.dispose()
