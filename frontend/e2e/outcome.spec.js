import {test,expect} from '@playwright/test';
import path from 'node:path';

test('offline observed proposal makes its outcome visible and distinguishes approval from a proposal', async({page,context},testInfo) => {
  let requests = 0;
  page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))requests++;});
  await page.route('**/api/**',route=>route.abort());
  await page.goto('/#snapshot-observed');
  await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
  await context.setOffline(true);await page.reload();
  await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
  await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
  const outcome = page.getByRole('region',{name:'자동 제안 요약'});
  await expect(outcome).toHaveCount(0);
  await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
  await expect(outcome).toBeVisible();
  // Demo date 2026-08-10: 13 assigned / 2 postponed (semi2, final), 13 of 14 originally stopped matches assigned.
  await expect(outcome).toContainText('전체 15경기 중 배정13경기');
  await expect(outcome).toContainText('별도 연기2경기');
  await expect(outcome).toContainText('원래 중지 단계 14경기 중 제안 배정13경기');
  await expect(outcome).toContainText('공통 13경기 열 노출 점수39.79% 감소');
  await expect(outcome).toContainText('2,563점 감소');
  await expect(page.locator('.postponed')).toHaveCount(2);
  await expect(page.locator('.postponed').filter({hasText:/^결승 연기/})).toContainText('선행 경기 연기');
  await expect(outcome).toContainText('승인 전 제안');
  await expect(outcome).toContainText('건강 효과나 사고 감소율이 아닙니다');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:path.resolve('../data/output/competition/'+testInfo.project.name+'-outcome.png'),fullPage:true});
  await page.getByRole('button',{name:'제안 승인',exact:true}).click();
  await expect(outcome).toContainText('제안 승인됨');
  await expect(outcome).not.toContainText('승인 전 제안');
  expect(requests).toBe(0);await context.setOffline(false);
});
