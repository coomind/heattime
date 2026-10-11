import {test,expect} from '@playwright/test';
import path from 'node:path';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const exportsBundle=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot-exports.json',import.meta.url),'utf8'));

async function flow(page,testInfo,snapshot){
 await page.getByRole('button',{name:snapshot?'스냅샷 재현 실행 →':'재현 시뮬레이션 실행 →',exact:true}).click();
 await expect(page.locator('.heat-row')).toHaveCount(3);await expect(page.locator('.heat-cell')).toHaveCount(42);
 await expect(page.locator('.disclaimer')).toContainText('기상청 관측 자료(수원 119·2026-08-10)');
 await expect(page.locator('.disclaimer')).not.toContainText('합성 기상으로 시연');
 await page.screenshot({path:path.resolve('../data/output/real/'+testInfo.project.name+'-'+(snapshot?'snapshot':'live')+'.png'),fullPage:true});
 await page.locator('.match-row').first().click();await expect(page.locator('.chart')).toBeVisible();
 await expect(page.locator('.range').first()).toContainText('추정');
 await page.getByText('근거 데이터와 계산 가정',{exact:true}).click();
 await expect(page.locator('pre').first()).toContainText('original_sample_sha256');
 await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await expect(page.getByRole('heading',{name:'공통 경기의 열 노출 비교'})).toBeVisible();
 // Demo date 2026-08-10: 13 common matches, 2 postponed (semi2, final), 6442->3879.
 await expect(page.locator('.comparison-metrics')).toContainText('공통 13경기');
 await expect(page.locator('.comparison-metrics')).toContainText('2경기 연기');
 if(snapshot){await expect(page.locator('.comparison-metrics')).toContainText('6,442');await expect(page.locator('.comparison-metrics')).toContainText('3,879');
  await expect(page.locator('.postponed')).toHaveCount(2);await expect(page.locator('.postponed').filter({hasText:'semi2'})).toContainText('배정 불가');}
 await page.getByRole('button',{name:'제안 승인',exact:true}).click();
 await expect(page.getByText('판단 기록 완료:',{exact:false})).toBeVisible();
 await page.locator('nav').getByRole('button',{name:'알림 로그'}).click();
 await expect(page.locator('.notification').first()).toContainText('모의 발송');
 if(snapshot)await expect(page.getByRole('link',{name:'참가팀 읽기 전용 일정 열기 ↗'})).toHaveAttribute('href','/#snapshot-observed-team');
 await page.locator('nav').getByRole('button',{name:'운영 기록'}).click();
 const pending=page.waitForEvent('download');await page.getByRole('link',{name:'운영 기록 PDF',exact:true}).click();
 const download=await pending;expect(await download.failure()).toBeNull();
 const filename=path.resolve('../data/output/real/'+testInfo.project.name+'-'+testInfo.repeatEachIndex+'-'+(snapshot?'observed-snapshot':'observed-live')+'.pdf');
 await download.saveAs(filename);
 if(snapshot){
  expect(createHash('sha256').update(readFileSync(filename)).digest('hex')).toBe(createHash('sha256').update(Buffer.from(exportsBundle.pdf_base64,'base64')).digest('hex'));
 }else{
  await page.locator('nav').getByRole('button',{name:'알림 로그'}).click();
  const href=await page.getByRole('link',{name:'참가팀 읽기 전용 일정 열기 ↗'}).getAttribute('href');
  await page.goto(href);await expect(page.getByRole('heading',{name:'참가팀 읽기 전용 일정'})).toBeVisible();
  await expect(page.locator('.disclaimer')).toContainText('기상청 관측 자료(수원 119·2026-08-10)');
  await expect(page.locator('.disclaimer')).not.toContainText('합성 기상으로 시연');
  await expect(page.getByRole('button',{name:'제안 승인',exact:true})).toHaveCount(0);
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
}

test('real observations complete replay, detail, approval, mock notification and PDF',async({page},testInfo)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await expect(page.locator('option[value="observed"]')).toBeEnabled();
 await page.getByRole('combobox',{name:'기상 자료',exact:true}).selectOption('observed');
 await expect(page.locator('input[type="date"]').first()).toHaveValue('2026-08-10');
 await flow(page,testInfo,false);expect(errors).toEqual([]);
});

test('observed snapshot completes with zero API requests after fully offline reload',async({page,context},testInfo)=>{
 const errors=[];let apiRequests=0;
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))apiRequests++;});
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await expect(page.locator('.demo-tag')).toContainText('관측 시연 스냅샷');
 await context.setOffline(true);await page.reload();
 await expect(page.getByRole('button',{name:'스냅샷 재현 실행 →'})).toBeEnabled();
 await flow(page,testInfo,true);
 await page.goto('/#snapshot-observed-team');await expect(page.getByRole('heading',{name:'참가팀 읽기 전용 일정'})).toBeVisible();
 await expect(page.locator('.disclaimer')).toContainText('기상청 관측 자료(수원 119·2026-08-10)');
 await expect(page.getByRole('button',{name:'제안 승인',exact:true})).toHaveCount(0);
 expect(apiRequests).toBe(0);expect(errors).toEqual([]);await context.setOffline(false);
});
