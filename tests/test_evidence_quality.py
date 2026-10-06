"""Evidence calculations are explicit, bounded and distinct from semantic truth."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from app.evidence_quality import assess, present, WEIGHTS


def record(text='A factual claim', retained=True, outcome='supported_by_check', **metadata):
    return {'text': text, 'retained': retained,
        'assessment': {'outcome': outcome, 'method': 'layered-qwen-v2', 'judge_revision': 'support-judge-v1', 'judge_called': True},
        'citations': [{'id': 'passage', 'start_offset': 0, 'end_offset': 20,
            'provenance': {'status': 'valid', 'method': 'sql-original-span-v1'},
            'metadata': {'document_id': 'doc', 'version_id': 'version', 'page_id': 'page',
                'issuer': 'Synthetic publisher', 'source_url': 'https://example.gov.in/policy?copy=1',
                'publication_date': '2000-01-01', 'effective_date': None,
                'review': {'applicability': 'historical_only', 'review_id': 'review'}, **metadata}}]}


def run(records=(), status='answered', state='done'):
    return SimpleNamespace(state=state, result={'status': status, 'claims': [
        {'text': r['text'], 'claim_id': str(i)} for i,r in enumerate(records) if r['retained']]},
        finished_at=datetime(2026,10,6,tzinfo=timezone.utc), model={}, evidence_quality=None)


@pytest.mark.parametrize('valid,total', [(0,1),(1,1),(1,2),(2,3)])
def test_exact_coverage_denominator_bounds_and_missing_values(valid,total):
    records=[record(str(i)) for i in range(total)]
    for r in records[valid:]:r['citations'][0]['provenance']['status']='invalid'
    a=assess(run(records),records)
    assert a['components']['citation_coverage']['value']==valid/total
    assert 0<=a['components']['citation_coverage']['value']<=1
    assert sum(WEIGHTS.values())==1 and a['available_weight_coverage']==.25
    assert all(a['components'][k]['value'] is None for k in WEIGHTS if k!='citation_coverage')
    assert a['partial_index'] is None and a['full_aggregate'] is None and a['correctness_probability'] is None


@pytest.mark.parametrize('status', ['insufficient_evidence','needs_clarification'])
def test_abstention_clarification_conflicts_attempt_counts_and_zero_denominator(status):
    records=[record(retained=False,outcome='conflicting'),record(retained=False,outcome='unsupported')]
    a=assess(run(records,status),records)
    assert a['status']==status and a['available_weight_coverage']==0
    assert all(c['value'] is None for c in a['components'].values())
    assert a['counts']=={'candidate_records':2,'retained_records':0,'rejected_records':2,
        'displayed_factual_claims':0,'conflicting_records':1}
    assert any('conflicting' in s for s in a['limitations']) and not a['source_references']


def test_retries_rejected_candidates_not_in_coverage_or_public_evidence():
    records=[record('Rejected secret candidate',False,'conflicting'),record('Final claim')]
    a=assess(run(records,'partial'),records)
    assert a['counts']['candidate_records']==2 and a['counts']['displayed_factual_claims']==1
    assert a['components']['citation_coverage']['value']==1
    assert a['components']['consistency']['evidence']['conflicting_records']==1
    assert 'Rejected secret candidate' not in str(a)
    assert a['components']['faithfulness']['value'] is None


def test_duplicate_versions_copies_and_chunks_never_establish_independent_agreement():
    records=[record('a'),record('b',version_id='second-version',source_url='https://example.gov.in/policy?copy=2'),
             record('c',document_id='copy',source_url='https://example.gov.in/policy/')]
    a=assess(run(records),records)
    evidence=a['components']['consistency']['evidence']
    assert evidence['distinct_versions']==2 and evidence['distinct_documents']==2
    assert evidence['distinct_source_urls']==1 and evidence['independent_sources'] is None
    assert a['components']['consistency']['value'] is None
    assert a['components']['recency']['value'] is None
    assert not a['components']['recency']['evidence']['upload_dates_used']


def test_old_answer_read_only_failure_cancel_pending_and_withheld_redaction():
    old=run([record()]); original=deepcopy(old.result)
    assert present(old)['status']=='not_evaluated' and old.result==original and old.evidence_quality is None
    for state,status in [('error','generation_failed'),('cancelled','cancelled'),('queued','pending')]:
        old.state=state;assert present(old)['status']==status
    records=[record()]; old=run(records);old.evidence_quality=assess(old,records)
    snapshot=deepcopy(old.evidence_quality)
    view=present(old);view['components']['citation_coverage']['value']=0
    assert old.evidence_quality==snapshot
    redacted=present(old,True)
    assert redacted['status']=='source_unavailable' and redacted['saved_snapshot']
    assert redacted['source_references']==[] and redacted['counts']=={}
    assert redacted['available_weight_coverage']==0 and all(c['value'] is None for c in redacted['components'].values())
    assert old.evidence_quality==snapshot
