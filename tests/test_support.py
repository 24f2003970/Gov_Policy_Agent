"""Isolated support checks: negative facts must not reach final answers."""
import asyncio
import json
import pytest
from app.grounding import RagError
from app.grounding import numbers
from app.support import SupportVerifier,guard,money_relations


def cite(quote,context=None,**metadata):
    return {'id':'p1','quote':quote,'context':context or quote,'metadata':{
        'publication_date':'2025-08-01','scheme_id':'synthetic',
        'review':{'applicability':'historical'},**metadata}}


@pytest.mark.parametrize('claim,reason',[
    ('Farmers receive Rs 9,000 per year.','amount_or_frequency'),
    ('Farmers receive Rs 6,000 monthly.','amount_or_frequency'),
    ('Farmers receive Rs 6,000 per instalment.','amount_or_frequency'),
    ('किसानों को ६,००० रुपये प्रति माह मिलते हैं।','amount_or_frequency'),
    ('All farmers receive Rs 6,000 per year.','scope_mismatch'),
    ('भूमिहीन किसानों को ६,००० रुपये सालाना मिलते हैं।','scope_mismatch'),
    ('Currently farmers receive Rs 6,000 per year.','temporal_scope'),
    ('Farmers receive USD 6,000 per year.','amount_or_frequency'),
])
def test_amount_frequency_scope_and_time(claim,reason):
    c=cite('All land-holding farmer families receive financial benefit of Rs 6,000 per year in three equal instalments.')
    assert guard(claim,[c])==('unsupported',reason)


def test_indian_numbers_relations_and_no_word_suffix_currency():
    assert money_relations('₹२०,५०० करोड़ annually')==[('2.05E+11','INR','annual')]
    assert money_relations('₹3.69 lakh crore')==[('3.69E+12','INR',None)]
    assert numbers('₹३.६९ लाख करोड़')=={'3690000000000'}
    assert money_relations('farmers 2025 report')==[]
    assert numbers('दस्तावेज़ के अनुसार सालाना ६,००० रुपये तीन किस्तों में')=={'6000','3'}
    assert guard('किसानों को ६,००० रुपये सालाना मिलते हैं।',[cite('Rs 6,000 per year')]) is None


def test_negation_objective_conditions_and_conflicts():
    c=cite('The financial benefit is transferred into the Aadhaar seeded bank accounts of farmers through Direct Benefit Transfer (DBT) mode.')
    assert guard('भूमिधारक किसानों की सहायता अधिकारी के खाते में ट्रांसफर की जाती है।',[c])[1]=='scope_mismatch'
    assert guard('Farmers receive assistance through digital benefit.',[c])[1]=='scope_mismatch'
    assert guard('Farmers receive Rs 6,000 annually.',[cite('Land-holding farmers receive Rs 6,000 per year.')])[1]=='condition_omitted'
    assert guard('OTP is mandatory for eKYC.',[cite('Face authentication completes eKYC without OTP or fingerprint.')])[1]=='negation_reversal'
    c=cite('To protect Small and Marginal Farmers (SMFs) from falling in the clutches of moneylenders.')
    assert guard('Farmers are protected from moneylenders.',[c])[1]=='condition_omitted'
    assert guard('Small and marginal farmers have been protected from moneylenders.',[c])[1]=='temporal_scope'
    c=cite('Financial benefit of Rs 6,000 per year.')
    assert guard('Rs 6,000 per year.',[c],[c,cite('Financial benefit of Rs 9,000 per year.')])[0]=='conflicting'
    assert guard('Rs 6,000 per year.',[c],[c,cite('Financial benefit of Rs 9,000 per year.',scheme_id='other')]) is None


class Judge:
    def __init__(self,raw=None,error=None):self.raw=raw;self.error=error;self.calls=0
    def judge_budget(self,*args):
        if self.error=='budget':raise RagError('verification_context_limit')
        return 'isolated',10
    async def judge(self,*args):
        self.calls+=1
        if self.error:raise RagError(self.error)
        return self.raw,{'eval_count':20}


@pytest.mark.parametrize('raw',[
    'invalid JSON',
    json.dumps({'outcome':'supported_by_check','reason':'direct_support','evidence_ids':['invented']}),
    json.dumps({'outcome':'supported_by_check','reason':'direct_support','evidence_ids':['p1'],'confidence':0.99}),
    json.dumps({'outcome':'unsupported','reason':'direct_support','evidence_ids':['p1']}),
])
def test_invalid_judge_fails_closed(raw):
    with pytest.raises(RagError,match='verification_invalid_output'):
        asyncio.run(SupportVerifier(None,Judge(raw)).check('A description of farmers.',[cite('A description of farmers.')]))


def test_budget_incomplete_ids_and_unavailable_are_not_supported():
    j=Judge(error='budget')
    assert asyncio.run(SupportVerifier(None,j).check('Farmers.',[cite('Farmers.')]))['outcome']=='insufficient_context'
    assert j.calls==0
    j=Judge(json.dumps({'outcome':'supported_by_check','reason':'direct_support','evidence_ids':[]}))
    assert asyncio.run(SupportVerifier(None,j).check('Farmers.',[cite('Farmers.')]))['reason_code']=='evidence_not_addressed'
    for error,expected in [('generation_timeout','verification_timeout'),('ollama_unavailable','verification_unavailable')]:
        with pytest.raises(RagError,match=expected):asyncio.run(SupportVerifier(None,Judge(error=error)).check('Farmers.',[cite('Farmers.')]))
    with pytest.raises(RagError,match='verification_unavailable'):
        asyncio.run(SupportVerifier(None,object()).check('Farmers.',[cite('Farmers.')]))


def test_heuristic_label_and_metrics_do_not_claim_independence():
    j=Judge(json.dumps({'outcome':'supported_by_check','reason':'direct_support','evidence_ids':['p1']}))
    result=asyncio.run(SupportVerifier(None,j).check('Farmers.',[cite('Farmers.')]))
    assert result['outcome']=='supported_by_check' and result['judge_called']
    assert result['independent_verification'] is False and result['metrics']['eval_count']==20
