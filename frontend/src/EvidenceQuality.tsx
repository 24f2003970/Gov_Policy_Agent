export type Assessment = {
  status:string; answer_status?:string; method:string; saved_snapshot:boolean; assessed_at?:string;
  full_aggregate:null; partial_index:null; available_weight_coverage:number;
  components:Record<string,{value:number|null;availability:string;weight:number;method:string;explanation:string;evidence:unknown}>;
  counts:Record<string,number>; source_references:unknown[]; limitations:string[]; aggregate_reason:string;
}

const labels:Record<string,[string,string]> = {
  recency:['Source currency','स्रोत की समय-संगति'], citation_coverage:['Citation coverage','दावों के स्रोत'],
  faithfulness:['Meaning supported by evidence','अर्थ के समर्थन की जाँच'], consistency:['Independent agreement','स्वतंत्र स्रोतों में सहमति'],
  calibration:['Measured reliability','मापी गई विश्वसनीयता'], feedback:['User feedback','उपयोगकर्ता प्रतिक्रिया'],
}
const hindi:Record<string,string> = {
  recency:'दर्ज तारीख और लागू होने का दायरा नीचे देखें। पुरानी तारीख से ऐतिहासिक उत्तर गलत नहीं होता; वर्तमान पात्रता साबित नहीं होती।',
  citation_coverage:'दिखाए गए तथ्यात्मक दावों में सही मूल उद्धरण वाले दावों का हिस्सा। सभी दावों के स्रोत होने का मतलब पूरे प्रश्न का उत्तर मिलना नहीं है।',
  faithfulness:'मौजूदा नियम और उत्तर बनाने वाला वही मॉडल समर्थन जाँचते हैं। यह स्वतंत्र सत्यापन नहीं है और स्रोत-कवरेज से जुड़ा है; इसकी सटीकता का मान्य संख्यात्मक माप नहीं है।',
  consistency:'एक ही स्रोत के अंश, प्रतियाँ या संस्करण स्वतंत्र पुष्टि नहीं हैं। स्वतंत्र सहमति स्थापित नहीं हुई है।',
  calibration:'अलग, पहले न इस्तेमाल किए गए मूल्यांकन से विश्वसनीयता नहीं मापी गई है। विकास के दौरान जाँचे गए उदाहरण पर्याप्त नहीं हैं।',
  feedback:'प्रतिक्रिया वोट अलग से संतुष्टि बताते हैं। उन्हें प्रमाण-गुणवत्ता में बदलने की मान्य विधि नहीं है; अनुमानित मान नहीं भरा गया है।',
}
const english:Record<string,string> = {
  recency:'Source dates and scope appear in details. Age alone cannot tell whether policy is still in force; old sources can support historical answers.',
  citation_coverage:'Share of displayed factual claims with valid original quotes. Fully cited claims do not mean the whole question was answered.',
  faithfulness:'The support check uses the model that also wrote the answer, with the same evidence as citation coverage. Its agreement is not independent proof; no validated numerical measure is available.',
  consistency:'Chunks, copies and versions of one source are not independent confirmation. Independent agreement has not been established.',
  calibration:'Reliability has not been measured using a separate, unused set of questions. Development examples are not enough.',
  feedback:'Feedback votes measure satisfaction separately. No validated method converts them into evidence quality; no guessed value is used.',
}
const statuses:Record<string,[string,string]> = {
  assessed_limited:['Limited assessment','सीमित आकलन'], not_evaluated:['Not evaluated — historical answer was not rescored','आकलन नहीं हुआ — पुराने उत्तर की दोबारा जाँच नहीं की गई'],
  insufficient_evidence:['Insufficient evidence — no factual score','पर्याप्त प्रमाण नहीं — तथ्यात्मक स्कोर नहीं'],
  needs_clarification:['Clarification needed — no factual score','स्पष्ट प्रश्न चाहिए — तथ्यात्मक स्कोर नहीं'],
  clarification_needed:['Clarification needed — no factual score','स्पष्ट प्रश्न चाहिए — तथ्यात्मक स्कोर नहीं'],
  generation_failed:['Answer failed — no factual score','उत्तर नहीं बन पाया — तथ्यात्मक स्कोर नहीं'], cancelled:['Cancelled — no factual score','रद्द हुआ — तथ्यात्मक स्कोर नहीं'],
  source_unavailable:['Source unavailable — saved values withheld','स्रोत उपलब्ध नहीं — पुराने मान रोके गए'], pending:['Assessment pending','आकलन बाकी है'],
}

export default function EvidenceQuality({assessment:a,language}:{assessment:Assessment;language:string}) {
  const hi=language==='hi', t=(en:string,hn:string)=>hi?hn:en
  const status=statuses[a.status]||[a.status,a.status]
  return <aside aria-label={t('Evidence quality','प्रमाण की गुणवत्ता')} className="space-y-3 rounded border border-slate-300 bg-slate-50 p-4">
    <h3 className="text-lg font-semibold">{t('Evidence quality','प्रमाण की गुणवत्ता')}</h3>
    <p>{hi?status[1]:status[0]}</p>
    <p className="text-sm">{t('This describes the available evidence, not the probability that the answer is correct. Overall score: unavailable.','यह उपलब्ध प्रमाण का विवरण है, उत्तर सही होने की संभावना नहीं। कुल स्कोर: उपलब्ध नहीं।')}</p>
    {a.answer_status==='partial'&&<p className="text-sm">{t('Only part of the question was answered. Citation coverage applies to the retained claims.','प्रश्न का केवल आंशिक उत्तर मिला। स्रोत-कवरेज केवल रखे गए दावों पर लागू है।')}</p>}
    {a.available_weight_coverage>0&&<p className="text-sm">{t('Available measurement covers','उपलब्ध माप का हिस्सा')} {Math.round(a.available_weight_coverage*100)}% {t('of the experimental weights. A citation-only measurement is not combined into a partial index.','प्रयोगात्मक भार है। केवल स्रोत-कवरेज से आंशिक संयुक्त स्कोर नहीं बनाया जाता।')}</p>}
    {!!Object.keys(a.counts).length&&<p className="text-sm">{t('Candidate checks','संभावित दावों की जाँच')}: {a.counts.candidate_records} · {t('retained','रखे गए')}: {a.counts.retained_records} · {t('rejected','हटाए गए')}: {a.counts.rejected_records}. {t('These count checking attempts, including repairs; displayed factual claims','इनमें सुधार के प्रयास भी गिने जाते हैं; दिखाए गए तथ्यात्मक दावे')}: {a.counts.displayed_factual_claims}.</p>}
    {!!a.counts.conflicting_records&&<p role="status" className="rounded border border-amber-400 p-2">{t('Conflicting evidence detected during checking. Conflict is not hidden in an average.','जाँच में विरोधी प्रमाण मिला। इसे औसत में नहीं छिपाया गया है।')}</p>}
    <dl className="grid gap-3 sm:grid-cols-2">{Object.keys(labels).map(key=>{const c=a.components[key];return <div key={key} className="min-w-0 rounded border bg-white p-3">
      <dt className="font-medium">{labels[key]?.[hi?1:0]||key}: {c.value===null?t('Unavailable','उपलब्ध नहीं'):`${Math.round(c.value*100)}%`}</dt>
      <dd className="mt-1 text-sm">{hi?hindi[key]||c.explanation:english[key]||c.explanation}</dd>
    </div>})}</dl>
    {a.status==='source_unavailable'&&<p>{t('Current source access changed. The historical assessment remains stored privately; its values and references are hidden.','स्रोत की वर्तमान अनुमति बदल गई है। पुराना आकलन निजी रूप से सुरक्षित है; उसके मान और संदर्भ नहीं दिखाए जाते।')}</p>}
    <details className="text-sm"><summary className="cursor-pointer">{t('Methods, counts and source scope','विधियाँ, गिनती और स्रोत का दायरा')}</summary>
      <p className="mt-2">{t('Saved snapshot','सुरक्षित आकलन')}: {a.saved_snapshot?t('Yes','हाँ'):t('No','नहीं')} · {a.method} {a.assessed_at&&`· ${a.assessed_at}`}</p>
      <p>{t('Coverage = cited displayed factual claims / displayed factual claims. No denominator means unavailable. The six weights are experimental; missing values are not filled or redistributed.','कवरेज = स्रोत वाले दिखाए गए तथ्यात्मक दावे / कुल दिखाए गए तथ्यात्मक दावे। कुल दावे शून्य हों तो माप उपलब्ध नहीं। छह भार प्रयोगात्मक हैं; गायब मान नहीं भरे जाते और भार नहीं बाँटे जाते।')}</p>
      <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify({components:a.components,counts:a.counts,source_references:a.source_references,limitations:a.limitations,aggregate_reason:a.aggregate_reason},null,2)}</pre>
    </details>
  </aside>
}
