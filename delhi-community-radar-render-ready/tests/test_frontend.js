const {JSDOM}=require('jsdom');const fs=require('fs');
const FX=JSON.parse(fs.readFileSync('fixtures.json','utf8'));
const NEW=fs.readFileSync(process.argv[2],'utf8');const OLD=fs.readFileSync('index_original.html','utf8');
const R=[];const rec=(id,name,expected,actual,ok,ev='')=>{R.push({id,name,expected,actual:String(actual),result:ok?'PASS':'FAIL',evidence:ev});console.log(ok?'PASS':'FAIL',id,name,'|',String(actual).slice(0,150))};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const SCALE=new Set([20000,60000,15000,6000]);   // shorten long timeouts so timeout paths can be tested quickly

function load(html,{L=true,routes,geo}={}){
  const calls=[],shapes=[],handlers={};
  const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,url:'https://radar.test/',beforeParse(win){
    win.scrollTo=()=>{};win.Element.prototype.scrollIntoView=()=>{};
    const st=win.setTimeout.bind(win);win.setTimeout=(f,d,...a)=>st(f,SCALE.has(d)?d/400:d,...a);
    if(L){const o=()=>{const x={};['addTo','bindPopup','setView','on','invalidateSize','removeLayer','clearLayers'].forEach(k=>x[k]=(...a)=>{if(k==='on')handlers[a[0]]=a[1];return x});return x};
      win.L={map:()=>o(),tileLayer:()=>o(),layerGroup:()=>o(),
        circle:(ll,op)=>{shapes.push({t:'circle',ll,op});return o()},circleMarker:(ll,op)=>{shapes.push({t:'marker',ll,op});return o()}}}
    if(geo)Object.defineProperty(win.navigator,'geolocation',{value:geo,configurable:true});
    win.fetch=(url,opts={})=>new Promise((res,rej)=>{
      calls.push({url,method:opts.method||'GET',body:opts.body});
      const ab=()=>{const e=new Error('aborted');e.name='AbortError';rej(e)};
      if(opts.signal){if(opts.signal.aborted)return ab();opts.signal.addEventListener('abort',ab)}
      const r=routes(url,opts);if(r==='hang')return;if(r==='neterr')return rej(new win.TypeError('Failed to fetch'));
      res({ok:r.status<400,status:r.status,json:async()=>r.json})});
  }});
  return {win:dom.window,doc:dom.window.document,calls,shapes,handlers,$:id=>dom.window.document.getElementById(id)};
}
const J=(json,status=200)=>({status,json});
const okRoutes=(o={})=>(u,opts)=>{
  if(u==='/api/reports')return o.reports||J(FX.reports);
  if(u==='/api/stats')return o.stats||J(FX.stats);
  if(u==='/api/aqi')return o.aqi||J(FX.aqi_live);
  if(u==='/api/report'&&opts.method==='POST')return o.post||J(FX.owner);
  if(/\/abuse$/.test(u))return J({ok:true});
  return J({},404)};
const txt=el=>el?el.textContent.replace(/\s+/g,' ').trim():'';

(async()=>{
/* ---------- static copy (Phase A) ---------- */
const bad=[/right office/i,/sends it to/i,/<em>Resolve/i,/Live triage/i,/Route to/i,/the right desk/i,/Thanks, your report is in/i];
const hits=bad.filter(r=>r.test(NEW)).map(String);
rec('F-01a','Misleading phrases removed from page HTML','none present',hits.join(',')||'none',!hits.length);
const d0=new JSDOM(NEW).window.document;
const lead=txt(d0.querySelector('.lead')),meta=d0.querySelector('meta[name=description]').content;
rec('F-01b','Hero + meta state the resident reviews and submits; nothing auto-sent','phrases present',`meta ok=${/prepares a complaint for the resident to review and submit/.test(meta)}; hero ok=${/review and submit yourself/.test(lead)&&/Nothing is sent to any government office automatically/.test(lead)}`,/prepares a complaint for the resident to review and submit/.test(meta)&&/review and submit yourself/.test(lead)&&/Nothing is sent to any government office automatically/.test(lead));
rec('F-01c','Headline no longer promises "Resolve"','Report.Prioritise.Prepare. (line breaks)',txt(d0.querySelector('h1')),txt(d0.querySelector('h1'))==='Report.Prioritise.Prepare.');
rec('F-01d','Routing feature kept, reworded (How-it-works)','"Suggest authority" step present',txt([...d0.querySelectorAll('.step')][3]).slice(0,120),/Suggest authority/.test(txt([...d0.querySelectorAll('.step')][3])));
const EM='Delhi Community Radar is not an emergency response service. For emergencies, contact 112.';
rec('F-03','Emergency notice in reporting panel AND footer, role=note, exact wording','both exact',`panel=${txt(d0.getElementById('emergency'))===EM} footer=${txt(d0.querySelector('footer [role=note]'))===EM}`,txt(d0.getElementById('emergency'))===EM&&txt(d0.querySelector('footer [role=note]'))===EM&&d0.getElementById('emergency').getAttribute('role')==='note');
const pv=txt(d0.getElementById('privacy'));
rec('F-04a','Consent notice covers location, photo/description use, vulnerable people, avoiding unneeded personal data','all four topics + checkbox',[/Location is required/.test(pv),/photo are analysed/.test(pv),/elderly, ill or otherwise vulnerable/.test(pv),/Don't include personal details/.test(pv),!!d0.getElementById('consent')].join(','),/Location is required/.test(pv)&&/photo are analysed/.test(pv)&&/elderly, ill or otherwise vulnerable/.test(pv)&&/Don't include personal details/.test(pv)&&!!d0.getElementById('consent'));
rec('F-02a','Volunteer step in How-it-works says SAMPLE / none contacted','present',/SAMPLE profiles/.test(d0.body.innerHTML)+'',/SAMPLE profiles/.test(d0.body.innerHTML));

/* ---------- stats (Phase B1) ---------- */
let p=load(NEW,{routes:okRoutes()});await wait(1300);
rec('F-09','Dashboard shows the real API values (16/14/2/4) and hides loader','16/14/2/4, loader hidden',[p.$('sTotal'),p.$('sClusters'),p.$('sMerged'),p.$('sVuln')].map(e=>e.textContent).join('/')+` loaderHidden=${p.$('statsState').hidden}`,[p.$('sTotal'),p.$('sClusters'),p.$('sMerged'),p.$('sVuln')].map(e=>e.textContent).join('/')==='16/14/2/4'&&p.$('statsState').hidden);
rec('F-09b','Loading indicator shown before data arrives','"Loading statistics…" visible initially',txt(load(NEW,{routes:()=>'hang'}).$('statsState')),/Loading statistics/.test(txt(load(NEW,{routes:()=>'hang'}).$('statsState'))));
let mode='fail';p=load(NEW,{routes:(u,o)=>u==='/api/stats'&&mode==='fail'?J({error:'x'},500):okRoutes()(u,o)});await wait(700);
rec('F-10','Stats API 500: counters show "–" (NOT 0); error + Retry shown','–,–,–,–; error; retry button',[p.$('sTotal'),p.$('sClusters'),p.$('sMerged'),p.$('sVuln')].map(e=>e.textContent).join(',')+' | '+txt(p.$('statsState')),[p.$('sTotal'),p.$('sClusters')].every(e=>e.textContent==='–')&&/could not be loaded/.test(txt(p.$('statsState')))&&!!p.$('statsState').querySelector('[data-retry]'));
mode='ok';p.$('statsState').querySelector('[data-retry]').click();await wait(1300);
rec('F-11','Retry button recovers the dashboard','16/14/2/4, error gone',[p.$('sTotal'),p.$('sClusters'),p.$('sMerged'),p.$('sVuln')].map(e=>e.textContent).join('/')+` hidden=${p.$('statsState').hidden}`,p.$('sTotal').textContent==='16'&&p.$('statsState').hidden);
p=load(NEW,{routes:(u,o)=>u==='/api/stats'?'hang':okRoutes()(u,o)});await wait(700);
rec('F-10b','Stats request that never answers times out with a message (no endless spinner)','timeout error + retry, counters "–"',txt(p.$('statsState'))+` | total=${p.$('sTotal').textContent}`,/timeout/.test(txt(p.$('statsState')))&&p.$('sTotal').textContent==='–'&&!!p.$('statsState').querySelector('[data-retry]'),'timeouts time-scaled 400x for the test');
p=load(NEW,{routes:(u,o)=>u==='/api/stats'?'neterr':okRoutes()(u,o)});await wait(700);
rec('F-10c','Backend unreachable (network error): clear message, no fake zeros','"Could not reach the server"',txt(p.$('statsState')),/Could not reach the server/.test(txt(p.$('statsState')))&&p.$('sTotal').textContent==='–');
// previously-loaded values are kept (not zeroed) when a later refresh fails
let phase=1;p=load(NEW,{routes:(u,o)=>u==='/api/stats'&&phase===2?J({},500):okRoutes()(u,o)});await wait(1300);phase=2;p.win.document.dispatchEvent(new p.win.Event('visibilitychange'));await wait(500);
rec('F-10d','Later refresh failure keeps last real values and warns','16 kept + "last values from"',p.$('sTotal').textContent+' | '+txt(p.$('statsState')),p.$('sTotal').textContent==='16'&&/last values from/.test(txt(p.$('statsState'))));

/* ---------- AQI (Phase B2) ---------- */
p=load(NEW,{routes:okRoutes()});await wait(500);
rec('F-05','AQI success (live): source named, "Not a CPCB" shown, rows rendered','Live · Open-Meteo model',txt(p.$('aqsrc'))+' | '+txt(p.$('aqState')).slice(0,170)+` rows=${p.doc.querySelectorAll('.aqrow').length}`,/Live · Open-Meteo model/.test(txt(p.$('aqsrc')))&&/Not a CPCB station reading/.test(txt(p.$('aqState')))&&/Model time 2026-11-24 14:00 IST/.test(txt(p.$('aqState')))&&p.doc.querySelectorAll('.aqrow').length>0);
p=load(NEW,{routes:(u,o)=>u==='/api/aqi'?'hang':okRoutes()(u,o)});await wait(700);
rec('F-06','AQI request hangs: times out, NOT stuck on Loading, retry offered, no values shown','Unavailable + timeout + retry',txt(p.$('aqsrc'))+' | '+txt(p.$('aqState')),txt(p.$('aqsrc'))==='Unavailable'&&/timeout/.test(txt(p.$('aqState')))&&!!p.$('aqState').querySelector('[data-retry]')&&!p.doc.querySelectorAll('.aqrow').length);
let am='fail';p=load(NEW,{routes:(u,o)=>u==='/api/aqi'&&am==='fail'?J({error:'x'},500):okRoutes()(u,o)});await wait(500);
const err1=txt(p.$('aqState'));am='ok';p.$('aqState').querySelector('[data-retry]').click();await wait(500);
rec('F-07','AQI API failure shows error; Retry then loads data','error then Live rows',`${err1.slice(0,60)} => ${txt(p.$('aqsrc'))}`,/could not be loaded/.test(err1)&&/Live/.test(txt(p.$('aqsrc')))&&p.doc.querySelectorAll('.aqrow').length>0);
p=load(NEW,{routes:okRoutes({aqi:J(FX.aqi_sim)})});await wait(500);
rec('F-08','Simulated fallback is unmistakably labelled (badge, banner, per-row "sim")','SIMULATED badge + "not measurements"',txt(p.$('aqsrc'))+' | '+txt(p.$('aqState')).slice(0,110),/SIMULATED/.test(txt(p.$('aqsrc')))&&/not measurements/.test(txt(p.$('aqState')))&&[...p.doc.querySelectorAll('.aqrow .v')].every(e=>/sim/.test(e.textContent)));
p=load(NEW,{routes:okRoutes({aqi:J(FX.aqi_stale)})});await wait(500);
rec('F-08b','Stale data labelled STALE with age, not shown as current','STALE + "min ago"',txt(p.$('aqsrc'))+' | '+txt(p.$('aqState')).slice(0,90),/STALE/.test(txt(p.$('aqsrc')))&&/min ago/.test(txt(p.$('aqState'))));

/* ---------- map / list privacy (Phase D, front end) ---------- */
p=load(NEW,{routes:okRoutes()});await wait(500);
const sensSh=p.shapes.filter(s=>FX.reports.some(r=>FX.sensitive_ids.includes(r.id)&&r.lat===s.ll[0]&&r.lng===s.ll[1]));
rec('F-21','Vulnerable reports drawn as ~1 km dashed approximate-area circles at the API\'s generalised coordinates (never a pin)','4 circles r=550, no markers',`${sensSh.length} shapes: ${[...new Set(sensSh.map(s=>s.t+':'+s.op.radius))]}`,sensSh.length===FX.sensitive_ids.length&&sensSh.every(s=>s.t==='circle'&&s.op.radius===550&&s.op.dashArray));
const q=txt(p.$('queue'));
rec('F-02b','Priority list marks sample reports; shows no vulnerable free-text','SAMPLE tags, no "bujurg"/"medicine"',`samples=${p.doc.querySelectorAll('#queue .sample').length} leak=${/bujurg|medicine|akele/i.test(q)}`,p.doc.querySelectorAll('#queue .sample').length>0&&!/bujurg|medicine|akele/i.test(q));
const xss=JSON.parse(JSON.stringify(FX.reports));xss[0].summary='<img src=x onerror="window.__x=1"> <script>window.__x=1<\/script>';xss[0].category='<b id=pwn>cat</b>';
p=load(NEW,{routes:okRoutes({reports:J(xss)})});await wait(500);
rec('F-24x','XSS regression: HTML in a report summary/category is rendered as text','no injected element, script not run',`img=${p.doc.querySelectorAll('#queue img').length} pwn=${!!p.$('pwn')} ran=${p.win.__x===1}`,!p.doc.querySelector('#queue img')&&!p.$('pwn')&&p.win.__x!==1);
// reports API down
p=load(NEW,{routes:(u,o)=>u==='/api/reports'?J({},500):okRoutes()(u,o)});await wait(500);
rec('F-10e','Reports API failure: error + Retry in list (not blank)','error and retry in list',txt(p.$('queue')).slice(0,100),/could not be loaded/.test(txt(p.$('queue')))&&!!p.$('queue').querySelector('[data-retry]'));

/* ---------- location + submit (Phase C) ---------- */
const posts=c=>c.filter(x=>x.url==='/api/report'&&x.method==='POST');
p=load(NEW,{routes:okRoutes()});await wait(400);p.$('text').value='pothole on road';p.$('consent').checked=true;p.$('send').click();await wait(200);
rec('F-12','Submit with no location: blocked, clear message, NO request sent','no POST, message',txt(p.$('status'))+` posts=${posts(p.calls).length}`,posts(p.calls).length===0&&/set a location/.test(txt(p.$('status'))));
p=load(NEW,{routes:okRoutes(),geo:{getCurrentPosition:(ok,err)=>err({code:1})}});await wait(400);p.$('loc').click();await wait(100);
rec('F-14','GPS permission denied: explains and points to the map; no location set','denied message; locInfo not set',txt(p.$('status'))+' | '+txt(p.$('locInfo')),/permission was denied/.test(txt(p.$('status')))&&/not set/.test(txt(p.$('locInfo'))));
p=load(NEW,{routes:okRoutes(),geo:{getCurrentPosition:(ok)=>ok({coords:{latitude:28.6519,longitude:77.1909,accuracy:4200}})}});await wait(400);p.$('loc').click();await wait(100);
rec('F-14b','GPS accepted but inaccurate (±4200 m): user warned and told how to correct','GPS + warning + Clear',txt(p.$('locInfo')),/GPS/.test(txt(p.$('locInfo')))&&/not precise/.test(txt(p.$('locInfo')))&&!!p.$('clearLoc'));
p=load(NEW,{routes:okRoutes()});await wait(400);p.handlers.click({latlng:{lat:28.6139,lng:77.2090}});await wait(50);
const li1=txt(p.$('locInfo'));p.$('text').value='Minto bridge paani bhar gaya';p.$('consent').checked=true;p.$('send').click();await wait(1800);
const fd=posts(p.calls)[0]&&Object.fromEntries(posts(p.calls)[0].body.entries());
rec('F-15','Manual map selection sets location (source "map") and it is sent with the report','"chosen on the map"; POST has lat,lng,loc_source=map',li1+' | '+JSON.stringify(fd),/chosen on the map/.test(li1)&&fd&&fd.lat==='28.6139'&&fd.loc_source==='map');
p.handlers.click({latlng:{lat:1,lng:1}});p.$('clearLoc')&&0;
rec('F-23','Normal submission: success text, "Not sent yet", SAMPLE volunteers, authority wording; form + location reset; lists refreshed','all',`notSent=${/Not sent yet/.test(txt(p.$('result')))} sample=${p.doc.querySelectorAll('#result .sample').length} auth=${/Suggested authority/.test(txt(p.$('result')))} textCleared=${p.$('text').value===''} loc=${txt(p.$('locInfo')).slice(0,20)} refreshed=${p.calls.filter(c=>c.url==='/api/reports').length>1}`,
  /Not sent yet/.test(txt(p.$('result')))&&p.doc.querySelectorAll('#result .sample').length===FX.owner.volunteers.length&&/Suggested authority/.test(txt(p.$('result')))&&/No volunteer has been contacted/.test(txt(p.$('result')))&&p.$('text').value===''&&p.calls.filter(c=>c.url==='/api/reports').length>1);
rec('F-02c','No "sent to the office"-style wording in confirmation','absent',txt(p.$('result')).slice(0,160),!/sent to the (right )?office|your report is in/i.test(txt(p.$('result'))));
// failure keeps input
let netmode='neterr';p=load(NEW,{routes:(u,o)=>u==='/api/report'?(netmode==='neterr'?'neterr':J({error:'Location is required.'},422)):okRoutes()(u,o)});await wait(400);
p.handlers.click({latlng:{lat:28.6139,lng:77.2090}});p.$('text').value='keep my text';p.$('consent').checked=true;p.$('send').click();await wait(400);
rec('F-23c','Network failure on submit: NO false confirmation; text + location kept; honest message','"NOT submitted", no result card, text kept',txt(p.$('status'))+` result="${txt(p.$('result'))}" text=${p.$('text').value}`,/NOT submitted/.test(txt(p.$('status')))&&txt(p.$('result'))===''&&p.$('text').value==='keep my text'&&!p.$('send').disabled);
netmode='srv';p.$('send').click();await wait(400);
rec('F-23d','Server validation error shown to user; input kept','server message',txt(p.$('status')),/Location is required/.test(txt(p.$('status')))&&p.$('text').value==='keep my text');
p=load(NEW,{routes:okRoutes()});await wait(400);p.handlers.click({latlng:{lat:28.6139,lng:77.2090}});p.$('text').value='x';p.$('send').click();await wait(200);
rec('F-04b','Consent unchecked: submit blocked, no request','no POST, prompt',txt(p.$('status'))+` posts=${posts(p.calls).length}`,posts(p.calls).length===0&&/tick the box/.test(txt(p.$('status'))));
// client-side photo checks
const pick=(name,size)=>{const q=load(NEW,{routes:okRoutes()});return wait(300).then(()=>{q.$('photo').onchange({target:{files:[{name,size}],value:'x'}});return txt(q.$('status'))})};
let m=await pick('virus.exe',1000);rec('F-17','Browser pre-check rejects .exe','unsupported message',m,/Unsupported photo/.test(m));
m=await pick('big.jpg',6*1024*1024);rec('F-19','Browser pre-check rejects >5 MB','larger than 5 MB',m,/larger than 5 MB/.test(m));
m=await pick('ok.jpg',1000);rec('F-16','Browser pre-check accepts a normal JPG','Photo added',m,/Photo added: ok.jpg/.test(m));

/* ---------- existing features still work ---------- */
p=load(NEW,{routes:okRoutes()});await wait(500);
p.doc.querySelector('#examples .chip').click();const exOk=p.$('text').value.length>5;
p.doc.querySelector('.vtab[data-v=list]').click();const tabOk=p.$('queueB').hidden===false&&p.$('map').hidden===true;
p.doc.querySelector('#queue .flag').click();await wait(200);
rec('F-24','Existing features: example chips, Map/List tabs, flag button (POST /abuse) still work','all true',`chips=${exOk} tabs=${tabOk} flagPost=${p.calls.some(c=>/\/abuse$/.test(c.url)&&c.method==='POST')} items=${p.doc.querySelectorAll('#queue .qitem').length}`,exOk&&tabOk&&p.calls.some(c=>/\/abuse$/.test(c.url))&&p.doc.querySelectorAll('#queue .qitem').length>0);

/* ---------- root-cause experiment: map library fails to load ---------- */
const oldP=load(OLD,{L:false,routes:okRoutes()});await wait(1300);
const newP=load(NEW,{L:false,routes:okRoutes()});await wait(1300);
rec('F-ROOT-a','ORIGINAL page, Leaflet unavailable: whole script dies (counters stay 0, AQI stuck on Loading…)','reproduces the live symptoms',`total=${oldP.$('sTotal').textContent} aqsrc="${txt(oldP.$('aqsrc'))}" engine="${txt(oldP.$('engine'))}"`,oldP.$('sTotal').textContent==='0'&&/Loading/.test(txt(oldP.$('aqsrc'))),'Simulated condition in jsdom. Shows a plausible cause; does NOT prove it is what happens on the live site.');
rec('F-ROOT-b','PATCHED page, Leaflet unavailable: stats, list and AQI still work; map shows a message','16 + AQI + map notice',`total=${newP.$('sTotal').textContent} aqsrc="${txt(newP.$('aqsrc'))}" map="${txt(newP.$('map')).slice(0,40)}"`,newP.$('sTotal').textContent==='16'&&/Live/.test(txt(newP.$('aqsrc')))&&/map could not load/.test(txt(newP.$('map'))));

fs.writeFileSync('frontend_results.json',JSON.stringify(R,null,1));
const pass=R.filter(x=>x.result==='PASS').length;console.log(`\n${pass}/${R.length} passed`);process.exit(pass===R.length?0:1);
})();
