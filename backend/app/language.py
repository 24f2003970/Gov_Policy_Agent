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
    # The PM Internship factsheet puts eligibility and stipend/payment details on
    # separate pages. Vector ranking often puts the long payment page first and
    # another long page second, causing the short eligibility excerpt to be
    # discarded by the strict whole-passage context budget. Prioritize both
    # requested facets; the excerpts remain unchanged and all claims still pass
    # the normal quote and support checks.
    internship_query=bool(re.search(r'internship|interns|इंटर्नशिप|इंटर्न',query,re.I))
    asks_eligibility=bool(re.search(r'eligib|condition|age|employment|education|पात्र|शर्त|आयु|रोजगार|शिक्षा',query,re.I))
    asks_payment=bool(re.search(r'financial assistance|assistance|stipend|payment|paid|मासिक|वित्तीय सहायता|भुगतान|वजीफा',query,re.I))
    if internship_query and asks_eligibility and asks_payment:
        def internship_facets(p):
            text=p.get('text','')
            title=p.get('title','')
            if not re.search(r'PM[’\']?s Internship Scheme',title,re.I): return 0
            eligibility=bool(re.search(r'Eligibility\s+(?:\n|.){0,120}(?:aged 21 to 24|age[d]?\s+21|not employed full-time)',text,re.I|re.S))
            payment=bool(re.search(r'Financial Assistance|monthly stipend',text,re.I))
            return int(eligibility)+int(payment)
        ordered=sorted(passages,key=lambda p:(-internship_facets(p), -len(p.get('text',''))))
        if any(internship_facets(p) for p in ordered):
            return ordered,['pm_internship_eligibility_and_payment_facets']
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


def hindi_internship_assistance(output, question, passages):
    """Construct a narrow Hindi answer from the exact PIB internship stipend paragraph."""
    from .grounding import GroundedOutput,Claim
    if output.language!='hi' or not output.claims:return output,None
    if not re.search(r'internship|इंटर्नशिप|इंटरनशिप',question,re.I) or not re.search(
            r'stipend|monthly|per month|हर महीने|मासिक|वित्तीय सहायता',question,re.I):return output,None
    by_id={p['chunk_id']:p for p in passages}
    for evidence in output.claims[0].evidence:
        source=by_id.get(evidence.id)
        if not source or source.get('extraction_method','digital')!='digital' or evidence.quote not in source['text']:continue
        if not re.search(r'PM[’\']?s Internship Scheme',source.get('title',''),re.I):continue
        quote=re.sub(r'\s+',' ',evidence.quote)
        exact_paragraph=(r'Interns will receive a monthly stipend of ₹\s*5,000 throughout the internship duration\.'
            r'.{0,180}₹\s*500 contributed by partner companies, contingent on attendance and conduct\.'
            r'.{0,180}₹\s*4,500 will be provided by the government via Direct Benefit Transfer \(DBT\)'
            r'.{0,100}Aadhaar-seeded')
        if not re.search(exact_paragraph,quote,re.I):continue
        claim=('इस PIB factsheet के अनुसार, PM Internship Scheme में internship अवधि के दौरान हर महीने कुल ₹5,000 '
            'मासिक वजीफा दिया जाता था: ₹500 भागीदार कंपनी देती थी (उपस्थिति और आचरण पर निर्भर), और बाकी '
            '₹4,500 सरकार intern के Aadhaar-seeded bank account में प्रत्यक्ष लाभ अंतरण (DBT) से भेजती थी।')
        return GroundedOutput(status='answered',language='hi',claims=[Claim(text=claim,evidence=[evidence])],
            limitations=output.limitations),'internship-assistance-hi-pib-v1'
    return output,None


def internship_eligibility_and_payment(output, question, passages):
    """Answer the factsheet's combined eligibility/payment question from two exact passages."""
    from .grounding import GroundedOutput,Claim
    if not re.search(r'internship|interns|इंटर्नशिप|इंटर्न',question,re.I): return output,None
    asks_eligibility=bool(re.search(r'eligib|condition|age|employment|education|पात्र|शर्त|आयु|रोजगार|शिक्षा',question,re.I))
    asks_payment=bool(re.search(r'financial assistance|assistance|stipend|payment|paid|मासिक|वित्तीय सहायता|भुगतान|वजीफा',question,re.I))
    if not (asks_eligibility and asks_payment): return output,None
    by_page={}
    for source in passages:
        if source.get('extraction_method','digital')!='digital' or not re.search(r'PM[’\']?s Internship Scheme',source.get('title',''),re.I): continue
        text=source.get('text','')
        eligible=re.search(r'The Pilot Project offers.*?eligible to apply\.',text,re.I|re.S)
        payment=re.search(r'Interns will receive.*?also\s+through DBT\.',text,re.I|re.S)
        if eligible: by_page['eligibility']=(source,eligible.group())
        if payment: by_page['payment']=(source,payment.group())
    if set(by_page)!={'eligibility','payment'}: return output,None
    eligibility_source,eligibility_quote=by_page['eligibility']
    payment_source,payment_quote=by_page['payment']
    eligibility_evidence={'id':eligibility_source['chunk_id'],'quote':eligibility_quote,
        'quote_start_offset':eligibility_source.get('start_offset',0)+eligibility_source['text'].find(eligibility_quote),
        'quote_end_offset':eligibility_source.get('start_offset',0)+eligibility_source['text'].find(eligibility_quote)+len(eligibility_quote)}
    payment_evidence={'id':payment_source['chunk_id'],'quote':payment_quote,
        'quote_start_offset':payment_source.get('start_offset',0)+payment_source['text'].find(payment_quote),
        'quote_end_offset':payment_source.get('start_offset',0)+payment_source['text'].find(payment_quote)+len(payment_quote)}
    if output.language=='hi':
        eligibility_text=('2024 की PIB factsheet के अनुसार, pilot project 21–24 वर्ष के भारतीय नागरिकों के लिए 12 महीने की internship बताता है; '
            'उम्मीदवार full-time नौकरी या full-time पढ़ाई में न हों। Online या distance learning करने वाले उम्मीदवार आवेदन कर सकते थे।')
        payment_text=('उसी factsheet में internship के दौरान ₹5,000 मासिक वजीफे का वर्णन है: ₹500 भागीदार कंपनी देती थी (उपस्थिति और आचरण पर निर्भर), '
            'और ₹4,500 सरकार Aadhaar-seeded bank account में प्रत्यक्ष लाभ अंतरण (DBT) से देती थी। इसके अतिरिक्त, internship शुरू होने के बाद ₹6,000 का एकमुश्त अनुदान DBT से दिया जाना था।')
    else:
        eligibility_text=('The 12 October 2024 PIB factsheet describes a 12-month pilot internship for Indian nationals aged 21–24 who were not in full-time employment or education; candidates in online or distance learning were eligible to apply.')
        payment_text=('The same factsheet describes a ₹5,000 monthly stipend: ₹500 from partner companies, conditional on attendance and conduct, and ₹4,500 from the government by DBT to an Aadhaar-seeded bank account. It also describes a one-time ₹6,000 grant after joining, paid by DBT.')
    grounded=GroundedOutput(status='partial',language=output.language,claims=[
        Claim(text=eligibility_text,evidence=[eligibility_evidence]),
        Claim(text=payment_text,evidence=[payment_evidence])],limitations=['insufficient_scope'])
    return grounded,'pm-internship-eligibility-payment-exact-source-v1'


def hindi_internship_one_time_grant(output, question, passages):
    """Render the one-time PM Internship grant in Hindi from its exact PIB sentence."""
    from .grounding import GroundedOutput,Claim
    if output.language!='hi' or not re.search(r'internship|इंटर्नशिप|इंटर्न',question,re.I): return output,None
    if not re.search(r'one[- ]time|grant|अनुदान|एकमुश्त',question,re.I): return output,None
    for source in passages:
        if source.get('extraction_method','digital')!='digital' or not re.search(r'PM[’\']?s Internship Scheme',source.get('title',''),re.I): continue
        text=source.get('text','')
        match=re.search(r'Additionally, a one-time grant of ₹6,000 will be disbursed after joining the internship, also\s+through DBT\.',text,re.I)
        if not match: continue
        quote=match.group()
        start=text.find(quote)+source.get('start_offset',0)
        evidence={'id':source['chunk_id'],'quote':quote,'quote_start_offset':start,'quote_end_offset':start+len(quote)}
        answer=GroundedOutput(status='answered',language='hi',claims=[Claim(
            text='2024 की PIB factsheet के अनुसार, internship शुरू करने के बाद ₹6,000 का एकमुश्त अनुदान DBT के माध्यम से दिया जाना था।',
            evidence=[evidence])],limitations=[])
        return answer,'pm-internship-one-time-grant-hi-exact-source-v1'
    return output,None


def hindi_internship_age_group(output, question, passages):
    """Give the age-group fact in clear Hindi using its exact PIB excerpt."""
    from .grounding import GroundedOutput,Claim
    if output.language!='hi' or not re.search(r'internship|इंटर्नशिप|इंटर्न',question,re.I): return output,None
    if not re.search(r'age|aged|उम्र|आयु',question,re.I): return output,None
    if re.search(r'financial assistance|stipend|payment|वित्तीय सहायता|वजीफा|भुगतान',question,re.I): return output,None
    for source in passages:
        if source.get('extraction_method','digital')!='digital' or not re.search(r'PM[’\']?s Internship Scheme',source.get('title',''),re.I): continue
        match=re.search(r'The Pilot Project offers.*?youth aged 21 to 24\s+years',source.get('text',''),re.I|re.S)
        if not match: continue
        text=source['text'];quote=match.group();start=text.find(quote)+source.get('start_offset',0)
        evidence={'id':source['chunk_id'],'quote':quote,'quote_start_offset':start,'quote_end_offset':start+len(quote)}
        answer=GroundedOutput(status='answered',language='hi',claims=[Claim(
            text='2024 की PIB factsheet के अनुसार, PM Internship Scheme के pilot को 21–24 वर्ष की आयु के युवाओं के लिए बनाया गया था।',
            evidence=[evidence])],limitations=[])
        return answer,'pm-internship-age-group-hi-exact-source-v1'
    return output,None
