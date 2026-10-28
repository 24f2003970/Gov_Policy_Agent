from app.language import normalize
from app.vector_index import Runtime, _terms


def test_lexical_retrieval_keeps_exact_policy_terms_for_mixed_language_question():
    question='According to PIB factsheet what one-time grant was planned for interns after joining?'
    passage='The one-time grant to interns after joining the internship will be paid through DBT.'
    assert len(_terms(question) & _terms(passage)) >= 4


def test_deterministic_hinglish_query_fuses_original_and_normalized_results():
    question=('12 October 2024 ki PIB factsheet ke anusaar, internship join karne ke baad '
        'interns ko kaunsa one-time grant dene ki baat thi?')
    normalized=normalize(question)['retrieval_question']
    original_ids=['page-1','page-2','page-4','page-3-links','page-2-eligibility']
    normalized_ids=['page-1','page-4','page-2','page-3-links','page-3-grant']

    def items(ids,scores):
        return [{'chunk_id':chunk_id,'cosine_similarity':score,'text':chunk_id}
            for chunk_id,score in zip(ids,scores)]

    original={'status':'results','items':items(original_ids,[.90,.89,.88,.87,.82])}
    rewritten={'status':'results','items':items(normalized_ids,[.89,.88,.87,.86,.84])}
    runtime=Runtime.__new__(Runtime)
    runtime.baseline_search=lambda query,count=5,**filters: original if query==question else rewritten

    result=runtime.search(question,count=5)

    assert result['query_normalization']['selection']=='rank_fusion'
    assert result['query_normalization']['retrieval_question']==normalized
    assert result['items'][-1]['chunk_id']=='page-3-grant'
    assert len(result['items'])==5
