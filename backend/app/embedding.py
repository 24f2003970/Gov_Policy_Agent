"""Pinned offline-only CPU encoder. Model preparation is an explicit CLI operation."""
import json
from pathlib import Path

MODEL = 'intfloat/multilingual-e5-small'
REVISION = '614241f622f53c4eeff9890bdc4f31cfecc418b3'
PROFILE = 'e5-token-v1:448:48'
SPEC = {'model': MODEL, 'revision': REVISION, 'dimensions': 384, 'normalized': True,
        'metric': 'cosine', 'max_tokens': 512, 'query_prefix': 'query: ', 'document_prefix': 'passage: ',
        'chunk_profile': PROFILE}


def model_path(settings):
    return settings.data_dir.parent / 'models' / ('e5-small-' + REVISION)


def prepare(settings):
    from huggingface_hub import snapshot_download
    path = model_path(settings)
    snapshot_download(MODEL, revision=REVISION, local_dir=str(path),
        allow_patterns=['*.json', 'tokenizer*', 'sentencepiece*', '*.model', 'model.safetensors', '1_Pooling/*', 'README.md'])
    encoder = Encoder(settings, validate_manifest=False)
    (path / 'gov-model.json').write_text(json.dumps(SPEC), encoding='utf-8')
    return encoder


class Encoder:
    def __init__(self, settings, validate_manifest=True):
        path = model_path(settings)
        if validate_manifest and (not (path / 'gov-model.json').is_file() or
                json.loads((path / 'gov-model.json').read_text('utf-8')) != SPEC):
            raise ValueError('model_not_prepared_or_mismatched')
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(2)
        self.model = SentenceTransformer(str(path), device='cpu', local_files_only=True,
            trust_remote_code=False, model_kwargs={'use_safetensors': True})
        self.tokenizer = self.model.tokenizer
        if self.model.get_sentence_embedding_dimension() != 384 or self.model.max_seq_length != 512:
            raise ValueError('model_configuration_mismatch')

    def tokens(self, text, query=False):
        return len(self.tokenizer(('query: ' if query else 'passage: ') + text,
                                  truncation=False, add_special_tokens=True)['input_ids'])

    def encode(self, texts, query=False):
        if any(self.tokens(t, query) > 512 for t in texts):
            raise ValueError('token_limit_no_truncation')
        prefix = 'query: ' if query else 'passage: '
        return self.model.encode([prefix + t for t in texts], batch_size=8,
            normalize_embeddings=True, show_progress_bar=False).tolist()

    def chunks(self, text):
        # Exact character windows found with the real fast tokenizer, including prefix/special tokens.
        from .extraction import paragraphs
        start = 0
        spans = paragraphs(text)
        while start < len(text):
            low, high = start + 1, min(len(text), start + 8000)
            while low < high:
                mid = (low + high + 1) // 2
                if self.tokens(text[start:mid]) <= 448: low = mid
                else: high = mid - 1
            end = low
            if self.tokens(text[start:end]) > 448:
                raise ValueError('unencodable_character')
            if end < len(text):
                boundary = text.rfind('\n', start + (end-start)//2, end)
                if boundary >= 0: end = boundary + 1
            containing = next((p for p in spans if p['start'] <= start < p['end']), None)
            yield {'start_offset': start, 'end_offset': end, 'text': text[start:end],
                'section_label': containing['section_label'] if containing else None,
                'continued_clause': bool(containing and start > containing['start']), 'profile': PROFILE}
            if end == len(text): break
            offsets = self.tokenizer(text[start:end], add_special_tokens=False,
                return_offsets_mapping=True, truncation=False)['offset_mapping']
            overlap = offsets[-48][0] if len(offsets) > 48 else max(1, (end-start)//2)
            start += max(1, overlap)
