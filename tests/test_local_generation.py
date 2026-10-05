"""Adapter failure isolation; real Ollama verification is recorded separately."""
import asyncio
import json
import httpx
import pytest
from app.rag_engine import LocalGenerator
from app.ollama_local import TAG
from app.grounding import RagError
from test_grounding import SOURCE


def generator():
    g=LocalGenerator.__new__(LocalGenerator)
    g.manifest={'digest':'pinned-test-digest','ollama_version':'test-version','temperature':0,'seed':28,
        'context_tokens':4096,'output_tokens':768}
    return g


@pytest.mark.parametrize('scenario,expected',[
    ('offline','ollama_unavailable'),('digest','llm_digest_mismatch'),('version','ollama_version_mismatch'),
    ('truncated','generation_truncated'),('tokens','llm_token_count_mismatch'),
    ('thinking','unexpected_thinking_output'),('timeout','generation_timeout'),('size','llm_response_limit')])
def test_local_adapter_rejects_failures(monkeypatch,scenario,expected):
    original=httpx.AsyncClient
    def handler(request):
        if scenario=='offline':raise httpx.ConnectError('isolated offline test',request=request)
        if scenario=='timeout':raise httpx.ReadTimeout('isolated timeout test',request=request)
        if request.url.path=='/api/version':return httpx.Response(200,json={'version':'changed' if scenario=='version' else 'test-version'})
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':TAG,'digest':'changed' if scenario=='digest' else 'pinned-test-digest'}]})
        payload=json.loads(request.content)
        assert payload['truncate'] is False and payload['shift'] is False and payload['think'] is False
        assert payload['options']['num_predict']==768
        if scenario=='size':return httpx.Response(200,content=b'x'*65537)
        return httpx.Response(200,json={'done':True,'done_reason':'length' if scenario=='truncated' else 'stop',
            'thinking':'private trace' if scenario=='thinking' else '', 'response':'{}',
            'prompt_eval_count':11 if scenario=='tokens' else 10,'eval_count':2})
    monkeypatch.setattr('app.rag_engine.httpx.AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    with pytest.raises(RagError,match=expected):asyncio.run(generator().generate('isolated test prompt',10))


def test_budget_removes_whole_passages_and_reserves_output():
    g=generator()
    class CountingDouble:
        def encode(self,text,**kwargs):return list(range(len(text)))
    g.tokenizer=CountingDouble()
    # Unit counter is intentionally a double; actual pinned-tokenizer equality is measured with Ollama.
    g.manifest['context_tokens']=10000
    passages=[SOURCE,{**SOURCE,'chunk_id':'second','text':'x'*20000}]
    prompt,tokens,selected,omitted=g.budget('2025 PM-KISAN factsheet','en',passages)
    assert omitted and selected==[SOURCE] and SOURCE['text'] in prompt
    assert tokens+768+64<=10000
    with pytest.raises(RagError,match='context_budget_exceeded'):g.budget('x'*11000,'en',[])
