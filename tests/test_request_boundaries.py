import asyncio
from fastapi import Request
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from index import service


def application():
    app=create_app(Settings(_env_file=None,environment='test'))
    @app.post('/test/echo')
    async def echo(request:Request):return {'bytes':len(await request.body())}
    return app


def test_untrusted_hosts_rejected_before_url_based_checks():
    with TestClient(application(),base_url='http://127.0.0.1:8000') as client:
        for host in ('evil.example','evil.example/auth/refresh','127.0.0.1@evil.example','127.0.0.1:8000/auth/refresh'):
            response=client.get('/health/live',headers={'Host':host})
            assert response.status_code==400
        assert client.get('/health/live',headers={'Host':'localhost:8000'}).status_code==200


def test_request_byte_limit_and_no_reflected_content():
    with TestClient(application(),base_url='http://127.0.0.1:8000') as client:
        assert client.post('/test/echo',content=b'x'*65536).json()['bytes']==65536
        r=client.post('/test/echo',content=b'x'*65537,headers={'Origin':'http://127.0.0.1:5173'})
        assert r.status_code==413 and 'xxxxx' not in r.text
        assert r.headers['access-control-allow-origin']=='http://127.0.0.1:5173'
        assert r.headers['cache-control']=='no-store'
        assert client.post('/test/echo',content=b'small',headers={'Content-Length':'90000'}).status_code==413


def test_stream_limit_cannot_trust_missing_or_small_content_length():
    async def exercise(headers):
        app=application();messages=[{'type':'http.request','body':b'x'*40000,'more_body':True},
                                    {'type':'http.request','body':b'x'*30000,'more_body':False}];sent=[]
        async def receive():return messages.pop(0) if messages else {'type':'http.disconnect'}
        async def send(message):sent.append(message)
        await app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST','scheme':'http',
                   'path':'/test/echo','raw_path':b'/test/echo','query_string':b'',
                   'headers':[(b'host',b'127.0.0.1:8000'),*headers],'client':('127.0.0.1',1),'server':('127.0.0.1',8000)},receive,send)
        assert next(m['status'] for m in sent if m['type']=='http.response.start')==413
    for headers in ([],[(b'content-length',b'1')]):asyncio.run(exercise(headers))


def test_private_index_has_same_host_body_bounds_and_key_gate():
    class Runtime:
        def run_once(self):pass
        def search(self,**kwargs):return {'status':'empty','items':[]}
    with TestClient(service(Runtime(),'synthetic-test-key'),base_url='http://127.0.0.1:8011') as client:
        assert client.post('/query',json={'question':'test'}).status_code==403
        assert client.post('/query',headers={'Host':'127.0.0.1:8011/elsewhere'},json={'question':'test'}).status_code==400
        assert client.post('/query',content=b'x'*65537).status_code==413
        assert client.post('/query',headers={'X-Index-Key':'synthetic-test-key'},json={'question':'test'}).status_code in (200,503)
