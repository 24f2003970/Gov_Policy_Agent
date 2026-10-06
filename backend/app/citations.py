"""Authoritative SQL provenance, stable citations and current access gates."""
from uuid import UUID,uuid5
from copy import deepcopy
from sqlalchemy import select
from .grounding import RagError
from .index_models import IndexGeneration,IndexPassage
from .document_models import Document,DocumentVersion,ExtractedPage
from .eligibility import eligibility
from .citation_models import AnswerClaim,ClaimCitation
from .extraction_artifacts import page_for, metadata_for

PROVENANCE_METHOD='sql-original-span-v1'


def validate_sources(db,passages,generation):
    if passages:
        job=db.get(IndexGeneration,UUID(generation),with_for_update=True)
        if not job or job.state!='ready':raise RagError('source_status_changed')
    for p in sorted(passages,key=lambda p:p['version_id']):
        version=db.get(DocumentVersion,UUID(p['version_id']),with_for_update=True)
        if not version:raise RagError('source_status_changed')
        db.get(Document,version.document_id,with_for_update=True)
        e=eligibility(db,version,p.get('extraction_revision_id'))
        if not e['eligible'] or e['review_id']!=p['verification']['review_id']:raise RagError('source_status_changed')
        passage=db.get(IndexPassage,UUID(p['chunk_id']))
        page=page_for(db,passage)
        if passage and any(p.get(k)!=metadata_for(db,passage)[k] for k in ('extraction_revision_id','extraction_page_id')):
            raise RagError('source_span_changed')
        if not passage or str(passage.generation_id)!=generation or str(passage.version_id)!=p['version_id'] or not page or page.version_id!=version.id:
            raise RagError('source_span_changed')
        if (passage.start_offset!=p['start_offset'] or passage.end_offset!=p['end_offset'] or passage.text!=p['text'] or
            page.text[p['start_offset']:p['end_offset']]!=p['text']):raise RagError('source_span_changed')


def context_for(db,evidence,passage_snapshot):
    passage=db.get(IndexPassage,UUID(evidence.id))
    page=page_for(db,passage)
    version=db.get(DocumentVersion,passage.version_id) if passage else None
    start,end=evidence.quote_start_offset,evidence.quote_end_offset
    if not page or not version or start is None or end is None or not (passage.start_offset<=start<end<=passage.end_offset):
        raise RagError('citation_provenance_invalid')
    if page.text[start:end]!=evidence.quote or page.text[passage.start_offset:passage.end_offset]!=passage.text:
        raise RagError('citation_provenance_invalid')
    spans=[p for p in page.paragraphs if p['end']>start and p['start']<end]
    if not spans:raise RagError('citation_context_missing')
    first,last=page.paragraphs.index(spans[0]),page.paragraphs.index(spans[-1])
    surrounding=page.paragraphs[max(0,first-1):last+2]
    context_start,context_end=surrounding[0]['start'],surrounding[-1]['end']
    doc=db.get(Document,version.document_id)
    metadata={'document_id':str(doc.id),'scheme_id':str(doc.scheme_id) if doc.scheme_id else None,'version_id':str(version.id),'version_number':version.version_number,
        'passage_id':str(passage.id),'page_id':str(page.id),'page_ordinal':page.ordinal,'pdf_page_number':page.pdf_page_number,
        'txt_source_start':page.source_start if version.format=='txt' else None,'title':doc.title,'issuer':doc.issuer,
        'source_url':version.source_url,'publication_date':str(version.publication_date) if version.publication_date else None,
        'effective_date':str(version.effective_date) if version.effective_date else None,'section_label':passage.section_label,
        'section_is_heuristic':bool(passage.section_label),'clause':None,'continued_clause':passage.continued_clause,
        'index_generation':str(passage.generation_id),'review':passage_snapshot['verification'],
        'paragraph_spans':[{'start':p['start'],'end':p['end']} for p in spans],
        'context_start':context_start,'context_end':context_end,**metadata_for(db,passage)}
    return {'id':str(passage.id),'quote':evidence.quote,'start_offset':start,'end_offset':end,
        'context':page.text[context_start:context_end],'metadata':metadata,
        'provenance':{'status':'valid','method':PROVENANCE_METHOD,'reason':'Exact quote, passage and version/page offsets matched authoritative SQL text.'}}


def persist_claims(db,run,records):
    result=deepcopy(run.result)
    for position,record in enumerate(records,1):
        claim_id=uuid5(run.id,f'claim:{position}:{record["text"]}')
        db.add(AnswerClaim(id=claim_id,run_id=run.id,position=position,text=record['text'],retained=record['retained'],
            assessment=record['assessment'],snapshot=dict(run.model)))
        db.flush()
        for ordinal,c in enumerate(record['citations'],1):
            m=c['metadata'];citation_id=uuid5(claim_id,f'citation:{ordinal}:{c["id"]}')
            db.add(ClaimCitation(id=citation_id,claim_id=claim_id,position=ordinal,version_id=UUID(m['version_id']),
                passage_id=UUID(c['id']),page_id=UUID(m['page_id']),quote=c['quote'],start_offset=c['start_offset'],end_offset=c['end_offset'],
                metadata_snapshot=m,provenance=c['provenance']))
        if record['retained']:
            displayed=next(c for c in result['claims'] if c['text']==record['text'] and 'claim_id' not in c)
            displayed['claim_id']=str(claim_id);displayed['position']=position;displayed['support']=record['assessment']
    run.result=result


def access_status(db,metadata):
    version=db.get(DocumentVersion,UUID(metadata['version_id']),with_for_update=True)
    if version:db.get(Document,version.document_id,with_for_update=True)
    e=eligibility(db,version,metadata.get('extraction_revision_id',metadata.get('review',{}).get('extraction_revision_id'))) if version else None
    if not e:return {'allowed':False,'reasons':['source_missing']}
    reasons=list(e['reasons'])
    if e['review_id']!=metadata.get('review',{}).get('review_id'):reasons.append('review_changed')
    passage=db.get(IndexPassage,UUID(metadata['passage_id'])) if metadata.get('passage_id') else None
    page=page_for(db,passage)
    if not passage or not page:reasons.append('provenance_missing')
    elif page.version_id!=version.id or passage.version_id!=version.id or page.text[passage.start_offset:passage.end_offset]!=passage.text:
        reasons.append('provenance_changed')
    elif metadata.get('extraction_revision_id',metadata.get('review',{}).get('extraction_revision_id'))!=metadata_for(db,passage)['extraction_revision_id']:
        reasons.append('extraction_revision_changed')
    return {'allowed':not reasons,'reasons':reasons,'applicability':e['applicability']}


def citation_views(db,run):
    claims=list(db.scalars(select(AnswerClaim).where(AnswerClaim.run_id==run.id).order_by(AnswerClaim.position)))
    items=[];checks=[]
    for claim in claims:
        checks.append({'claim_id':str(claim.id),'position':claim.position,'retained':claim.retained,'assessment':claim.assessment})
        if not claim.retained:continue  # Never display rejected factual statements as explanatory prose.
        for c in db.scalars(select(ClaimCitation).where(ClaimCitation.claim_id==claim.id).order_by(ClaimCitation.position)):
            access=access_status(db,c.metadata_snapshot)
            items.append({'citation_id':str(c.id),'claim_id':str(claim.id),'claim_position':claim.position,
                'claim_text':claim.text if access['allowed'] else None,'quote':c.quote if access['allowed'] else None,
                'start_offset':c.start_offset,'end_offset':c.end_offset,'metadata':c.metadata_snapshot,
                'provenance':c.provenance,'support':claim.assessment,'current_access':access})
    if not claims and run.result:
        # Presentation only: no migration/backfill/reassessment of old immutable answers.
        for position,claim in enumerate(run.result.get('claims',[]),1):
            claim_id=uuid5(run.id,f'claim:{position}:{claim["text"]}')
            support={'outcome':'not_evaluated','method':None,'reason':'Part 5 snapshot; the Part 6 support method was not executed.','independent_verification':False}
            checks.append({'claim_id':str(claim_id),'position':position,'retained':True,'assessment':support})
            for ordinal,e in enumerate(claim.get('evidence',[]),1):
                source=next((p for p in run.sources if p['chunk_id']==e['id']),None)
                if not source:continue
                passage=db.get(IndexPassage,UUID(e['id']));page=db.get(ExtractedPage,passage.page_id) if passage else None
                m={k:source.get(k) for k in ('document_id','version_id','title','issuer','source_url','publication_date','pdf_page_number','page_ordinal','section_label')}
                m.update(passage_id=e['id'],page_id=str(page.id) if page else None,review=source['verification'],
                    index_generation=run.model.get('index_generation'),effective_date=None,section_is_heuristic=bool(m.get('section_label')),clause=None)
                access=access_status(db,m);start=e.get('quote_start_offset')
                if start is None:start=source['start_offset']+source['text'].find(e['quote'])
                items.append({'citation_id':str(uuid5(claim_id,f'citation:{ordinal}:{e["id"]}')),'claim_id':str(claim_id),
                    'claim_position':position,'claim_text':claim['text'] if access['allowed'] else None,
                    'quote':e['quote'] if access['allowed'] else None,'start_offset':start,'end_offset':start+len(e['quote']),
                    'metadata':m,'provenance':{'status':'recorded_in_part5','method':'part5-exact-quotes','reason':'Historical provenance snapshot; not retrospectively marked checked.'},
                    'support':support,'current_access':access})
    for marker,c in enumerate(items,1):c['marker']=marker
    return items,checks
