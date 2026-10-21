import {test,expect} from '@playwright/test';
for(const mode of ['snapshot','snapshot-observed'])test(mode+' proposed and approved detail constraints work fully offline',async({page,context})=>{
 let calls=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))calls++;});
 await page.route('**/api/**',r=>r.abort());await page.goto('/#'+mode);
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await context.setOffline(true);await page.reload();
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 const mid=mode==='snapshot'?'4조 3경기':'1조 1경기';
 await page.getByRole('button',{name:mid+' 자동 제안 근거',exact:true}).click();
 const evidence=page.locator('.match-evidence');
 await expect(evidence).toContainText('아직 승인하지 않은 자동 제안');
 await expect(evidence).toContainText('WBGT 추정');await expect(evidence).toContainText('범위');
 if(mode==='snapshot-observed')await expect(evidence.getByRole('table',{name:'경기별 제약 근거'})).toContainText('팀 휴식');
 else {await expect(evidence.getByRole('table',{name:'경기별 제약 근거'})).toBeVisible();}
 await expect(evidence).toContainText('이 일정의 기존 하드 제약 검사 통과');
 if(mode==='snapshot-observed')await expect(evidence).toContainText('8. 10. 09:00');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
 {const box=page.getByLabel('판단 사유',{exact:true});const ph=await box.getAttribute('placeholder');if(ph)await box.fill(ph);}await page.getByRole('button',{name:'제안 승인',exact:true}).click();
 await page.getByRole('button',{name:(mode==='snapshot'?'4조 3경기':'준결승 1')+' 승인 일정 근거',exact:true}).click();
 await expect(evidence).toContainText('승인 시점의 적용 일정');
 if(mode==='snapshot-observed'){
  await expect(evidence).toContainText('진출 가능 팀 휴식');
 }
 if(mode==='snapshot'){
  // Synthetic 2026-08-01: g1-2 is postponed (no feasible slot), so its proposed view shows the reason, not an assignment.
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  await page.getByRole('button',{name:'1조 2경기 자동 제안 근거',exact:true}).click();
  await expect(evidence).toContainText('연기 —');await expect(evidence).toContainText('배정 불가');
 }
 expect(calls).toBe(0);await context.setOffline(false);
 if(mode==='snapshot-observed'){
  // 2026-08-10 assigns every match, so the postponement views are checked on the 2026-08-08 scene:
  // the final is postponed because its semi-finals were postponed; g1-2 has no feasible slot.
  await page.goto('/#snapshot-observed-0808');
  await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
  {const box=page.getByLabel('판단 사유',{exact:true});const ph=await box.getAttribute('placeholder');if(ph)await box.fill(ph);}await page.getByRole('button',{name:'제안 승인',exact:true}).click();
  await page.getByRole('button',{name:'결승 승인 일정 근거',exact:true}).click();
  await expect(evidence).toContainText('승인 시점의 적용 일정');await expect(evidence).toContainText('연기 — 선행 경기 연기');
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  await page.getByRole('button',{name:'1조 2경기 승인 일정 근거',exact:true}).click();
  await expect(evidence).toContainText('연기 — ');await expect(evidence).toContainText('배정 불가');
  expect(calls).toBe(0);
 }
});
