"""Bounded transparent query normalization; no language-choice or factual inference."""
import re
import unicodedata

REVISION = 'hinglish-phrases-v1'
PHRASES = (
    (r'pradhan\s+mantri\s+kisan(?:\s+samman\s+nidhi)?|प्रधानमंत्री\s+किसान(?:\s+सम्मान\s+निधि)?|पीएम[ -]?किसान', 'PM-KISAN', 'scheme_alias'),
    (r'ke\s+(?:anusaar|anusar)', 'according to', 'historical_scope'),
    (r'dastave[sz]|factsheet', 'factsheet', 'document_alias'),
    (r'saala?na|salana|saalana|har\s+saal', 'annual', 'annual_frequency'),
    (r'kisht(?:on|en|e)?|kist(?:on|en|e)?', 'instalments', 'instalment_spelling'),
    (r'kitn[ai]|kitne', 'how much', 'question_word'),
    (r'pais[ae]|rashi', 'amount', 'amount_word'),
    (r'bina', 'without', 'negation'),
    (r'nahin|nahi', 'not', 'negation'),
    (r'aaj|abhi', 'today', 'current_scope'),
    (r'patra|paatra', 'eligible', 'eligibility_scope'),
    (r'aavedan|avedan', 'apply', 'application_scope'),
)


def normalize(question):
    query = unicodedata.normalize('NFC', question)
    transformations = []
    if query != question: transformations.append('unicode_nfc')
    converted = query.translate(str.maketrans('०१२३४५६७८९','0123456789'))
    if converted != query: transformations.append('devanagari_digits')
    query = re.sub(r'\s+',' ',converted).strip()
    if query != converted: transformations.append('whitespace')
    # Only complete common phrases; do not guess missing dates, beneficiaries or scheme identity.
    roman = bool(re.search(r'\b(?:saalana|salana|kiste|kisht|kitna|kitni|kitne|anusaar|anusar|nahi|bina|aaj|abhi|patra|paatra|avedan|aavedan)\b',query,re.I))
    for pattern, replacement, label in PHRASES:
        if label != 'scheme_alias' and not roman: continue
        query, count = re.subn(r'(?<!\w)(?:'+pattern+r')(?!\w)',replacement,query,flags=re.I)
        if count: transformations.append(label)
    devanagari = bool(re.search(r'[\u0900-\u097f]',question))
    detected = 'mixed' if devanagari and re.search(r'[a-zA-Z]{3}',question) else 'hi' if devanagari else 'hinglish' if roman else 'uncertain'
    return {'original_question':question,'retrieval_question':query,'revision':REVISION,
        'transformations':list(dict.fromkeys(transformations)),'detected_language':detected,
        'notice':'Detection may be uncertain; explicit response selection/profile always takes precedence.'}


def context_order(question, passages):
    """Retain complete likely-relevant excerpts before token budgeting; never establish support."""
    query=normalize(question)['retrieval_question'].lower()
    rules=[]
    if re.search(r'annual|per year|हर साल|वार्षिक|प्रति वर्ष',query):
        rules.append(('annual_benefit',lambda p:bool(re.search(r'per year',p['text'],re.I) and re.search(r'financial benefit|assistance',p['text'],re.I))))
    if not rules:return list(passages),[]
    ordered=sorted(passages,key=lambda p:-sum(matches(p) for _,matches in rules))
    if (rules[0][0]=='annual_benefit' and not re.search(r'objective|crop|moneylender|उद्देश्य|खेती|साहूकार|chatbot|चैटबॉट|e.kyc',query,re.I)):
        relevant=[p for p in ordered if rules[0][1](p)]
        if relevant:
            # Annual-assistance questions must not cite adjacent cumulative/national disbursements.
            # Complete chunks remain intact; no value/condition is removed or supplied by the selector.
            return relevant,['annual_benefit_complete_excerpts_only']
    return ordered,[name for name,_ in rules]


def hindi_annual(output, question, passages):
    """Narrow digital-source construction; final text still requires the unchanged support stage."""
    from .grounding import GroundedOutput,Claim
    if output.language!='hi' or not output.claims:return output,None
    _,rules=context_order(question,passages)
    if 'annual_benefit_complete_excerpts_only' not in rules:return output,None
    by_id={p['chunk_id']:p for p in passages}
    for evidence in output.claims[0].evidence:
        source=by_id[evidence.id]
        if source.get('extraction_method','digital')!='digital':continue
        if evidence.quote not in source['text']:continue
        text=re.sub(r'\s+',' ',evidence.quote)
        if not re.search(r'to supplement the financial needs of land-holding farmers\.',text,re.I):continue
        match=re.search(r'Under the scheme, a financial benefit of Rs\s+([\d,]+)(?:/-)? per year is transferred in (one|two|three|four|five|six|seven|eight|nine|ten|\d+) equal instalments',text,re.I)
        if not match or not re.search(r'PM-KISAN scheme',text,re.I):continue
        counts={word:str(i) for i,word in enumerate(('one','two','three','four','five','six','seven','eight','nine','ten'),1)}
        amount,count=match.groups();count=counts.get(count.lower(),count)
        date=str(source.get('publication_date') or '')
        frame=(date[:4]+' के दस्तावेज़ के अनुसार, ') if re.fullmatch(r'\d{4}-\d{2}-\d{2}',date) else 'दस्तावेज़ के अनुसार, '
        claim=frame+f'भूमिधारक किसानों (land-holding farmers) के लिए PM-KISAN में {amount} रुपये प्रति वर्ष की सहायता {count} बराबर किस्तों में देने का वर्णन है।'
        family=bool(re.search(r'famil(?:y|ies)|परिवार',question,re.I))
        limitations=list(output.limitations)
        if family and 'insufficient_scope' not in limitations:limitations.append('insufficient_scope')
        return GroundedOutput(status='partial' if family else output.status,language='hi',claims=[Claim(text=claim,evidence=[evidence])],limitations=limitations),'annual-hi-digital-fields-v1'
    return output,None


def hindi_chatbot(output, question, passages):
    """One exact digital paragraph pattern preserves the two proper source names."""
    from .grounding import GroundedOutput,Claim
    if output.language!='hi' or not output.claims:return output,None
    if not re.search(r'chatbot|चैटबॉट',question,re.I) or not re.search(r'organis|संस्था',question,re.I):return output,None
    by_id={p['chunk_id']:p for p in passages}
    for evidence in output.claims[0].evidence:
        source=by_id[evidence.id]
        if source.get('extraction_method','digital')!='digital' or evidence.quote not in source['text']:continue
        text=re.sub(r'\s+',' ',evidence.quote)
        if not re.search(r'PM-KISAN AI CHATBOT',text) or not re.search(r'It has been developed and improved with the support of EKstep foundation and Bhashini\.',text):continue
        claim='दस्तावेज़ के अनुसार, PM-KISAN AI chatbot का विकास और सुधार EKstep foundation और Bhashini के सहयोग से किया गया था।'
        return GroundedOutput(status=output.status,language='hi',claims=[Claim(text=claim,evidence=[evidence])],limitations=output.limitations),'chatbot-hi-digital-names-v1'
    return output,None
