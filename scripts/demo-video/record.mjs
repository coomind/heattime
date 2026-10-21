// Records the usage video from the offline static demo (frontend/dist-demo) inside wrapper.html.
// Usage (repository root): node scripts/demo-video/record.mjs
// Needs: frontend/dist-demo (npm run build:demo), data/output/demo-numbers.json, recordings/assets/pdf-page1.png
// (scripts/demo-video/render_pdf_page.py). Output: recordings/frames/*.jpg + recordings/timeline.json.
//
// Capture: the page runs at deviceScaleFactor 2 and frames come from the Chrome DevTools screencast at
// 3840x2160 (Playwright's recordVideo only captures CSS pixels). compose.py scales them to 1920x1080 with lanczos.
// Framing: each shot is either the app at the top of its page (sidebar fully visible) or one card with margins
// centred, with plain background panels hiding everything else (sidebar included). Shots change with a 0.25 s fade. Every request outside this local server is blocked.
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {readFile,stat,mkdir,writeFile,rm} from 'node:fs/promises';
import {writeFileSync} from 'node:fs';
import {extname,join,normalize,resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(join(ROOT,'frontend/package.json'));
const {chromium}=require('@playwright/test');
const PORT=8131,BASE=`http://127.0.0.1:${PORT}`;
const K=4/3;                     // app iframe 1440x702 CSS px shown at 1920x936
const N=JSON.parse(await readFile(join(ROOT,'data/output/demo-numbers.json'),'utf8'));
const scene=k=>N.scenes.find(s=>s.key===k);
const demo=scene('demo'),hot=scene('extreme'),ex=demo.decision_example;

// Scene lengths in seconds (constant, so a re-recording has the same length). Total 130 s.
const LENGTH=[8,14,20,22,16,12,10,16,12];
const fmt1=x=>Number(x).toFixed(1);
const CAPTIONS=[
 ['8월 10일 아침, 운영자가 HeatTime을 엽니다',`가상 ${demo.teams}팀 대회를 ${demo.station.name} 관측 자료로 계산했습니다`],
 [`원래 일정 ${demo.matches}경기 중 ${demo.original_levels[4]}경기가 운동 중지 단계입니다`,'구장과 시간마다 판정값과 범위를 함께 보여 줍니다'],
 ['판정값이 어떻게 나왔는지 숫자로 보여 줍니다',`관측 기반 추정 ${fmt1(ex.observed_estimate_c)} + 구장 보정 ${ex.venue_offset_c} = ${fmt1(ex.decision_c)}℃`],
 ['재편성 실행 한 번으로 일정 대안을 만듭니다',demo.postponed===0?`${demo.assigned}경기를 모두 배정했고 연기는 없습니다`:`${demo.assigned}경기를 배정했고 ${demo.postponed}경기는 연기 후보입니다`],
 ['최종 판단은 운영자가 합니다','승인 사유가 기록에 남습니다'],
 [`바뀐 일정을 ${demo.teams}팀에 알립니다`,'모의 발송입니다. 실제 문자는 보내지 않습니다'],
 // The team view lists the new kickoff, venue and action (no original-time column), so the caption says that.
 ['참가팀은 휴대폰으로 바뀐 시각을 확인합니다','새 킥오프와 구장, 운영 조치를 읽기 전용으로 보여 줍니다'],
 [`더 더운 8월 8일에는 ${hot.postponed}경기를 연기 후보로 따로 보여 줍니다`,'재편성해도 배정할 수 없는 경기와 그 사유입니다'],
 ['판단 근거는 기록으로 남습니다','입력 기상, 추정 범위, 정책 출처, 운영자 조치를 담습니다'],
];

const TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json',
 '.woff':'font/woff','.woff2':'font/woff2','.png':'image/png','.svg':'image/svg+xml','.pdf':'application/pdf'};
const MOUNTS=[['/heattime/',join(ROOT,'frontend/dist-demo')],['/wrap/',join(ROOT,'scripts/demo-video')],['/fonts/ibm-plex-mono',join(ROOT,'frontend/node_modules/@fontsource/ibm-plex-mono/files/ibm-plex-mono')],
 ['/fonts/',join(ROOT,'frontend/src/fonts')],['/assets-video/',join(ROOT,'recordings/assets')]];
const server=createServer(async(req,res)=>{
 const path=decodeURIComponent(new URL(req.url,BASE).pathname);
 const mount=MOUNTS.find(([p])=>path.startsWith(p));if(!mount){res.writeHead(404);return res.end();}
 const rest=path.slice(mount[0].length);let file=normalize(mount[0].endsWith('/')?join(mount[1],rest):mount[1]+rest);
 try{if((await stat(file)).isDirectory())file=join(file,'index.html');res.writeHead(200,{'Content-Type':TYPES[extname(file)]||'application/octet-stream'});res.end(await readFile(file));}
 catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(PORT,'127.0.0.1',r));

const FRAMES=join(ROOT,'recordings/frames');await rm(FRAMES,{recursive:true,force:true});await mkdir(FRAMES,{recursive:true});
const browser=await chromium.launch();
const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:2,acceptDownloads:true});
await context.route('**/*',route=>new URL(route.request().url()).origin===BASE?route.continue():route.abort());
const page=await context.newPage();
const events=[];const mark=(kind,extra={})=>events.push({kind,t:Date.now()/1000,...extra});
const app=page.frameLocator('#app'),app2=page.frameLocator('#app2'),team=page.frameLocator('#team');
const rec=(fn,...args)=>page.evaluate(([fn,args])=>window.rec[fn](...args),[fn,args]);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let view={s:1,tx:0,ty:0};
const rectOf=loc=>loc.evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};});
// Wait until the app is idle (no "처리하고 있습니다" status) and the element stops moving, then measure.
async function stableRect(frame,loc){
 await frame.locator('.status',{hasText:'초 경과'}).waitFor({state:'detached',timeout:20000}).catch(()=>{});
 let prev=await rectOf(loc);
 for(let i=0;i<20;i++){await sleep(150);const r=await rectOf(loc);if(Math.abs(r.x-prev.x)<0.5&&Math.abs(r.y-prev.y)<0.5&&Math.abs(r.h-prev.h)<0.5)return r;prev=r;}
 return prev;
}
const toScreen=(x,y)=>({x:view.tx+view.s*x*K,y:view.ty+view.s*y*K});
async function setView(v){view=v;await rec('frame',v.s,v.tx,v.ty);}
// Shot 1: the page from its top, whole app visible (sidebar complete).
async function pageTop(frame){await rec('fadeOut');await rec('unmask');await frame.locator('html').evaluate(()=>window.scrollTo(0,0));await setView({s:1,tx:0,ty:0});await sleep(150);await rec('fadeIn');}
// Shot 2: one card with margins; the sidebar is kept fully out of frame.
async function cardShot(frame,loc,{margin=20,maxScale=1.9,through=null}={}){
 await rec('fadeOut');
 await stableRect(frame,loc);
 // Scroll only the app document (scrollIntoView would also scroll the wrapper's overflow-hidden viewport).
 await loc.evaluate((el,m)=>window.scrollTo(0,window.scrollY+el.getBoundingClientRect().top-m),margin);
 const r=await stableRect(frame,loc);
 if(through){const t=await stableRect(frame,through);r.h=t.y+t.h-r.y+12;}             // frame the card top down to this element
 const h=Math.min(r.h,702-r.y-margin);
 const x=(r.x-margin)*K,y=(r.y-margin)*K,w=(r.w+2*margin)*K,hh=(h+2*margin)*K;
 const s=Math.min(1920/w,936/hh,maxScale);
 const tx=(1920-s*w)/2-s*x,ty=(936-s*hh)/2-s*y;     // card centred; the mask hides everything else
 if(process.env.DEMO_DEBUG)console.log('cardShot',JSON.stringify({r,h,s,tx,ty,x,y,w,hh}));
 await setView({s,tx,ty});
 const edge=Math.min(margin,10)*K*s;                     // mask hugs the card so no neighbouring edge shows
 await rec('mask',tx+s*x+(margin*K*s-edge),ty+s*y+(margin*K*s-edge),s*w-2*(margin*K*s-edge),s*hh-2*(margin*K*s-edge));
 await sleep(150);await rec('fadeIn');return r;
}
async function point(loc){const r=await rectOf(loc);const p=toScreen(r.x+r.w/2,r.y+r.h/2);await rec('move',p.x,p.y);return p;}
async function click(loc,sound=false){await point(loc);await rec('press');if(sound)mark('click');await loc.evaluate(el=>el.click());}
const nav=(frame,name)=>frame.locator('nav').getByRole('button',{name:new RegExp(name+'$')});

await page.goto(`${BASE}/wrap/wrapper.html?app=${encodeURIComponent(BASE+'/heattime/')}&pdf=${encodeURIComponent(BASE+'/assets-video/pdf-page1.png')}`);
await app.getByRole('heading',{name:'오늘 판단할 일'}).waitFor();
await app.getByText('시연 자료 저장됨').waitFor({timeout:60000});
await page.evaluate(b=>{document.getElementById('app2').src=b+'/heattime/#snapshot-observed-0808';document.getElementById('team').src=b+'/heattime/#snapshot-observed-team';},BASE);
await app2.locator('button.primary').first().waitFor({state:'attached'});await team.locator('table[aria-label="참가팀 일정"]').waitFor({state:'attached'});
await page.evaluate(()=>document.fonts.ready);await sleep(500);

// Screencast at device pixels; every frame is written to disk with its timestamp.
const cdp=await context.newCDPSession(page);const frames=[];let index=0;
cdp.on('Page.screencastFrame',f=>{const file=String(index++).padStart(6,'0')+'.jpg';writeFileSync(join(FRAMES,file),Buffer.from(f.data,'base64'));
 frames.push({file,t:f.metadata.timestamp});cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{});});
await cdp.send('Page.startScreencast',{format:'jpeg',quality:95,maxWidth:3840,maxHeight:2160,everyNthFrame:1});
await sleep(800);

const t0=Date.now();mark('demo-start');let end=0;
async function sceneStart(i){await rec('caption',i+1,LENGTH.length,...CAPTIONS[i]);mark('scene',{n:i+1});}
async function sceneEnd(i){if(process.env.DEMO_STOP&&i+1===Number(process.env.DEMO_STOP)){console.log('state',JSON.stringify(await page.evaluate(()=>({stage:document.getElementById('stage').style.transform,masked:document.body.className,m:['m1','m2','m3','m4'].map(id=>document.getElementById(id).style.cssText)}))),JSON.stringify(await rectOf(app.locator('.decision-card'))),await app.locator('html').evaluate(()=>scrollY));await page.screenshot({path:join(ROOT,'recordings/debug-stop.png')});console.log('stopped');process.exit(0);}end+=LENGTH[i];const left=t0+end*1000-Date.now();if(left<0)console.warn(`scene ${i+1} overran by ${(-left/1000).toFixed(1)}s`);await sleep(Math.max(0,left));}
const until=sec=>sleep(Math.max(0,t0+sec*1000-Date.now()));

// 01: the dashboard of 8/10 from the top
await sceneStart(0);await sceneEnd(0);
// 02: the heatmap panel; point at stage-4 cells
await sceneStart(1);const heat=app.locator('section.dash-panel').filter({has:app.locator('#heat-title')});
await cardShot(app,heat,{maxScale:1.3});await sleep(500);
const hot4=app.locator('.heat-cell.risk-4');await point(hot4.first());await sleep(1800);await point(hot4.nth(1));await sleep(1800);await point(hot4.nth(2));
await sceneEnd(1);
// 03: open the stage-4 example match; frame only the decision card so the value is large
await sceneStart(2);const list=app.locator('section.dash-panel').filter({has:app.locator('#list-title')});
const row=list.locator('.match-row').filter({hasText:ex.match}).first();
await cardShot(app,row,{margin:60,maxScale:1.6});await click(row);
await app.locator('.decision-card').waitFor();await rec('cursorVisible',false);
await cardShot(app,app.locator('.decision-card'),{margin:28,maxScale:2.0});
if(process.env.DEMO_DEBUG){await page.screenshot({path:join(ROOT,'recordings/debug-after-card.png')});}
await sceneEnd(2);
// 04: reschedule from the dashboard top; frame the result card, then the heatmap lanes, then the result again
await sceneStart(3);await pageTop(app);await rec('cursorVisible',true);await click(nav(app,'대시보드'));await sleep(400);
await click(app.getByRole('button',{name:'재편성 실행',exact:true}),true);
await app.locator('.decide .big').filter({hasText:'배정'}).waitFor();await sleep(1200);
await rec('cursorVisible',false);const decide=app.locator('section.decide');await cardShot(app,decide,{maxScale:1.5});await sleep(4500);
await cardShot(app,heat,{maxScale:1.3});await until(end+LENGTH[3]-8);
await cardShot(app,decide,{maxScale:1.7});await sceneEnd(3);
// 05: type the reason in the decision card and approve
await sceneStart(4);await pageTop(app);await rec('cursorVisible',true);await click(nav(app,'재편성 비교'));await sleep(500);
const reasonCard=app.locator('section.card').filter({has:app.getByRole('heading',{name:'변경 사유와 운영자 판단'})});
await cardShot(app,reasonCard,{maxScale:1.5});const box=app.getByLabel('판단 사유');
await click(box);await box.pressSequentially(demo.decision_reason,{delay:70});await sleep(500);
await click(app.getByRole('button',{name:'제안 승인'}),true);await app.getByText('판단 기록 완료').waitFor();await sleep(300);
await rec('cursorVisible',false);await cardShot(app,reasonCard,{maxScale:1.5});await sceneEnd(4);
// 06: mock notifications from the page top, then the first messages framed
await sceneStart(5);await pageTop(app);await rec('cursorVisible',true);await click(nav(app,'알림 로그'));await sleep(2500);
await rec('cursorVisible',false);await cardShot(app,app.locator('section.card').filter({has:app.getByRole('heading',{name:'모의 발송 내역'})}),{maxScale:1.5,through:app.locator('.notification').nth(3)});
await sceneEnd(5);
// 07: phone frame with the team view from its top
await sceneStart(6);await rec('fadeOut');await rec('unmask');await rec('show','team');await sleep(200);
await team.locator('section.card:has(table[aria-label="참가팀 일정"])').evaluate(el=>window.scrollTo(0,window.scrollY+el.getBoundingClientRect().top-12));await sleep(150);await rec('fadeIn');await sceneEnd(6);
// 08: the hotter day; postponed box framed; two-day link
await sceneStart(7);await rec('fadeOut');await rec('unmask');await rec('show','app2');await setView({s:1,tx:0,ty:0});await rec('fadeIn');await rec('cursorVisible',true);
await click(app2.getByRole('button',{name:'스냅샷 재현 실행 →'}));await app2.getByRole('heading',{name:'오늘 판단할 일'}).waitFor();await sleep(600);
await click(app2.getByRole('button',{name:'재편성 실행',exact:true}));await app2.locator('.postponed-box').waitFor();await sleep(600);
await rec('cursorVisible',false);await cardShot(app2,app2.locator('.postponed-box'),{maxScale:1.8});await sleep(4200);await rec('cursorVisible',true);
await click(app2.getByRole('link',{name:'이틀 일정으로 다시 짜면'}));await sleep(300);await pageTop(app2);
await click(app2.getByRole('button',{name:'스냅샷 재현 실행 →'}));await app2.getByRole('group',{name:'대회 날짜'}).waitFor();await sceneEnd(7);
// 09: records page from the top, PDF download, first page
await sceneStart(8);await rec('fadeOut');await rec('unmask');await rec('show','app');await app.locator('html').evaluate(()=>window.scrollTo(0,0));await setView({s:1,tx:0,ty:0});await rec('fadeIn');
await rec('cursorVisible',true);await click(nav(app,'운영 기록'));await sleep(600);
const dl=page.waitForEvent('download');await click(app.getByRole('link',{name:'운영 기록 PDF'}));const file=await dl;mark('pdf',{name:file.suggestedFilename()});
await sleep(1500);await rec('cursorVisible',false);await rec('fadeOut');await rec('show','pdf');await rec('fadeIn');await sceneEnd(8);
mark('demo-end');await sleep(600);

await cdp.send('Page.stopScreencast');await context.close();await browser.close();server.close();
await writeFile(join(ROOT,'recordings/timeline.json'),JSON.stringify({frames_dir:FRAMES,scale:2,scene_lengths:LENGTH,captions:CAPTIONS,events,frames},null,1));
console.log(JSON.stringify({frames:frames.length,events:events.filter(e=>e.kind!=='scene').map(e=>({...e,t:+(e.t-events[0].t).toFixed(2)}))}));
