"""Post-validation evidence audit, not a probability or an extra model judgment."""
from copy import deepcopy
from urllib.parse import urlsplit

METHOD = 'evidence-quality-v1'
WEIGHTS = {'recency': .20, 'citation_coverage': .25, 'faithfulness': .25,
           'consistency': .15, 'calibration': .10, 'feedback': .05}
EXPLANATIONS = {
    'recency': 'Recorded dates and applicability are shown, but publication age does not establish policy currency or historical correctness. No validated date-to-score rule exists.',
    'citation_coverage': 'Share of displayed factual claims with valid exact-source citations. Fully cited retained claims do not establish that the whole question was answered.',
    'faithfulness': 'Existing guards and the same Qwen support judge check displayed claims. This is a heuristic, overlaps citation coverage, and has no independently validated numerical accuracy scale.',
    'consistency': 'Chunks, copies and versions are not independent corroboration. Source independence and agreement have not been established; known conflicts remain visible.',
    'calibration': 'No independent held-out calibration process exists. Tuned development results are not calibration.',
    'feedback': 'No real feedback dataset or defensible aggregation exists. No neutral default is substituted.',
}


def empty(status, *, saved=False):
    return {'schema_version': 1, 'method': METHOD, 'status': status, 'saved_snapshot': saved,
        'experimental_weights': True, 'correctness_probability': None,
        'full_aggregate': None, 'partial_index': None, 'available_weight_coverage': 0,
        'aggregate_reason': 'A citation-only measurement is not a defensible multi-dimensional index. Missing values are neither zero-filled nor reweighted.',
        'components': {key: {'value': None, 'availability': 'unavailable', 'weight': weight,
            'method': METHOD + '/' + key, 'explanation': EXPLANATIONS[key], 'evidence': {}}
            for key, weight in WEIGHTS.items()},
        'limitations': ['Evidence quality has not been calibrated as a probability of correctness.'],
        'counts': {}, 'source_references': []}


def assess(run, records):
    """Only called after SQL source validation and claim persistence, in their transaction.

    Candidates count validation records, including rejected repair attempts (not unique
    propositions). Coverage denominator is final displayed factual claims, never attempts.
    References contain no claim/quote/context text or model confidence.
    """
    status = ('generation_failed' if run.state == 'error' else 'cancelled' if run.state == 'cancelled'
              else (run.result or {}).get('status', 'not_evaluated'))
    snapshot = empty(status, saved=True)
    snapshot['answer_status'] = status
    snapshot['assessed_at'] = run.finished_at.isoformat()
    snapshot['answer_model'] = {k: run.model.get(k) for k in ('digest', 'prompt_revision', 'schema_revision', 'index_generation')}
    if run.state != 'done':
        return snapshot
    claims = (run.result or {}).get('claims', [])
    retained = [r for r in records if r['retained']]
    conflicts = sum(r['assessment'].get('outcome') == 'conflicting' for r in records)
    snapshot['counts'] = {'candidate_records': len(records), 'retained_records': len(retained),
        'rejected_records': len(records) - len(retained), 'displayed_factual_claims': len(claims),
        'conflicting_records': conflicts}
    snapshot['components']['faithfulness']['evidence'] = {
        'support_methods': sorted({r['assessment']['method'] for r in records}),
        'judge_revisions': sorted({r['assessment']['judge_revision'] for r in records if r['assessment'].get('judge_revision')}),
        'judge_calls': sum(bool(r['assessment'].get('judge_called')) for r in records),
        'outcomes': {outcome: sum(r['assessment'].get('outcome') == outcome for r in records)
                     for outcome in ('supported_by_check', 'unsupported', 'conflicting', 'insufficient_context')},
        'independent_verification': False}
    if conflicts:
        snapshot['limitations'].append('Known conflicting candidate evidence was detected; it is not averaged away or independent corroboration.')
    if not claims:
        # Abstention/clarification has no factual denominator, rather than 0%/100%.
        return snapshot
    snapshot['status'] = 'assessed_limited'
    covered = 0
    for claim in claims:
        record = next((r for r in retained if r['text'] == claim['text']), None)
        citations = record['citations'] if record else []
        valid = [c for c in citations if c['provenance']['status'] == 'valid'
                 and c['provenance']['method'] == 'sql-original-span-v1']
        covered += bool(valid)
        for c in valid:
            m = c['metadata']
            snapshot['source_references'].append({
                'claim_id': claim.get('claim_id'), 'passage_id': c['id'],
                'start_offset': c['start_offset'], 'end_offset': c['end_offset'],
                **{k: deepcopy(m.get(k)) for k in ('document_id', 'version_id', 'page_id', 'pdf_page_number',
                    'issuer', 'source_url', 'publication_date', 'effective_date', 'review',
                    'index_generation', 'extraction_revision_id', 'extraction_page_id', 'extraction_method',
                    'extraction_review_id', 'extraction_review_status')},
                'provenance_method': c['provenance']['method']})
    coverage = snapshot['components']['citation_coverage']
    # No candidate audits => this was not assessed; never fabricate a new legacy score.
    if records:
        coverage.update(value=covered / len(claims), availability='available',
            evidence={'cited_factual_claims': covered, 'displayed_factual_claims': len(claims),
                      'formula': 'cited_factual_claims / displayed_factual_claims'})
        snapshot['available_weight_coverage'] = WEIGHTS['citation_coverage']
    refs = snapshot['source_references']
    dates = [{k: r[k] for k in ('version_id', 'publication_date', 'effective_date', 'review')} for r in refs]
    # Counts are descriptive only: even distinct publishers may repeat the same source.
    origins = set()
    for r in refs:
        url = urlsplit(r['source_url'] or '')
        origins.add((url.netloc.lower(), url.path.rstrip('/')))
    snapshot['components']['recency']['evidence'] = {'recorded_source_dates': dates, 'upload_dates_used': False}
    snapshot['components']['consistency']['evidence'] = {
        'distinct_documents': len({r['document_id'] for r in refs}),
        'distinct_versions': len({r['version_id'] for r in refs}), 'distinct_source_urls': len(origins),
        'independent_sources': None, 'conflicting_records': conflicts,
        'method': 'descriptive-reference-counts-v1; no independence inference'}
    snapshot['limitations'].append('Recorded publication/effective dates and review scope do not establish current entitlement. An older historical source is not penalized for age.')
    return snapshot


def present(run, withheld=False):
    """Read-only presentation; never re-assess old snapshots, never reveal revoked scores."""
    if withheld:
        result = empty('source_unavailable', saved=run.evidence_quality is not None)
        result['aggregate_reason'] = 'Current source access changed. Saved historical assessment is preserved privately; values and evidence are withheld.'
        return result
    if run.evidence_quality is not None:
        return deepcopy(run.evidence_quality)
    status = ('pending' if run.state in ('queued', 'processing') else
              'generation_failed' if run.state == 'error' else 'cancelled' if run.state == 'cancelled' else 'not_evaluated')
    return empty(status)
