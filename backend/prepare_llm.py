"""Explicit official model/tokenizer download. Never invoked by ordinary API startup."""
import json
import hashlib
from filelock import FileLock
import httpx
import requests
from app.config import Settings, ROOT
from app.ollama_local import OllamaHost, URL, TAG


TOKENIZER_FILES = ('tokenizer.json', 'tokenizer_config.json', 'config.json')


def prepare_tokenizer(root, repository, revision, expected_hashes):
    tokenizer_dir = root/'tokenizer'
    def files_match():
        return all((tokenizer_dir/name).is_file() and
            hashlib.sha256((tokenizer_dir/name).read_bytes()).hexdigest() == expected_hashes[name]
            for name in TOKENIZER_FILES)

    if not files_match():
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(repository, revision=revision, local_dir=str(tokenizer_dir),
                allow_patterns=list(TOKENIZER_FILES))
        except Exception:
            pass
    if not files_match():
        # Qwen also publishes this exact tokenizer on ModelScope. Its copy is
        # accepted only when every file matches the project-pinned SHA256.
        print('Hugging Face unavailable; trying the pinned-hash Qwen ModelScope copy.', flush=True)
        tokenizer_dir.mkdir(parents=True, exist_ok=True)
        base = 'https://modelscope.cn/models/Qwen/Qwen3-4B-Instruct-2507/resolve/master/'
        for name in TOKENIZER_FILES:
            response = requests.get(base+name, stream=True, timeout=120)
            response.raise_for_status()
            temporary = tokenizer_dir/(name+'.download')
            digest = hashlib.sha256()
            with temporary.open('wb') as output:
                for chunk in response.iter_content(1024*1024):
                    if chunk:
                        digest.update(chunk)
                        output.write(chunk)
            response.close()
            if digest.hexdigest() != expected_hashes[name]:
                temporary.unlink(missing_ok=True)
                raise RuntimeError('Qwen tokenizer file does not match the pinned revision')
            temporary.replace(tokenizer_dir/name)
    if not files_match():
        raise RuntimeError('Prepared Qwen tokenizer file does not match its pinned SHA256')

if __name__ == '__main__':
    settings = Settings(); root = settings.data_dir.parent/'ollama'; root.mkdir(parents=True,exist_ok=True)
    lock=settings.owner_path('rag');lock.parent.mkdir(parents=True,exist_ok=True)
    with FileLock(str(lock),timeout=0), OllamaHost(settings):
        with httpx.Client(trust_env=False,timeout=120) as client:
            with client.stream('POST',URL+'/api/pull',json={'model':TAG,'stream':True}) as response:
                response.raise_for_status(); last = None
                for line in response.iter_lines():
                    item=json.loads(line)
                    if item.get('error'): raise RuntimeError('Official model pull failed')
                    progress=int(item.get('completed',0)*100/max(1,item.get('total',1)))
                    label=(item.get('status'),progress//10)
                    if label!=last: print(item.get('status'),progress,flush=True);last=label
            record=next(m for m in client.get(URL+'/api/tags').json()['models'] if m['name']==TAG)
            show=client.post(URL+'/api/show',json={'model':TAG}).json()
            ollama_version=client.get(URL+'/api/version').json()['version']
        expected=ROOT/'docs/llm_model.json'
        pins=json.loads(expected.read_text('utf-8')) if expected.exists() else {}
        revision=pins['tokenizer_revision'] if expected.exists() else httpx.get(
            'https://huggingface.co/api/models/Qwen/Qwen3-4B-Instruct-2507',trust_env=False,timeout=30).json()['sha']
        prepare_tokenizer(root, 'Qwen/Qwen3-4B-Instruct-2507', revision, pins['tokenizer_files'])
        manifest={'tag':TAG,'digest':record['digest'],'quantization':show['details']['quantization_level'],
            'parameters':show['details']['parameter_size'],'ollama_version':ollama_version,
            'tokenizer_repository':'Qwen/Qwen3-4B-Instruct-2507','tokenizer_revision':revision,
            'tokenizer_files':pins['tokenizer_files'],
            'context_tokens':4096,'output_tokens':768,'temperature':0,'seed':28,'think':False}
        if expected.exists() and json.loads(expected.read_text('utf-8'))!=manifest:
            raise RuntimeError('Prepared model differs from pinned record; review deliberately before changing it')
        if not expected.exists(): expected.write_text(json.dumps(manifest,indent=2)+'\n','utf-8')
        (root/'prepared.json').write_text(json.dumps(manifest),'utf-8')
        print(json.dumps(manifest),flush=True)
