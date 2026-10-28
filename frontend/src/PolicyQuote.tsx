export default function PolicyQuote({hindi=false}:{hindi?:boolean}) {
  return <section className="card policy-quote-card" aria-label={hindi?'भारत के लिए बेहतर नीतियाँ':'Better policies for India'}>
    <span className="policy-quote-mark" aria-hidden="true">“</span>
    <p>{hindi?<>बेहतर नीतियाँ<br/>एक मज़बूत और<br/>समावेशी भारत के लिए।</>:<>Better policies<br/>for a stronger,<br/>more inclusive India.</>}</p>
    <span className="policy-quote-tricolour" aria-hidden="true"><i/><i/><i/></span>
    <img src="/images/india-national-emblem.svg" alt="State Emblem of India — Lion Capital of Ashoka"/>
    <small>{hindi?'शैक्षणिक नीति शोध कार्यक्षेत्र':'Academic policy research workspace'}</small>
  </section>
}
