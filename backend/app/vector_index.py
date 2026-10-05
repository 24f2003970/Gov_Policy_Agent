"""Single-owner Chroma runtime; SQL controls eligibility and active generations."""
from datetime import timedelta
import json
import time
from uuid import uuid4, uuid5, UUID
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from .auth import now
from .document_models import Document, DocumentVersion, ExtractedPage, Scheme
from .eligibility import eligibility, source_snapshot
from .embedding import SPEC, Encoder
from .index_models import IndexGeneration, IndexPassage, IndexState

LEASE_SECONDS = 180
MAX_PASSAGES = 20_000


def queue(db):
    db.execute(text('SELECT pg_advisory_xact_lock(28041)'))
    pending = db.scalar(select(IndexGeneration).where(IndexGeneration.state.in_(['queued', 'processing'])).limit(1))
    if pending: return pending
    sources = source_snapshot(db)
    versions = [{'id': str(v.id), 'review_id': e['review_id'], 'checksum': v.checksum,
                 'extraction_revision': v.extraction_revision} for v, e in sources if e['eligible']]
    generation = IndexGeneration(spec=SPEC, versions=versions)
    db.add(generation); db.commit()
    return generation


def status(db):
    sources = source_snapshot(db)
    pointer = db.get(IndexState, 1)
    active = db.get(IndexGeneration, pointer.active_id) if pointer and pointer.active_id else None
    latest = db.scalar(select(IndexGeneration).order_by(IndexGeneration.created_at.desc()).limit(1))
    return {'active_generation': str(active.id) if active else None,
        'state': active.state if active else 'unavailable', 'model': SPEC,
        'latest_job': {'id': str(latest.id), 'state': latest.state, 'attempts': latest.attempts,
                       'processed': latest.processed, 'total': latest.total, 'error_code': latest.error_code} if latest else None,
        'sources': [{'version_id': str(v.id), 'title': db.get(Document, v.document_id).title,
                    **e} for v, e in sources]}


class Runtime:
    def __init__(self, settings, engine, encoder=None, vector_dir=None):
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        self.engine = engine
        self.encoder = encoder or Encoder(settings)
        self.client = chromadb.PersistentClient(path=str(vector_dir or settings.data_dir.parent / 'vectors'),
            settings=ChromaSettings(anonymized_telemetry=False))

    def collection(self, generation, create=False):
        name = 'gov_' + generation.id.hex
        metadata = {'spec': json.dumps(SPEC, sort_keys=True), 'hnsw:space': 'cosine'}
        if generation.spec != SPEC: raise ValueError('index_model_mismatch')
        if create:
            collection = self.client.get_or_create_collection(name, metadata=metadata, embedding_function=None)
        else:
            collection = self.client.get_collection(name, embedding_function=None)
        if collection.metadata != metadata: raise ValueError('collection_model_mismatch')
        configuration = collection.configuration
        if not configuration.get('hnsw') or configuration['hnsw']['space'] != 'cosine' or configuration.get('embedding_function') is not None:
            raise ValueError('collection_model_mismatch')
        return collection

    def claim(self):
        with Session(self.engine, expire_on_commit=False) as db:
            job = db.scalar(select(IndexGeneration).where((IndexGeneration.state == 'queued') |
                ((IndexGeneration.state == 'processing') & (IndexGeneration.lease_until < now())))
                .order_by(IndexGeneration.created_at).with_for_update(skip_locked=True).limit(1))
            if not job: return None
            if job.attempts >= 3:
                job.state, job.error_code = 'failed', 'attempt_limit'
                db.commit(); return None
            job.state, job.attempts, job.lease_owner = 'processing', job.attempts + 1, uuid4()
            job.error_code = None
            job.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
            db.commit(); return job.id, job.lease_owner

    def owned(self, db, job_id, owner):
        job = db.scalar(select(IndexGeneration).where(IndexGeneration.id == job_id,
            IndexGeneration.state == 'processing', IndexGeneration.lease_owner == owner,
            IndexGeneration.lease_until > now()).with_for_update())
        if not job: raise ValueError('index_lease_lost')
        return job

    def beat(self, job_id, owner, processed):
        with Session(self.engine) as db:
            job = self.owned(db, job_id, owner)
            job.processed, job.lease_until = processed, now() + timedelta(seconds=LEASE_SECONDS)
            db.commit()

    def build(self, claimed):
        job_id, owner = claimed
        try:
            with Session(self.engine, expire_on_commit=False) as db:
                job = self.owned(db, job_id, owner)
                collection = self.collection(job, create=True)
                passages = list(db.scalars(select(IndexPassage).where(IndexPassage.generation_id == job.id)
                    .order_by(IndexPassage.id)))
                if not passages:
                    for snapshot in job.versions:
                        version = db.get(DocumentVersion, UUID(snapshot['id']))
                        if not eligibility(db, version)['eligible']: raise ValueError('source_became_ineligible')
                        pages = db.scalars(select(ExtractedPage).where(ExtractedPage.version_id == version.id)
                            .order_by(ExtractedPage.ordinal))
                        for page in pages:
                            for chunk in self.encoder.chunks(page.text):
                                pid = uuid5(job.id, f'{page.id}:{chunk["start_offset"]}:{chunk["end_offset"]}')
                                passage = IndexPassage(id=pid, generation_id=job.id, version_id=version.id,
                                                      page_id=page.id, **chunk)
                                db.add(passage); passages.append(passage)
                                if len(passages) > MAX_PASSAGES: raise ValueError('index_passage_limit')
                    job.total = len(passages)
                    db.commit()
            for start in range(0, len(passages), 8):
                batch = passages[start:start+8]
                self.beat(job_id, owner, start)
                embeddings = self.encoder.encode([p.text for p in batch])
                collection.upsert(ids=[str(p.id) for p in batch], embeddings=embeddings,
                    metadatas=[{'version_id': str(p.version_id)} for p in batch])
                self.beat(job_id, owner, start + len(batch))
            expected = {str(p.id) for p in passages}
            actual = set(collection.get(include=[])['ids'])
            if actual != expected: raise ValueError('vector_set_mismatch')
            with Session(self.engine) as db:
                job = self.owned(db, job_id, owner)
                for snapshot in job.versions:
                    v = db.get(DocumentVersion, UUID(snapshot['id']))
                    e = eligibility(db, v)
                    if (not e['eligible'] or e['review_id'] != snapshot['review_id'] or
                            v.extraction_revision != snapshot['extraction_revision']):
                        raise ValueError('source_review_changed')
                pointer = db.get(IndexState, 1)
                if not pointer: pointer = IndexState(id=1); db.add(pointer)
                pointer.active_id = job.id
                job.state, job.finished_at, job.lease_owner, job.lease_until = 'ready', now(), None, None
                db.commit()
            return True
        except Exception as exc:
            allowed = {'index_model_mismatch','collection_model_mismatch','source_became_ineligible',
                'source_review_changed','vector_set_mismatch','index_passage_limit','token_limit_no_truncation'}
            with Session(self.engine) as db:
                job = db.get(IndexGeneration, job_id)
                if job and job.state == 'processing' and job.lease_owner == owner and job.lease_until > now():
                    job.state, job.error_code = 'failed', str(exc) if str(exc) in allowed else 'index_processing_failed'
                    job.lease_owner, job.lease_until, job.finished_at = None, None, now()
                    db.commit()
            return False

    def run_once(self):
        claimed = self.claim()
        if not claimed: return False
        self.build(claimed); return True

    def reconcile(self):
        with Session(self.engine) as db:
            pointer = db.get(IndexState, 1)
            if not pointer or not pointer.active_id: return {'state': 'unavailable'}
            job = db.get(IndexGeneration, pointer.active_id)
            collection = self.collection(job)
            expected = set(str(p) for p in db.scalars(select(IndexPassage.id).where(IndexPassage.generation_id == job.id)))
            actual = set(collection.get(include=[])['ids'])
            extra, missing = actual-expected, expected-actual
            if extra: collection.delete(ids=list(extra))
            if missing:
                pointer.active_id = None
                job.state, job.error_code = 'failed', 'reconcile_missing_vectors'
                db.commit()
            return {'missing': len(missing), 'removed_stale': len(extra), 'state': 'failed' if missing else 'ready'}

    def search(self, question, count=5, scheme=None, issuer=None, document_type=None,
               published_after=None, published_before=None, unknown_dates='exclude'):
        started = time.perf_counter()
        if self.encoder.tokens(question, query=True) > 512: raise ValueError('query_token_limit')
        with Session(self.engine) as db:
            pointer = db.get(IndexState, 1)
            job = db.get(IndexGeneration, pointer.active_id) if pointer and pointer.active_id else None
            if not job or job.state != 'ready': return {'status': 'unavailable', 'items': []}
            collection = self.collection(job)
            allowed = []
            eligibility_map = {}
            for snapshot in job.versions:
                v = db.get(DocumentVersion, UUID(snapshot['id'])); e = eligibility(db, v)
                if not e['eligible'] or e['review_id'] != snapshot['review_id']: continue
                doc = db.get(Document, v.document_id)
                sch = db.get(Scheme, doc.scheme_id) if doc.scheme_id else None
                if scheme and (not sch or sch.name != scheme): continue
                if issuer and doc.issuer != issuer: continue
                if document_type and doc.document_type != document_type: continue
                if published_after or published_before:
                    if v.publication_date is None:
                        if unknown_dates == 'exclude': continue
                    elif ((published_after and v.publication_date < published_after) or
                          (published_before and v.publication_date > published_before)): continue
                allowed.append(str(v.id)); eligibility_map[str(v.id)] = e
            if not allowed: return {'status': 'empty', 'items': [], 'generation': str(job.id), 'model': SPEC}
            encode_start = time.perf_counter()
            vector = self.encoder.encode([question], query=True)
            encoded = time.perf_counter()
            n = min(collection.count(), MAX_PASSAGES)
            result = collection.query(query_embeddings=vector, n_results=n,
                where={'version_id': {'$in': allowed}}, include=['distances']) if n else {'ids':[[]], 'distances':[[]]}
            db.expire_all()  # Re-read SQL gates after model/vector work, not cached archive/review state.
            items = []
            for pid, distance in zip(result['ids'][0], result['distances'][0]):
                passage = db.get(IndexPassage, UUID(pid))
                if not passage or passage.generation_id != job.id: raise ValueError('stale_vector_reconcile_required')
                page = db.get(ExtractedPage, passage.page_id)
                if page.text[passage.start_offset:passage.end_offset] != passage.text:
                    raise ValueError('source_span_mismatch')
                version = db.get(DocumentVersion, passage.version_id)
                if str(version.id) not in allowed: continue
                current = eligibility(db, version)
                if not current['eligible'] or current['review_id'] != eligibility_map[str(version.id)]['review_id']:
                    continue
                doc = db.get(Document, version.document_id)
                # Heuristic relevance cutoff, never a truth/confidence score.
                if 1-float(distance) < 0.78: continue
                items.append({'chunk_id': str(passage.id), 'document_id': str(doc.id), 'version_id': str(version.id),
                    'title': doc.title, 'issuer': doc.issuer, 'source_url': version.source_url,
                    'page_ordinal': page.ordinal, 'pdf_page_number': page.pdf_page_number,
                    'start_offset': passage.start_offset, 'end_offset': passage.end_offset, 'text': passage.text,
                    'section_label': passage.section_label, 'continued_clause': passage.continued_clause,
                    'cosine_distance': float(distance), 'cosine_similarity': 1-float(distance),
                    'verification': eligibility_map[str(version.id)], 'publication_date': version.publication_date})
                if len(items) == count: break
            return {'status': 'results' if items else 'empty', 'question': question, 'items': items,
                'generation': str(job.id), 'model': SPEC, 'heuristic_min_similarity': 0.78,
                'notice': 'Candidate passages only; relevance is not correctness or claim support. Current applicability is not assumed.',
                'timings_ms': {'embedding': round((encoded-encode_start)*1000,2),
                               'total': round((time.perf_counter()-started)*1000,2)}}
