import { useEffect, useState, type FormEvent } from 'react'
import Foundation from './App'
import DocumentAdmin from './DocumentAdmin'
import Search from './Search'
import Ask from './Ask'
import Analytics from './Analytics'
import AnswerLibrary from './AnswerLibrary'
import RecordPage from './RecordPage'
import PolicyQuote from './PolicyQuote'
import { translate } from './ui'
import { authorized, login, logout, register, restoreSession, subscribe, type User } from './auth'

const publicDemo = import.meta.env.VITE_PUBLIC_DEMO === 'true'

const inputClass = 'mt-2 w-full field-control'
const buttonClass = 'button-primary'
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'Request failed. Try again.'

export default function AuthApp() {
  const [user, setUser] = useState<User | null>(null)
  const [restoring, setRestoring] = useState(true)
  const [page, setPage] = useState(location.hash.slice(1) || 'home')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [languageBusy,setLanguageBusy]=useState(false)
  const [guestLanguage,setGuestLanguage]=useState<'en'|'hi'>(()=>localStorage.getItem('gov-policy-language')==='hi'?'hi':'en')
  useEffect(() => subscribe(setUser), [])
  useEffect(() => {
    let disposed = false
    restoreSession().catch((failure: unknown) => { if (!disposed) setError(messageOf(failure)) })
      .finally(() => { if (!disposed) setRestoring(false) })
    return () => { disposed = true }
  }, [])
  useEffect(() => {
    const onHash = () => { setPage(location.hash.slice(1) || 'home'); setError('') }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  async function signOut() {
    setBusy(true); setError('')
    try { await logout(); location.hash = 'login' } catch (failure) { setError(`Logout not completed: ${messageOf(failure)}`) }
    finally { setBusy(false) }
  }
  async function changeLanguage(language:'en'|'hi') {
    setError('')
    if(user){setLanguageBusy(true);try{setUser(await authorized<User>('/auth/me',{method:'PATCH',body:JSON.stringify({preferred_language:language})}))}catch(failure){setError(messageOf(failure))}finally{setLanguageBusy(false)}}
    else {localStorage.setItem('gov-policy-language',language);setGuestLanguage(language)}
  }
  const t=user?translate(user):(en:string,hi:string)=>guestLanguage==='en'?en:hi
  const [path,query]=page.split('?')
  const [route,id]=path.split('/')
  useEffect(() => {
    if (!restoring && user && (route==='login' || route==='register')) location.hash='ask'
  }, [restoring,user,route])
  const initialPage=Math.max(1,Number(new URLSearchParams(query).get('page'))||1)
  const links=[['ask','Ask & Research','प्रश्न पूछें','⌂'],['search','Search Passages','स्रोत खोजें','⌕'],['history','History','इतिहास','◷'],['saved','Saved Answers','सहेजे उत्तर','♧'],['account','Account','खाता','♙']]
  const pageNames:Record<string,[string,string]>={ask:['Ask & Research','सवाल और शोध'],search:['Search Passages','स्रोत खोज'],history:['History','इतिहास'],saved:['Saved Answers','सहेजे जवाब'],analytics:['Analytics','विश्लेषण'],admin:['Admin','प्रशासन'],account:['Account','खाता'],home:['Home','होम'],system:['System status','सिस्टम स्थिति'],login:['Sign in','लॉग इन'],register:['Register','रजिस्टर']}
  const pageName=pageNames[route]||[route[0]?.toUpperCase()+route.slice(1),route]
  function quickSearch(event:FormEvent<HTMLFormElement>) { event.preventDefault(); const query=new FormData(event.currentTarget).get('global-query')?.toString().trim(); location.hash=query?`search?query=${encodeURIComponent(query)}`:'search' }
  return <>
    <a className="skip-link" href="#main-content" onClick={e=>{e.preventDefault();document.getElementById('main-content')?.focus()}}>{t('Skip to content','मुख्य भाग पर जाएँ')}</a>
    <div className="workspace-shell">
    <aside className="sidebar"><a className="brand-link" href="#home"><span className="brand-mark brand-mark-image"><img src="/images/india-national-emblem.svg" alt="State Emblem of India — Lion Capital of Ashoka"/></span><span>Government<br/>Policy Assistant</span></a><p className="sidebar-subtitle">GOV-CS-028 · {t('Academic prototype · Historical Policy Library','शैक्षणिक प्रोटोटाइप · ऐतिहासिक नीति संग्रह')}</p>
      {user?<nav aria-label={t('Main navigation','मुख्य नेविगेशन')} className="sidebar-nav"><p className="sidebar-section-label">{t('WORKSPACE','कार्य क्षेत्र')}</p>{links.map(([key,en,hi,icon])=><a className="sidebar-link" aria-current={route===key?'page':undefined} key={key} href={`#${key}`}><span className="sidebar-icon" aria-hidden="true">{icon}</span>{t(en,hi)}</a>)}
        {user.role==='admin'&&!publicDemo&&<><p className="sidebar-section-label sidebar-section-spaced">{t('MANAGE','प्रबंधन')}</p><a className="sidebar-link" aria-current={route==='admin'?'page':undefined} href="#admin"><span className="sidebar-icon" aria-hidden="true">◇</span>{t('Admin','प्रशासन')}</a><a className="sidebar-link" aria-current={route==='analytics'?'page':undefined} href="#analytics"><span className="sidebar-icon" aria-hidden="true">▥</span>{t('Analytics','आँकड़े')}</a></>}
        <div className="sidebar-bottom"><a href="#system" className="sidebar-status"><i/> {t('Local system status','स्थानीय सिस्टम स्थिति')}</a><button className="sidebar-logout" disabled={busy} onClick={()=>void signOut()}>{t('Logout','लॉग आउट')} <span aria-hidden="true">↗</span></button></div>
      </nav>:<nav className="sidebar-nav"><a className="sidebar-link" href="#login">{t('Login','लॉग इन')}</a>{!publicDemo&&<a className="sidebar-link" href="#register">{t('Register','रजिस्टर')}</a>}</nav>}
      <div className="sidebar-language" role="group" aria-label={t('Choose interface language','इंटरफ़ेस की भाषा चुनें')}><button type="button" aria-pressed={(user?.preferred_language||guestLanguage)==='en'} disabled={languageBusy} onClick={()=>void changeLanguage('en')}>English</button><button type="button" aria-pressed={(user?.preferred_language||guestLanguage)!=='en'} disabled={languageBusy} onClick={()=>void changeLanguage('hi')}>हिन्दी</button></div>
      <div className="sidebar-motto"><span className="motto-rule"/><strong>{t('Policies for a stronger tomorrow','बेहतर कल के लिए नीतियाँ')}</strong><small>Evidence · Context · Clarity</small></div>
    </aside>
    <div className="app-frame"><header className="app-header"><div className="topbar"><form className="global-search" onSubmit={quickSearch}><span aria-hidden="true">⌕</span><input name="global-query" aria-label={t('Search documents and passages','दस्तावेज़ और स्रोत खोजें')} placeholder={t('Search documents, schemes and passages…','दस्तावेज़, योजनाएँ और स्रोत खोजें…')}/><button aria-label={t('Search','खोजें')}>↵</button></form><div className="topbar-user">{user?<><span className="user-avatar">{user.username.slice(0,1).toUpperCase()}</span><span className="user-name">{user.username}</span></>:<span className="project-label">GOV-CS-028</span>}</div></div><div className="breadcrumb"><a href="#home">{t('Home','होम')}</a><span>›</span><strong>{t(...pageName)}</strong></div></header>
    <main id="main-content" tabIndex={-1} className="app-main">
    {error&&<p role="alert" className="notice mb-4">{error}</p>}
    {restoring?<p role="status">{t('Restoring session…','सत्र खुल रहा है…')}</p>:route==='home'?<HomeDashboard user={user} t={t}/>
    :publicDemo&&['system','admin','analytics','register'].includes(route)?<p>{t('This page is available only in the private local installation.','यह पृष्ठ सिर्फ निजी स्थानीय स्थापना में उपलब्ध है।')}</p>:route==='system'?<Foundation/>:route==='login'||route==='register'?<AuthForm kind={route} onLogin={()=>{location.hash='ask'}} t={t}/>
    :!user?<GuestAccessPage t={t} route={route}/>
    :route==='ask'?<Ask user={user}/>:route==='search'?<Search user={user}/>
    :route==='history'||route==='saved'?id?<RecordPage key={id} user={user} id={id} library={route} backPage={initialPage}/>:<AnswerLibrary key={route} user={user} saved={route==='saved'} initialPage={initialPage}/>
    :route==='admin'?<AdminPage/>:route==='account'?<AccountPage user={user} onUpdate={setUser}/>:route==='analytics'?<Analytics user={user}/>:<p>{t('Page not found. Choose a page from the navigation.','पृष्ठ नहीं मिला। नेविगेशन से पृष्ठ चुनें।')}</p>}
    </main><footer className="app-footer"><p>{t('Academic prototype · historical evidence does not establish present eligibility.','शैक्षणिक परियोजना · ऐतिहासिक साक्ष्य वर्तमान पात्रता साबित नहीं करते।')}</p><span>GOV-CS-028</span></footer></div></div>
  </>
}

function HomeDashboard({user,t}:{user:User|null;t:(en:string,hi:string)=>string}) {
  const [sources,setSources]=useState<{version_id:string;title:string;eligible:boolean;applicability:string}[]>([])
  const [indexState,setIndexState]=useState('checking')
  const [serviceError,setServiceError]=useState(false)
  useEffect(()=>{let disposed=false;if(!user)return()=>{disposed=true};authorized<{state:string;sources:{version_id:string;title:string;eligible:boolean;applicability:string}[]}>('/search/status')
    .then(v=>{if(!disposed){setSources(v.sources.filter(s=>s.eligible));setIndexState(v.state)}}).catch(()=>{if(!disposed)setServiceError(true)});return()=>{disposed=true}},[user])
  const suggested=['What financial support is described in the PM Internship Scheme factsheet?','What one-time grant was planned for interns after joining?']
  function submitQuestion(event:FormEvent<HTMLFormElement>){event.preventDefault();const question=new FormData(event.currentTarget).get('question')?.toString().trim();location.hash=question?`ask?question=${encodeURIComponent(question)}`:'ask'}
  function askSuggested(question:string){location.hash=`ask?question=${encodeURIComponent(question)}`}
  return <section className="home-dashboard"><div className="home-overview"><div className="home-primary"><div className="home-hero"><img className="hero-illustration" src="/images/policy-hero-watercolor.png" alt=""/><div className="hero-copy"><p className="eyebrow">{t('EVIDENCE FROM REVIEWED DOCUMENTS','जाँचे गए दस्तावेज़ों से साक्ष्य')}</p><h1>{t('Ask. Explore.','पूछें। खोजें।')} <em>{t('Understand.','समझें।')}</em></h1><p>{t('Explore historical government policy sources and get answers with citations you can inspect.','ऐतिहासिक सरकारी नीति स्रोत देखें और ऐसे जवाब पाएँ जिनके citations आप जाँच सकें।')}</p></div>
        {user&&<form className="home-question-box" onSubmit={submitQuestion}><label className="sr-only" htmlFor="home-question">{t('Ask a question','सवाल पूछें')}</label><textarea id="home-question" name="question" rows={2} maxLength={2000} placeholder={t('Ask about a scheme, policy or government document…','किसी योजना, नीति या सरकारी दस्तावेज़ के बारे में पूछें…')}/><div className="home-question-actions"><span>{t('Use a scheme name and document date for a more focused answer.','सटीक जवाब के लिए योजना का नाम और दस्तावेज़ की तारीख लिखें।')}</span><button className="button-primary" type="submit">{t('Ask sources','स्रोत से पूछें')} <span aria-hidden="true">→</span></button></div></form>}
        <p className="hero-disclaimer">{t('Historical sources do not establish current eligibility or application advice.','ऐतिहासिक स्रोत वर्तमान पात्रता या आवेदन सलाह साबित नहीं करते।')}</p></div>
      <div className="home-suggestions"><div className="suggestions-heading"><div><p className="eyebrow">{t('TRY A QUESTION','यह सवाल पूछकर देखें')}</p><h2>{t('Start your research','शोध शुरू करें')}</h2></div><a href={user?'#search':'#login'}>{t('Search passages','स्रोत खोजें')} →</a></div><div className="suggestion-list">{suggested.map(q=><button key={q} onClick={()=>askSuggested(q)}>{q}<span aria-hidden="true">→</span></button>)}</div></div>
      <div className="home-quick-grid"><a href={user?'#search':'#login'} className="home-quick-card"><span className="quick-icon">⌕</span><strong>{t('Search exact source passages','स्रोत के सटीक अंश खोजें')}</strong><span aria-hidden="true">→</span></a><a href={user?'#history':'#login'} className="home-quick-card"><span className="quick-icon">◷</span><strong>{t('Browse your research history','अपने शोध का इतिहास देखें')}</strong><span aria-hidden="true">→</span></a><a href={user?'#saved':'#login'} className="home-quick-card"><span className="quick-icon">♧</span><strong>{t('Return to saved answers','सहेजे जवाब फिर से देखें')}</strong><span aria-hidden="true">→</span></a></div>
      </div><aside className="home-sidebar"><article className="card recent-sources-card"><div className="side-card-heading"><div><p className="eyebrow">{t('YOUR SOURCE LIBRARY','आपके स्रोत')}</p><h2>{t('Recent sources','हाल के स्रोत')}</h2></div><a href={user?'#search':'#login'}>{t('View all','सभी देखें')} →</a></div>
        {serviceError?<p role="status" className="muted">{t('Source list is unavailable right now.','स्रोत सूची अभी उपलब्ध नहीं है।')}</p>:!user?<p className="muted">{t('Sign in to view your sources.','स्रोत देखने के लिए लॉग इन करें।')}</p>:indexState==='checking'?<p role="status" className="muted">{t('Loading reviewed sources…','जाँचे गए स्रोत लोड हो रहे हैं…')}</p>:sources.length?<ul className="recent-source-list">{sources.slice(0,4).map(source=><li key={source.version_id}><span className="source-file-icon">PDF</span><div><strong>{source.title}</strong><small>{source.applicability==='historical'?t('Historical source snapshot','ऐतिहासिक स्रोत'):source.applicability.replaceAll('_',' ')}</small></div><a href={`#search?query=${encodeURIComponent(source.title)}`} aria-label={`${t('Search source','स्रोत खोजें')}: ${source.title}`}>→</a></li>)}</ul>:<p className="muted">{t('No reviewed sources are ready for search yet.','खोज के लिए अभी कोई जाँचा स्रोत तैयार नहीं है।')}</p>}
        <a className="source-library-link" href={user?'#search':'#login'}>{t('Open source search','स्रोत खोज खोलें')} <span>→</span></a></article>
        <article className="card workspace-stats-card"><div className="side-card-heading"><div><p className="eyebrow">{t('WORKSPACE OVERVIEW','कार्यक्षेत्र')}</p><h2>{t('At a glance','एक नज़र में')}</h2></div><span className={`service-pill ${indexState==='ready'?'is-ready':''}`}><i/>{indexState==='checking'?t('Checking','जाँच'):indexState==='ready'?t('Ready','तैयार'):t('Index offline','इंडेक्स बंद')}</span></div><div className="workspace-stat"><span className="quick-icon">▤</span><strong>{sources.length}</strong><small>{t('reviewed sources','जाँचे गए स्रोत')}</small></div><div className="workspace-stat"><span className="quick-icon">文</span><strong>2</strong><small>{t('question languages: English and Hindi','सवाल की भाषाएँ: English और Hindi')}</small></div><p className="stat-footnote">{t('Only verified, eligible historical sources appear here.','यहाँ सिर्फ सत्यापित और पात्र ऐतिहासिक स्रोत दिखते हैं।')}</p></article>
        <article className="home-caution-card"><span aria-hidden="true">ⓘ</span><p>{t('Check the cited page and date. Historical answers are not current application advice.','Citation वाला पेज और तारीख जाँचें। ऐतिहासिक जवाब वर्तमान आवेदन सलाह नहीं हैं।')}</p></article><PolicyQuote hindi={user?.preferred_language!=='en'&&!!user}/>
      </aside></div><p className="home-signature">{t('Evidence · Context · Clarity','साक्ष्य · संदर्भ · स्पष्टता')}</p></section>
}

function GuestAccessPage({t,route}:{t:(en:string,hi:string)=>string;route:string}) {
  const label=route==='ask'?t('Ask & Research','सवाल और शोध'):route==='search'?t('Search Passages','स्रोत खोज'):route==='history'?t('Research history','शोध इतिहास'):route==='saved'?t('Saved answers','सहेजे जवाब'):t('This workspace page','यह कार्यक्षेत्र पृष्ठ')
  const hindi=t('English','हिन्दी')==='हिन्दी'
  return <section className="guest-access-layout"><div className="guest-access-card"><div className="guest-access-art"><img src="/images/policy-hero-watercolor.png" alt=""/><span>{t('EVIDENCE. CONTEXT. CLARITY.','साक्ष्य। संदर्भ। स्पष्टता।')}</span></div><div className="guest-access-copy"><p className="eyebrow">{t('PRIVATE POLICY RESEARCH','निजी नीति शोध')}</p><h1>{t('Sign in to continue','आगे बढ़ने के लिए लॉग इन करें')}</h1><p>{t(`Sign in to open ${label} and keep your private research linked to your account.`,`अपने खाते से जुड़ा निजी शोध खोलने के लिए ${label} पर लॉग इन करें।`)}</p><a className="button-primary" href="#login">{t('Continue to sign in','लॉग इन करें')} <span aria-hidden="true">→</span></a><a className="guest-home-link" href="#home">{t('Back to workspace overview','कार्यक्षेत्र के मुख्य पृष्ठ पर जाएँ')}</a><small>{t('This academic prototype is not an official Government of India service.','यह शैक्षणिक प्रोटोटाइप भारत सरकार की आधिकारिक सेवा नहीं है।')}</small></div></div><aside className="guest-access-side"><PolicyQuote hindi={hindi}/></aside></section>
}

function AuthForm({ kind, onLogin, t }: { kind: 'login' | 'register'; onLogin: () => void;t:(en:string,hi:string)=>string }) {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => { setPassword(''); setError(''); setNotice('') }, [kind])
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try {
      if (kind === 'register') {
        await register(email, username, password); setPassword('')
        setNotice(t('Account created. Use the Login page to sign in.','खाता बन गया। लॉग इन पेज से प्रवेश करें।'))
      } else { await login(email, password); setPassword(''); onLogin() }
    } catch (failure) { setError(messageOf(failure)) }
    finally { setBusy(false) }
  }
  return <section className="auth-card">
    <p className="eyebrow">GOV-CS-028 · {t('Academic prototype','शैक्षणिक प्रोटोटाइप')}</p><h1>{kind === 'register' ? t('Create your account','अपना खाता बनाएँ') : t('Welcome back','वापसी पर स्वागत है')}</h1>
    <p className="muted">{kind === 'register' ? t('Create a regular user account for this workspace.','इस कार्यक्षेत्र के लिए सामान्य उपयोगकर्ता खाता बनाएँ।') : t('Sign in with your registered email and password.','अपने पंजीकृत email और password से लॉग इन करें।')}</p>
    {publicDemo && <p className="mt-3 text-sm text-slate-600">{t("Use the email registered in this laptop's native installation. Public account creation is closed; ask the demo owner for an ordinary account. Administrator pages stay private.",'इस laptop की local installation में registered email इस्तेमाल करें। Public account creation बंद है; सामान्य खाते के लिए demo owner से संपर्क करें। Admin pages private रहते हैं।')}</p>}
    <form onSubmit={(event) => void submit(event)} className="auth-form">
      <label className="block">{t('Email address','ईमेल पता')}<input className={inputClass} type="email" required maxLength={254} autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      {kind === 'register' && <label className="block">{t('Username','यूज़रनेम')}<input className={inputClass} required minLength={3} maxLength={32} pattern="[A-Za-z0-9_]{3,32}" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /><span className="text-xs text-slate-500">{t('3–32 letters, digits or underscores. Stored in lowercase.','3–32 अक्षर, अंक या underscore। lowercase में सुरक्षित होगा।')}</span></label>}
      <label className="block">{t('Password','पासवर्ड')}<input className={inputClass} type="password" required minLength={kind === 'register' ? 12 : 1} maxLength={128} autoComplete={kind === 'register' ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} /><span className="text-xs text-slate-500">{kind === 'register' && t('12–128 characters; passwords are never truncated.','12–128 अक्षर; password काटा नहीं जाएगा।')}</span></label>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      {notice && <p role="status" className="text-sm text-teal-800">{notice} <a href="#login" className="underline">{t('Login','लॉग इन')}</a></p>}
      <button className={buttonClass} disabled={busy}>{busy ? t('Please wait…','कृपया प्रतीक्षा करें…') : kind === 'register' ? t('Create account','खाता बनाएँ') : t('Sign in','लॉग इन')} <span aria-hidden="true">→</span></button>
    </form>
  </section>
}

function AccountPage({ user, onUpdate }: { user: User; onUpdate: (user: User) => void }) {
  const t=translate(user)
  const [language, setLanguage] = useState(user.preferred_language)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(()=>setLanguage(user.preferred_language),[user.preferred_language])
  useEffect(() => {
    let disposed = false
    authorized<User>('/auth/me').then((result) => { if (!disposed) onUpdate(result) })
      .catch((failure: unknown) => { if (!disposed) setError(messageOf(failure)) })
    return () => { disposed = true }
  }, [onUpdate])
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try { const result = await authorized<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ preferred_language: language }) }); onUpdate(result); setNotice('Profile saved.') }
    catch (failure) { setError(messageOf(failure)) } finally { setBusy(false) }
  }
  return <section className="page-stack account-page"><div className="page-heading"><div><p className="eyebrow">{t('PROFILE & PREFERENCES','प्रोफ़ाइल और पसंद')}</p><h1>{t('Your account','आपका खाता')}</h1><p className="muted">{t('Manage your profile details and answer language for this workspace.','इस कार्यक्षेत्र के लिए प्रोफ़ाइल और जवाब की भाषा बदलें।')}</p></div></div>
    <div className="account-layout"><article className="card account-profile-card"><div className="account-profile-head"><span className="account-avatar">{user.username.slice(0,1).toUpperCase()}</span><div><h2>{user.username}</h2><span className="role-badge">{user.role==='admin'?t('Administrator','प्रशासक'):t('Research user','शोध उपयोगकर्ता')}</span></div></div><p className="muted">{t('Member since','सदस्य बने')} {new Date(user.created_at).toLocaleDateString(user.preferred_language==='en'?'en-IN':'hi-IN',{year:'numeric',month:'long',day:'numeric'})}</p><dl className="profile-details"><div><dt>{t('Username','यूज़रनेम')}</dt><dd>{user.username}</dd></div><div><dt>{t('Email address','ईमेल पता')}</dt><dd>{user.email}</dd></div><div><dt>{t('Account role','खाते की भूमिका')}</dt><dd>{user.role}</dd></div></dl></article>
      <article className="card preference-card"><div className="preference-heading"><span className="quick-icon">文</span><div><p className="eyebrow">{t('DISPLAY PREFERENCE','दिखाने की पसंद')}</p><h2>{t('Answer language','जवाब की भाषा')}</h2></div></div><p className="muted">{t('Choose the default language for generated answers. You can still change it for each question.','बनाए गए जवाबों की डिफ़ॉल्ट भाषा चुनें। हर सवाल के लिए इसे अलग से भी बदल सकते हैं।')}</p><form className="preference-form" onSubmit={(event) => void save(event)}><label className="field-label">{t('Preferred language','पसंदीदा भाषा')}<select className={inputClass} value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="hi">हिन्दी</option><option value="hinglish">Hinglish</option></select></label><button className={buttonClass} disabled={busy}>{busy ? t('Saving…','सहेज रहा है…') : t('Save preference','पसंद सहेजें')} <span aria-hidden="true">→</span></button></form>
        {error&&<p role="alert" className="error-banner">{error}</p>}{notice&&<p role="status" className="success-banner">{notice}</p>}</article></div>
    <article className="account-note"><span aria-hidden="true">ⓘ</span><p>{t('This account is private to your local policy research workspace. Historical source access may change if a document review is updated.','यह खाता आपके निजी नीति शोध कार्यक्षेत्र के लिए है। दस्तावेज़ समीक्षा बदलने पर ऐतिहासिक स्रोतों की उपलब्धता बदल सकती है।')}</p></article>
  </section>
}

function AdminPage() {
  const [status, setStatus] = useState('Checking server authorization…')
  useEffect(() => {
    let disposed = false
    authorized<{ authorized: boolean; role: string }>('/auth/admin/access')
      .then((result) => { if (!disposed) setStatus(result.authorized ? 'Admin access confirmed by the backend.' : 'Access denied.') })
      .catch((failure: unknown) => { if (!disposed) setStatus(messageOf(failure)) })
    return () => { disposed = true }
  }, [])
  return <section aria-label="Admin workspace">{status === 'Admin access confirmed by the backend.'
    ? <><p role="status" className="sr-only">{status}</p><DocumentAdmin /></>
    : <div><h1 className="text-3xl font-semibold">Admin access</h1><p role="status" className="mt-5">{status}</p></div>}</section>
}
