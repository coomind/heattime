import {test,expect} from '@playwright/test';
import {mkdirSync} from 'node:fs';
import path from 'node:path';
// Step 4 captures from the offline static demo: 1280 and 1920x1080 (desktop project) and 390 (mobile project).
// Each capture also checks for horizontal overflow; the images are reviewed by eye for overlap, clipping and tofu.
const OUT=path.resolve('../data/output/captures');
const nav=(page,name)=>page.locator('nav').getByRole('button',{name:new RegExp(name+'$')}).click();
async function shot(page,width,name){
 const dir=path.join(OUT,String(width));mkdirSync(dir,{recursive:true});
 await page.evaluate(()=>document.fonts.ready);
 await page.evaluate(()=>window.scrollTo(0,0));
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),`${name} @${width}: horizontal overflow`).toBe(true);
 await page.screenshot({path:path.join(dir,name+'.png'),fullPage:true});
}
async function flow(page,width){
 await page.context().route('**/*',r=>{const u=new URL(r.request().url());return u.hostname==='127.0.0.1'&&u.port==='8128'?r.continue():r.abort();});
 await page.goto('./');
 await expect(page.getByRole('heading',{name:'오늘 판단할 일'})).toBeVisible();
 await shot(page,width,'01-dashboard-0810');
 await page.locator('.match-row').filter({has:page.locator('.chip-stage.risk-4')}).first().click();
 await expect(page.locator('.decision-card')).toBeVisible();
 await shot(page,width,'02-match-detail-decision');
 await page.locator('summary',{hasText:'판정값이 나온 과정'}).click();
 await shot(page,width,'02b-match-detail-tables');
 await nav(page,'대시보드');
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await expect(page.locator('.decide .big')).toContainText('배정');
 await shot(page,width,'03-dashboard-0810-proposal');
 await nav(page,'재편성 비교');
 await expect(page.getByText('원래 일정은 작성자가 정한 가상 기준')).toBeVisible();
 await shot(page,width,'04-comparison');
 const snapshotReason=await page.getByLabel('판단 사유').getAttribute('placeholder');
 await page.getByLabel('판단 사유').fill(snapshotReason);
 await page.getByRole('button',{name:'제안 승인'}).click();
 await expect(page.getByText('판단 기록 완료')).toBeVisible();
 await page.getByText('판단 기록 완료').scrollIntoViewIfNeeded();
 await shot(page,width,'05-approval');
 await nav(page,'알림 로그');await expect(page.locator('.notification').first()).toBeVisible();
 await shot(page,width,'06-notifications');
 await nav(page,'운영 기록');await expect(page.getByText('사전 생성된 시연용 기록입니다.')).toBeVisible();
 await shot(page,width,'07-records');
 await page.goto('./#snapshot-observed-team');await expect(page.getByRole('table',{name:'참가팀 일정'})).toBeVisible();
 await shot(page,width,'08-team-view');
 await page.goto('./#snapshot-observed-0808');await page.getByRole('button',{name:'스냅샷 재현 실행 →'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();await expect(page.locator('.postponed-box')).toBeVisible();
 await shot(page,width,'09-dashboard-0808-postponed');
 await nav(page,'재현 모드');
 for(const s of await page.locator('.evidence-group details').all())await s.locator('summary').first().click();
 await expect(page.getByRole('table',{name:'62일 전체 재현 결과'})).toBeVisible();
 await shot(page,width,'10-evidence');
}
test('captures at 1280 and 1920x1080',async({page},info)=>{
 test.skip(info.project.name!=='desktop');test.setTimeout(240000);
 for(const [w,h] of [[1280,800],[1920,1080]]){await page.setViewportSize({width:w,height:h});await flow(page,w);}
});
test('captures at 390',async({page},info)=>{
 test.skip(info.project.name!=='mobile');test.setTimeout(240000);
 await flow(page,390);
});
