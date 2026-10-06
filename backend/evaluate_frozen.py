"""Frozen agent-authored evaluation. No application answer/vote/bookmark writes."""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from uuid import UUID
import httpx
from filelock import FileLock
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session
from evaluation import load_frozen, gold_hit, aggregate, public_rows
from app.config import ROOT, Settings
from app.database import make_engine
from app.document_models import DocumentVersion, ExtractedPage
from app.index_models import IndexPassage, IndexState
from app.eligibility import eligibility
from app.grounding import Evidence, RagError, expand_model_output, quote_options, PROMPT_REVISION
from app.citations import context_for
from app.rag_engine import LocalGenerator, LocalRetriever, pipeline
from app.support import SupportVerifier, METHOD
from app.ollama_local import OllamaHost, URL


def select_only(conn, cursor, statement, parameters, context, executemany):
    if not statement.lstrip().lower().startswith('select'):
        raise RuntimeError('Evaluation database writes are forbidden')


def preserved_hashes(engine):
    # Private hashes only; source and answer contents never printed or publicly exported.
    tables = ('answer_runs', 'answer_claims', 'claim_citations', 'saved_answers', 'answer_feedback',
              'users', 'documents', 'document_versions', 'eligibility_reviews', 'extraction_reviews')
    with engine.connect() as conn:
        return {name: hashlib.sha256(json.dumps(sorted(conn.execute(text('SELECT row_to_json(t)::text FROM '+name+' t')).scalars()),
                         ensure_ascii=False).encode()).hexdigest() for name in tables}


class RecordedRetriever(LocalRetriever):
    async def retrieve(self, question, filters):
        self.response = await super().retrieve(question, filters)
        return self.response


async def probe(case, engine, version, verifier):
    with Session(engine) as db:
        g = case['gold']
        page = db.scalar(select(ExtractedPage).where(ExtractedPage.version_id == version,
                                                     ExtractedPage.ordinal == g['ordinal']))
        passage = db.scalar(select(IndexPassage).where(IndexPassage.generation_id == db.get(IndexState, 1).active_id,
                   IndexPassage.page_id == page.id, IndexPassage.start_offset <= g['start'], IndexPassage.end_offset >= g['end']))
        if passage is None: raise RuntimeError('Probe gold not indexed')
        review = eligibility(db, db.get(DocumentVersion, version))
        evidence = Evidence(id=str(passage.id), quote=passage.text, quote_start_offset=passage.start_offset, quote_end_offset=passage.end_offset)
        if case['mutation'] == 'fabricated_quote': evidence.quote += ' Synthetic fabricated material.'
        if case['mutation'] == 'invented_id': evidence.id = '00000000-0000-0000-0000-000000000000'
        citation = context_for(db, evidence, {'verification': {'review_id': review['review_id'], 'applicability': review['applicability']}})
    if case['mutation'] == 'wrong_language':
        p = {'chunk_id': str(passage.id), 'text': passage.text, 'start_offset': passage.start_offset}
        choice = next(iter(quote_options(p)))
        raw = json.dumps({'status': 'answered', 'language': 'en', 'claims': [{'text': 'The scheme provides annual financial assistance to land-holding farmers.',
                          'evidence': [{'id': p['chunk_id'], 'quote_id': choice}]}], 'limitations': []})
        expand_model_output(raw, 'hi', [p])
        return {'outcome': 'supported_by_check', 'judge_called': False}
    available = None
    if case['mutation'] == 'conflict':
        other = deepcopy(citation); other['id'] = 'isolated-conflicting-probe'
        other['quote'] = other['context'] = 'Financial benefit of Rs 12,000 per year.'
        available = [citation, other]
    return await verifier.check(case['claim'], [citation], available)


async def run(dataset, digest, destination, settings, engine, host):
    before = preserved_hashes(engine)
    with Session(engine) as db:
        assert db.scalar(text("SELECT count(*) FROM answer_runs WHERE state IN ('queued','processing')")) == 0, 'Stop only an idle RAG worker'
        v = db.scalar(select(DocumentVersion).where(DocumentVersion.checksum == dataset['source_sha256']))
        if v is None or v.version_number != dataset['source_version_number'] or not eligibility(db, v)['eligible']:
            raise RuntimeError('Reviewed source/version unavailable')
        version = v.id
        for c in dataset['cases']:
            g = c.get('gold')
            if not g: continue
            page = db.scalar(select(ExtractedPage).where(ExtractedPage.version_id == version, ExtractedPage.ordinal == g['ordinal']))
            if page is None or page.pdf_page_number != g['page'] or hashlib.sha256(page.text[g['start']:g['end']].encode()).hexdigest() != g['text_sha256']:
                raise RuntimeError('Frozen gold span changed')
    generator = LocalGenerator(settings); verifier = SupportVerifier(engine, generator)
    retriever = RecordedRetriever(settings); rows = []
    metadata = {'set_version': dataset['version'], 'set_sha256': digest, 'started_at': datetime.now(timezone.utc).isoformat(),
                'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'model': generator.manifest, 'prompt_revision': PROMPT_REVISION, 'support_method': METHOD,
                'label_status': dataset['label_status'], 'index_state': 'Existing warm index service; fresh owned LLM process',
                'independent_human_labels': 0, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'evaluation_helpers_sha256': hashlib.sha256((ROOT/'backend/evaluation.py').read_bytes()).hexdigest()}
    for case in dataset['cases']:
        row = {k: case[k] for k in ('id', 'mode', 'input_language', 'kind')}
        row.update(error=None, behavior_match=False, candidate_count=None, accepted_count=None,
                   valid_citations=0, citation_attempts=0, deterministic_decisions=0, same_model_decisions=0)
        async with httpx.AsyncClient(trust_env=False, timeout=3) as client:
            loaded = bool((await client.get(URL+'/api/ps')).json()['models'])
        start = time.perf_counter(); result = None; checks = []; retriever.response = None
        try:
            if case['mode'] == 'probe':
                check = await probe(case, engine, version, verifier)
                row.update(status=check['outcome'], behavior_match=check['outcome'] != 'supported_by_check')
                row['probe_check'] = check
            else:
                result, sources, generation, timings = await asyncio.wait_for(pipeline(case['question'], case['response_language'], {},
                                                            retriever, generator, verifier), timeout=120)
                checks = result.get('_claim_checks', [])
                row.update(status=result['status'], behavior_match=result['status'] in case['expected_status'],
                           candidate_count=len(checks), accepted_count=sum(c['retained'] for c in checks),
                           deterministic_decisions=sum(not c['assessment']['judge_called'] for c in checks),
                           same_model_decisions=sum(c['assessment']['judge_called'] for c in checks), result=result, timings=timings)
                with Session(engine) as db:
                    for claim in result['claims']:
                        for e in claim['evidence']:
                            row['citation_attempts'] += 1
                            try: context_for(db, Evidence.model_validate(e), next(p for p in sources if p['chunk_id'] == e['id'])); row['valid_citations'] += 1
                            except RagError: pass
        except (RagError, asyncio.TimeoutError) as exc:
            row.update(status='error', error=exc.code if isinstance(exc, RagError) else 'evaluation_deadline')
            if case['mode'] == 'probe': row['behavior_match'] = isinstance(exc, RagError) and exc.code in ('citation_provenance_invalid', 'response_language_mismatch')
        if row['error'] in ('evaluation_deadline','generation_timeout','verification_timeout','ollama_unavailable','verification_unavailable'): host.restart()
        row['wall_ms'] = round((time.perf_counter()-start)*1000, 2)
        invoked = bool(row.get('timings', {}).get('generation_attempts')) or row['same_model_decisions'] > 0
        # Errors may occur after inference; unknown timing stays separate rather than inventing a warm sample.
        row['latency_category'] = ('warm_llm' if loaded else 'cold_llm') if invoked else 'unknown_error' if row['error'] and case['mode']=='pipeline' else 'no_generation'
        if case['mode'] == 'pipeline':
            response = retriever.response
            row['retrieval_available'] = response is not None
            row['hits'] = {str(k): gold_hit(response['items'], case['gold'], str(version), k) if response and case['gold'] else False for k in (1, 3, 5)}
        rows.append(row)
        print(case['id'], row['status'], row['error'] or '', row['wall_ms'], flush=True)
        (destination/'private.json').write_text(json.dumps({'metadata': metadata, 'rows': rows}, ensure_ascii=False, default=str, indent=2), encoding='utf-8')
    after = preserved_hashes(engine)
    if before != after: raise RuntimeError('Application records changed during evaluation; inspect concurrent activity')
    summary = {'metadata': metadata, 'application_records_unchanged': True, 'metrics': aggregate(rows), 'cases': public_rows(rows)}
    (destination/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Evaluation complete; private outputs and safe aggregate summary are under ignored runtime/evaluation/', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--set', choices=('evaluation_set_v1','evaluation_installment_controls_v1'), default='evaluation_set_v1')
    parser.add_argument('--run-id', default='baseline-v1')
    args = parser.parse_args(); dataset, digest = load_frozen(ROOT, args.set)
    if args.check: print(dataset['version'], len(dataset['cases']), digest); return
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,39}', args.run_id): raise SystemExit('Use a short lowercase run ID')
    destination = ROOT/'runtime/evaluation'/args.run_id
    destination.mkdir(parents=True, exist_ok=False)  # Never overwrite a baseline or previous outputs.
    settings = Settings(); engine = make_engine(settings)
    event.listen(engine, 'before_cursor_execute', select_only)
    try:
        with FileLock(str(settings.data_dir.parent/'ollama/owner.lock'), timeout=0), OllamaHost(settings) as host:
            asyncio.run(run(dataset, digest, destination, settings, engine, host))
    finally: engine.dispose()


if __name__ == '__main__': main()
