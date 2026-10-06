"""Pure frozen-set validation and disclosure-safe aggregation."""
import hashlib
import json
import re
import statistics
from collections import Counter
from pathlib import Path


def load_frozen(root, set_name='evaluation_set_v1'):
    if set_name not in ('evaluation_set_v1', 'evaluation_installment_controls_v1'):
        raise ValueError('Unknown evaluation set')
    path = root / ('docs/'+set_name+'.json')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != (root / ('docs/'+set_name+'.sha256')).read_text().strip():
        raise ValueError('Frozen evaluation checksum mismatch')
    dataset = json.loads(path.read_text(encoding='utf-8'))
    ids = [c['id'] for c in dataset['cases']]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate case ID')
    development = []
    for filename, expected in dataset['development_files'].items():
        p = (root / filename).resolve()
        # Frozen development hashes were captured on Windows. Git may normalize
        # line endings; accept only the identical content with that transformation.
        raw = p.read_bytes()
        windows_bytes = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        if p.parent != (root / 'docs').resolve() or expected not in {hashlib.sha256(b).hexdigest() for b in (raw, windows_bytes)}:
            raise ValueError('Development baseline changed')
        development += [c['question'] for c in json.loads(p.read_text('utf-8'))['cases'] if 'question' in c]
    normalize = lambda q: re.sub(r'\W+', ' ', q.lower()).strip()
    old = {normalize(q) for q in development}
    questions = [normalize(c['question']) for c in dataset['cases'] if c['mode'] == 'pipeline']
    if len(set(questions)) != len(questions) or set(questions) & old:
        raise ValueError('Copied or duplicate evaluation question')
    return dataset, digest


def gold_hit(items, gold, source_version, k):
    return any(p['version_id'] == source_version and p['pdf_page_number'] == gold['page']
               and p['start_offset'] <= gold['start'] and p['end_offset'] >= gold['end'] for p in items[:k])


def aggregate(rows):
    report = {}
    for language in ('en', 'hi', 'hinglish'):
        selected = [r for r in rows if r['mode'] == 'pipeline' and r['input_language'] == language]
        relevant = [r for r in selected if r['kind'] == 'answerable']
        latency = {}
        for category in ('cold_llm', 'warm_llm', 'no_generation', 'unknown_error'):
            samples = [r['wall_ms'] for r in selected if r['latency_category'] == category]
            latency[category] = {'sample_count': len(samples), 'median_ms': statistics.median(samples) if samples else None,
                                 'min_ms': min(samples) if samples else None, 'max_ms': max(samples) if samples else None}
        report[language] = {
            'cases': len(selected), 'behavior_matches': sum(r['behavior_match'] for r in selected),
            'outcomes': dict(Counter(r['status'] for r in selected)),
            'retrieval_denominator': len(relevant),
            'gold_hit_at_k': {str(k): sum(r.get('hits', {}).get(str(k), False) for r in relevant) for k in (1, 3, 5)},
            'retrieval_unavailable_cases': sum(r.get('retrieval_available') is not True for r in relevant),
            'candidate_claims': sum(r['candidate_count'] or 0 for r in selected),
            'accepted_candidates': sum(r['accepted_count'] or 0 for r in selected),
            'candidate_count_unavailable_cases': sum(r['candidate_count'] is None for r in selected),
            'valid_citations': sum(r['valid_citations'] for r in selected),
            'citation_attempts': sum(r['citation_attempts'] for r in selected),
            'deterministic_decisions': sum(r['deterministic_decisions'] for r in selected),
            'same_model_decisions': sum(r['same_model_decisions'] for r in selected),
            'independent_semantic_labels': 0, 'semantic_accuracy': None, 'latency': latency}
    probes = [r for r in rows if r['mode'] == 'probe']
    return {'pipeline': report, 'guard_probes': {'cases': len(probes), 'expected_rejections': sum(r['behavior_match'] for r in probes),
            'label_origin': 'Agent-authored negative controls sharing development failure classes; not held-out accuracy'}}


def public_rows(rows):
    # Explicit allowlist: never serialize raw prompts, output, source text or private UUIDs.
    fields = ('id', 'mode', 'input_language', 'kind', 'status', 'error', 'behavior_match', 'hits',
              'retrieval_available', 'candidate_count', 'accepted_count', 'valid_citations', 'citation_attempts',
              'deterministic_decisions', 'same_model_decisions', 'wall_ms', 'latency_category')
    return [{k: r[k] for k in fields if k in r} for r in rows]
