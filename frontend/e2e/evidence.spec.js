import {test,expect} from '@playwright/test';
import path from 'node:path';

test('all-date evidence and match changes remain usable offline with explicit model and algorithm limits',async({page,context},testInfo)=>{
  let requests=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))requests++;});
  await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
  await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
  await context.setOffline(true);await page.reload();
  await page.getByText('62일 전체 재현 결과와 알고리즘 비교',{exact:true}).click();
  const evidence=page.locator('.period-evidence');
  await expect(evidence.getByRole('table',{name:'62일 전체 재현 결과'}).locator('tbody tr')).toHaveCount(62);
  // 2026-10-21 recalculation (central estimate + 2.5℃ venue offset): 28 complete / 32 partial / 2 zero-assignment days.
  await expect(evidence.locator('.period-totals').first()).toContainText('전부 배정 28일');
  await expect(evidence.locator('.period-totals').first()).toContainText('일부 배정 32일');
  await expect(evidence.locator('.period-totals').first()).toContainText('0경기 배정 2일');
  await expect(evidence).toContainText('경기장 보정 +2.5℃');
  await expect(evidence).toContainText('62일 중 34일에');
  await expect(evidence).toContainText('0경기 배정일은 2일(8/4, 8/6)');
  await expect(evidence).toContainText('지금 고른 대회나 날짜 또는 바꾼 설정으로 새로 계산한 결과와 다릅니다');
  await page.getByText('같은 제약에서 탐욕 방식과 비교한 별도 지표',{exact:true}).click();
  await expect(evidence.getByRole('table',{name:'62일 알고리즘 비교'}).locator('tbody tr')).toHaveCount(62);
  await expect(evidence).toContainText('609 → 699건');
  await expect(evidence).toContainText('0 → 28일');
  await expect(evidence.locator('.comparison-tradeoff')).toContainText('8,120점(6.07%) 높습니다');
  await expect(evidence).toContainText('사람이 손으로 짠 일정이나 경쟁 제품을 시험한 결과가 아닙니다');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:path.resolve('../data/output/competition/'+testInfo.project.name+'-evidence.png'),fullPage:true});
  await page.getByText('62일 전체 재현 결과와 알고리즘 비교',{exact:true}).click();
  await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
  const table=page.getByRole('table',{name:'경기별 자동 제안 변경 내역'});
  await expect(table.locator('tbody tr')).toHaveCount(15);
  // 2026-08-10 (central-estimate rule): every match is assigned, so no row carries a postponement reason (8/8 is checked below).
  await expect(table.locator('tbody tr').filter({hasText:'연기 사유 확인'})).toHaveCount(0);
  await expect(page.locator('.schedule-changes')).toContainText('아직 승인하지 않은 자동 제안');
  await expect(table.getByRole('row').filter({has:page.getByRole('button',{name:'1조 1경기 원래 경기 상세',exact:true})})).toContainText('120분 앞당김');
  await table.getByRole('button',{name:'1조 1경기 원래 경기 상세',exact:true}).click();
  await expect(page.getByRole('heading',{name:/^1조 1경기/})).toBeVisible();
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  {const box=page.getByLabel('판단 사유',{exact:true});const ph=await box.getAttribute('placeholder');if(ph)await box.fill(ph);}await page.getByRole('button',{name:'제안 승인',exact:true}).click();
  await expect(page.locator('.schedule-changes')).toContainText('승인된 자동 제안');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(requests).toBe(0);await context.setOffline(false);
  // 2026-08-08 scene: five rows (g1-2, g4-1, semi1, semi2, final) carry postponement reasons instead of a new kickoff.
  await page.goto('/#snapshot-observed-0808');
  await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
  const table0808=page.getByRole('table',{name:'경기별 자동 제안 변경 내역'});
  await expect(table0808.locator('tbody tr')).toHaveCount(15);
  await expect(table0808.locator('tbody tr').filter({hasText:'연기 사유 확인'})).toHaveCount(5);
  expect(requests).toBe(0);
});
