"""Bounded, repeatable-read aggregates only; never private questions or comments."""
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from .auth import admin_user,now
from .database import get_db
from .models import User

router=APIRouter(tags=['admin analytics'])
OUTCOME="""CASE WHEN state='error' THEN 'failed' WHEN state='done' THEN
 CASE result->>'status' WHEN 'answered' THEN 'answered' WHEN 'partial' THEN 'partial'
 WHEN 'insufficient_evidence' THEN 'abstained' WHEN 'needs_clarification' THEN 'clarification'
 ELSE 'unclassified_done' END ELSE state END"""

@router.get('/admin/analytics')
def analytics(request:Request,days:int=Query(default=7,ge=1,le=30),end:datetime|None=None,
              user:User=Depends(admin_user),db:Session=Depends(get_db)):
    if days not in (1,7,30):raise HTTPException(422,'days must be 1, 7 or 30')
    as_of=now()
    if end is not None and (end.tzinfo is None or end>as_of):
        raise HTTPException(422,'end must be a timezone-aware timestamp no later than now')
    end=(end or as_of).astimezone(timezone.utc);start=end-timedelta(days=days)
    params={'start':start,'end':end}
    window='created_at >= :start AND created_at < :end'
    # Separate read-only snapshot prevents changing counts/denominators across aggregate queries.
    with db.get_bind().connect().execution_options(isolation_level='REPEATABLE READ') as conn,conn.begin():
        conn.execute(text('SET TRANSACTION READ ONLY'))
        snapshot_at=conn.scalar(text('SELECT transaction_timestamp()'))
        outcomes={k:0 for k in ('answered','partial','abstained','clarification','failed','cancelled','queued','processing','unclassified_done')}
        outcomes.update(dict(conn.execute(text(f'SELECT {OUTCOME} AS outcome,count(*) FROM answer_runs WHERE {window} GROUP BY outcome'),params).all()))
        languages=dict(conn.execute(text(f'SELECT language,count(*) FROM answer_runs WHERE {window} GROUP BY language'),params).all())
        latency=dict(conn.execute(text(f"""WITH terminal AS (
            SELECT CASE WHEN jsonb_typeof(timings->'worker_total_ms')='number'
                THEN (timings->>'worker_total_ms')::numeric END AS raw
            FROM answer_runs WHERE {window} AND state IN ('done','error','cancelled')),
            valid AS (SELECT CASE WHEN raw BETWEEN 0 AND 2592000000 THEN raw::double precision END AS ms FROM terminal)
            SELECT count(ms) AS sample_count,count(*)-count(ms) AS excluded_terminal_count,
                avg(ms) AS mean_ms,percentile_cont(0.5) WITHIN GROUP (ORDER BY ms) AS p50_ms,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY ms) AS p95_ms FROM valid"""),params).mappings().one())
        cohort="a.created_at >= :start AND a.created_at < :end"
        feedback_rows=conn.execute(text(f"""SELECT a.result->>'status' AS outcome,f.vote,count(*)
            FROM answer_feedback f JOIN answer_runs a ON a.id=f.run_id AND a.user_id=f.user_id
            WHERE {cohort} GROUP BY outcome,f.vote"""),params).all()
        feedback={k:{'helpful':0,'not_helpful':0} for k in ('answered','partial')}
        for outcome,vote,count in feedback_rows:
            if outcome in feedback:feedback[outcome][vote]=count
        reasons=dict(conn.execute(text(f"""SELECT coalesce(f.reason,'unspecified'),count(*)
            FROM answer_feedback f JOIN answer_runs a ON a.id=f.run_id AND a.user_id=f.user_id
            WHERE {cohort} GROUP BY f.reason"""),params).all())
        votes={vote:sum(v[vote] for v in feedback.values()) for vote in ('helpful','not_helpful')}
        count=sum(votes.values());denominator=outcomes['answered']+outcomes['partial']
        # Fixed table/column identifiers; no user-supplied SQL or per-record loading.
        processing={}
        for key,table in (('ingestion_jobs','ingestion_jobs'),('ocr_jobs','extraction_revisions'),('index_jobs','index_generations')):
            processing[key]=dict(conn.execute(text(f'SELECT state,count(*) FROM {table} WHERE {window} GROUP BY state'),params).all())
        processing['ocr_reviews']=dict(conn.execute(text(f'SELECT decision,count(*) FROM extraction_reviews WHERE {window} GROUP BY decision'),params).all())
        processing['ingested_versions']=conn.scalar(text('SELECT count(*) FROM document_versions WHERE ingested_at >= :start AND ingested_at < :end'),params)
    return {'data_environment':'isolated_test' if request.app.state.settings.environment=='test' else 'local_application','window':{'start':start,'end_exclusive':end,'timezone':'UTC','days':days,'snapshot_at':snapshot_at},
        'answer_runs':{'total':sum(outcomes.values()),'outcomes':outcomes,'languages':languages},
        'latency':latency,'feedback':{'count':count,'votes':votes,'by_outcome':feedback,'reasons':reasons,
            'participation_denominator':denominator,'participation_rate':count/denominator if denominator else None,
            'helpful_rate':votes['helpful']/count if count else None,'evidence_quality_component':None},
        'processing':processing,
        'definitions':{'cohort':'Retained answer runs created in [start,end). Feedback is the current vote on that cohort, including votes edited after end; not a feedback activity timeline.',
            'participation':'Current votes / retained completed answered or partial runs in the cohort, including subsequently revoked sources. Not a current-source-access rate.',
            'latency':'Recorded worker_total_ms on terminal runs; excludes missing, nonnumeric, negative or >30-day values. Pending runs are excluded. No missing stage timings are inferred.',
            'processing':'Versions use ingested_at. Job groups use job created_at with current state. OCR reviews use review created_at and count decisions, not distinct pages.',
            'retention':'Rolling 30-day terminal-answer deletion cascades feedback. Older windows are incomplete; job/source records have different retention.',
            'feedback':'Self-selected current helpful votes are satisfaction signals, never accuracy or a numerical evidence-quality component.'}}
