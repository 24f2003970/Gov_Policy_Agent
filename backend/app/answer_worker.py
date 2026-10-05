"""One bounded job at a time. Source gates run before final publication."""
import asyncio
from datetime import timedelta
import json
import time
from uuid import UUID
from sqlalchemy import select,delete
from sqlalchemy.orm import Session
from .auth import now
from .answer_models import AnswerRun,AnswerWorker
from .index_models import IndexGeneration,IndexPassage
from .document_models import Document,DocumentVersion,ExtractedPage
from .eligibility import eligibility
from .models import User
from .grounding import RagError,PROMPT_REVISION,SCHEMA_REVISION
from .rag_engine import LocalRetriever,LocalGenerator,pipeline

DEADLINE_SECONDS=120


def validate_sources(db,passages,generation):
    if passages:
        job=db.get(IndexGeneration,UUID(generation),with_for_update=True)
        if not job or job.state!='ready': raise RagError('source_status_changed')
    for p in passages:
        version=db.get(DocumentVersion,UUID(p['version_id']),with_for_update=True)
        if not version: raise RagError('source_status_changed')
        db.get(Document,version.document_id,with_for_update=True)
        e=eligibility(db,version)
        if not e['eligible'] or e['review_id']!=p['verification']['review_id']:
            raise RagError('source_status_changed')
        passage=db.get(IndexPassage,UUID(p['chunk_id']))
        page=db.get(ExtractedPage,passage.page_id) if passage else None
        if not passage or str(passage.generation_id)!=generation or str(passage.version_id)!=p['version_id'] or not page:
            raise RagError('source_span_changed')
        if passage.text!=p['text'] or page.text[p['start_offset']:p['end_offset']]!=p['text']:
            raise RagError('source_span_changed')


class Worker:
    def __init__(self,settings,engine,host,generator=None,retriever=None):
        self.engine,self.host=engine,host
        self.generator=generator or LocalGenerator(settings)
        self.retriever=retriever or LocalRetriever(settings)
        self.last_beat=0
        self.last_cleanup=0

    def heartbeat(self):
        if time.monotonic()-self.last_beat<1: return
        with Session(self.engine) as db:
            marker=db.get(AnswerWorker,1)
            if not marker: marker=AnswerWorker(id=1,heartbeat=now());db.add(marker)
            if time.monotonic()-self.last_cleanup>3600:
                db.execute(delete(AnswerRun).where(AnswerRun.created_at<now()-timedelta(days=30),AnswerRun.state.not_in(['queued','processing'])))
                self.last_cleanup=time.monotonic()
            marker.heartbeat=now();db.commit()
        self.last_beat=time.monotonic()

    def recover(self):
        with Session(self.engine) as db:
            # Only after the exclusive owner lock and a fresh contained Ollama instance.
            for run in db.scalars(select(AnswerRun).where(AnswerRun.state=='processing')):
                run.state,run.error_code,run.finished_at='error','worker_interrupted',now()
            db.execute(delete(AnswerRun).where(AnswerRun.created_at<now()-timedelta(days=30),AnswerRun.state.not_in(['queued','processing'])))
            db.commit()
        self.heartbeat()

    async def once(self):
        self.heartbeat()
        with Session(self.engine,expire_on_commit=False) as db:
            run=db.scalar(select(AnswerRun).where(AnswerRun.state=='queued').order_by(AnswerRun.created_at).with_for_update(skip_locked=True).limit(1))
            if not run: return False
            if run.created_at<now()-timedelta(seconds=DEADLINE_SECONDS):
                run.state,run.error_code,run.finished_at='error','queue_deadline_exceeded',now();db.commit();return True
            run.state='processing';db.commit()
            job_id=run.id;question,language,filters=run.question,run.language,run.filters
        start=time.perf_counter();error=None;result=None;sources=[];timings={};generation=None
        task=asyncio.create_task(pipeline(question,language,filters,self.retriever,self.generator))
        try:
            while not task.done():
                await asyncio.wait({task},timeout=0.2)
                self.heartbeat()
                with Session(self.engine) as db:
                    record=db.get(AnswerRun,job_id)
                    if record.cancel_requested: raise RagError('cancelled')
                if time.perf_counter()-start>DEADLINE_SECONDS: raise RagError('generation_timeout')
            result,sources,generation,timings=await task
            with Session(self.engine) as db: validate_sources(db,sources,generation)
        except RagError as exc: error=exc.code
        except Exception: error='answer_processing_failed'
        finally:
            if not task.done():
                task.cancel()
                try: await task
                except (asyncio.CancelledError,Exception): pass
            if error in ('cancelled','generation_timeout','ollama_unavailable'):
                # Closing the Windows job kills this project's server AND all inference children.
                self.host.restart()
        timings['worker_total_ms']=round((time.perf_counter()-start)*1000,2)
        with Session(self.engine) as db:
            record=db.get(AnswerRun,job_id,with_for_update=True)
            if record.cancel_requested: error='cancelled'
            if not db.get(User,record.user_id).active: error='owner_inactive'
            if not error:
                try: validate_sources(db,sources,generation)  # Lock source gates through publication.
                except RagError as exc: error=exc.code
                else:
                    record.result=result
                    record.sources=json.loads(json.dumps(sources,default=str))
            record.model={**self.generator.manifest,'prompt_revision':PROMPT_REVISION,'schema_revision':SCHEMA_REVISION,'index_generation':generation}
            record.timings=timings
            record.state='cancelled' if error=='cancelled' else 'error' if error else 'done'
            record.error_code=error;record.finished_at=now();db.commit()
        return True
