"""Local owner maintenance; private DB credentials, no token/identity output."""
import argparse
import json
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import Settings
from app.database import make_engine,schema_ready
from app.models import User
from app.ocr import queue
from app.ocr_models import ExtractionRevision
from app.ocr_api import view


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['queue','status']);parser.add_argument('version_id',type=UUID)
    args=parser.parse_args();settings=Settings();engine=make_engine(settings)
    if not schema_ready(engine):raise SystemExit('Current migration required')
    with Session(engine) as db:
        if args.command=='queue':
            user=db.scalar(select(User).where(User.role=='admin',User.active.is_(True)).order_by(User.created_at).limit(1))
            if not user:raise SystemExit('An existing active admin is required')
            revision=queue(db,settings,args.version_id,user.id)
            print(json.dumps({'id':str(revision.id),'state':revision.state,'total':revision.total}))
        else:
            for revision in db.scalars(select(ExtractionRevision).where(ExtractionRevision.version_id==args.version_id).order_by(ExtractionRevision.created_at.desc()).limit(20)):
                value=view(db,revision)
                print(json.dumps({k:value[k] for k in ('id','state','attempts','processed','total','error_code','pages')},default=str))
    engine.dispose()
