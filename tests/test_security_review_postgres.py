"""Focused preservation of raw upload semantics above the JSON body cap."""
from pathlib import Path
from test_auth_postgres import postgres
from test_documents_postgres import docs,upload


def test_large_raw_upload_and_markup_filename_stay_private_plain_text(docs):
    client,settings,engine,headers=docs
    data=b'Synthetic private body boundary fixture.\n'*2000
    assert len(data)>65536
    filename='<img onerror=alert(1)>.txt'
    response=upload(docs,data,name=filename)
    assert response.status_code==202
    version=response.json()['version']['id']
    original=client.get(f'/admin/documents/versions/{version}/original',headers=headers)
    assert original.content==data and original.headers['content-type'].startswith('text/plain')
    assert original.headers['x-content-type-options']=='nosniff'
    assert filename not in original.headers['content-disposition']
    assert len(list((settings.data_dir/'originals').glob('*.txt')))==1
    for path in ('../escape.txt','C:\\escape.txt','\\\\other-host\\share.txt','bad\r\nheader.txt'):
        assert upload(docs,b'synthetic',name=path).status_code==422
