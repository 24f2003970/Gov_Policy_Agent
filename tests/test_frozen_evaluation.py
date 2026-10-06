from copy import deepcopy
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine, event, text
from evaluation import aggregate, gold_hit, load_frozen, public_rows
from evaluate_frozen import select_only
from app.config import ROOT


def test_frozen_integrity_and_duplicate_separation(tmp_path):
    data, digest = load_frozen(ROOT)
    assert len(data['cases']) == 30 and len(digest) == 64
    assert sum(c['mode']=='pipeline' for c in data['cases']) == 24
    controls, control_digest = load_frozen(ROOT, 'evaluation_installment_controls_v1')
    assert len(controls['cases']) == 3 and all(c['mode']=='probe' for c in controls['cases']) and len(control_digest)==64
    with pytest.raises(ValueError, match='Unknown'):load_frozen(ROOT, '../other')
    for name in ('evaluation_set_v1.json','evaluation_set_v1.sha256', 'retrieval_devset.json','language_devset.json','support_devset.json'):
        (tmp_path/'docs').mkdir(exist_ok=True)
        (tmp_path/'docs'/name).write_bytes((ROOT/'docs'/name).read_bytes())
    for name in ('retrieval_devset.json','language_devset.json','support_devset.json'):
        p=tmp_path/'docs'/name;p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
    assert load_frozen(tmp_path)[1] == digest
    (tmp_path/'docs/evaluation_set_v1.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):load_frozen(tmp_path)


def test_gold_requires_entire_exact_span_same_source_page_and_rank():
    gold={'page':2,'start':100,'end':150}
    item={'version_id':'real','pdf_page_number':2,'start_offset':90,'end_offset':150}
    assert gold_hit([item],gold,'real',1)
    assert not gold_hit([{**item,'end_offset':149}],gold,'real',5)
    assert not gold_hit([{**item,'pdf_page_number':3}],gold,'real',5)
    assert not gold_hit([item],gold,'other',5)
    assert not gold_hit([{**item,'version_id':'other'},item],gold,'real',1)
    assert gold_hit([{**item,'version_id':'other'},item],gold,'real',3)


def test_metrics_exclude_controls_and_unknown_labels_and_safe_export():
    row=dict(id='a',mode='pipeline',input_language='en',kind='answerable',status='partial',behavior_match=True,
             hits={'1':False,'3':True,'5':True},retrieval_available=True,candidate_count=2,accepted_count=1,
             valid_citations=1,citation_attempts=1,deterministic_decisions=1,same_model_decisions=1,
             latency_category='warm_llm',wall_ms=100,result={'secret':'private answer'},question='private question',sources=['private UUID'])
    error={**row,'id':'b','status':'error','behavior_match':False,'hits':{},'retrieval_available':False,
           'candidate_count':None,'accepted_count':None,'valid_citations':0,'citation_attempts':0,
           'deterministic_decisions':0,'same_model_decisions':0,'latency_category':'unknown_error','wall_ms':200}
    control={**row,'id':'probe','mode':'probe','behavior_match':True}
    rows=[row,error,control];report=aggregate(rows)['pipeline']['en']
    assert report['cases']==2 and report['retrieval_denominator']==2 and report['gold_hit_at_k']['5']==1
    assert report['candidate_claims']==2 and report['candidate_count_unavailable_cases']==1
    assert report['latency']['warm_llm']['sample_count']==1 and report['latency']['unknown_error']['sample_count']==1
    assert report['semantic_accuracy'] is None and report['independent_semantic_labels']==0
    output=json.dumps(public_rows(rows))
    assert 'private' not in output and 'result' not in output and 'question' not in output and 'sources' not in output


def test_evaluation_engine_refuses_dml():
    engine=create_engine('sqlite://')
    event.listen(engine,'before_cursor_execute',select_only)
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT 1'))==1
        for sql in ('CREATE TABLE private (x int)','DELETE FROM private','INSERT INTO private VALUES (1)','UPDATE private SET x=2'):
            with pytest.raises(RuntimeError,match='writes'):conn.execute(text(sql))
