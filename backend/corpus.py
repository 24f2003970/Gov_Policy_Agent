"""Explicit local demo command; curated manifest only, never automatic server URL fetching."""
import argparse
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import ROOT, Settings
from app.database import make_engine, schema_ready
from app.documents import Metadata, persist_upload
from app.document_models import DocumentVersion
from app.models import User
from app.storage import checksum_file, directories, filename_format, validate_file
from app.auth import now
from app.index_models import EligibilityReview


def download(entry, path):
    if path.exists() and checksum_file(path) == entry['sha256']:
        return
    temporary = path.with_suffix('.download')
    try:
        # TLS verified; no bypasses/credentials. Redirects limited to this official source host.
        source = httpx.URL(entry['metadata']['source_url'])
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            url = source
            for _ in range(4):
                with client.stream('GET', url) as response:
                    if response.is_redirect:
                        url = response.url.join(response.headers['location'])
                        if url.scheme != 'https' or url.host.removeprefix('www.') != source.host.removeprefix('www.'):
                            raise ValueError('Unexpected redirect; inspect source manually')
                        continue
                    response.raise_for_status()
                    size = 0
                    with temporary.open('wb') as output:
                        for data in response.iter_bytes(65536):
                            size += len(data)
                            if size > 50 * 1024 * 1024: raise ValueError('Source exceeds limit')
                            output.write(data)
                    if checksum_file(temporary) != entry['sha256']:
                        raise ValueError('Source bytes changed; review manifest rather than silently accepting')
                    os.replace(temporary, path)
                    return
            raise ValueError('Too many redirects')
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--import', dest='import_files', action='store_true')
    args = parser.parse_args()
    if not (args.download or args.import_files): parser.error('Choose --download and/or --import')
    manifest = json.loads((ROOT / 'docs' / 'corpus_manifest.json').read_text('utf-8'))
    cache = ROOT / 'runtime' / 'corpus'; cache.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    engine = make_engine(settings) if args.import_files else None
    try:
        if engine and not schema_ready(engine): raise ValueError('Explicit migration required')
        for entry in manifest['entries']:
            format = filename_format(entry['filename'])
            path = cache / entry['filename']
            if args.download: download(entry, path)
            if not path.is_file() or checksum_file(path) != entry['sha256']: raise ValueError('Missing or mismatched source; download first')
            validate_file(settings, path, format)
            if engine:
                temporary = directories(settings) / 'temporary' / f'{uuid4().hex}.upload'
                try:
                    shutil.copyfile(path, temporary)
                    with Session(engine, expire_on_commit=False) as db:
                        admin = db.scalar(select(User).where(User.role == 'admin', User.active.is_(True)).order_by(User.created_at).limit(1))
                        if admin is None: raise ValueError('Existing active admin required; no admin created')
                        result = persist_upload(db, settings, temporary, entry['filename'], format, path.stat().st_size,
                                                entry['sha256'], Metadata(**entry['metadata']), admin.id)
                        version = db.get(DocumentVersion, result['version']['id'])
                        if version.provenance_status == 'unverified':
                            version.provenance_status, version.verified_at, version.verified_by = 'verified', now(), admin.id
                            version.verification_note = entry['verification_note']; db.commit()
                        if entry.get('review') and not db.scalar(select(EligibilityReview.id).where(EligibilityReview.version_id == version.id).limit(1)):
                            db.add(EligibilityReview(version_id=version.id, reviewer_id=admin.id, **entry['review']))
                            db.commit()
                        print(f"{entry['filename']}: {'existing' if result['duplicate'] else 'queued'}; rights={entry['metadata']['reuse_status']}")
                finally:
                    temporary.unlink(missing_ok=True)
            else:
                print(f"{entry['filename']}: checksum and PDF validation passed")
    finally:
        if engine: engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Corpus command failed. Check official source availability, manifest checksum, local files and migration. No private error details logged.')
        raise SystemExit(1)
