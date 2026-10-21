import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
// Judge demo (dist-demo) with every request outside the local static server blocked: the whole flow must work.
// Expected values come from the committed scene snapshots (the same files the demo serves).
const FILES={demo:'observed-snapshot',extreme:'observed-snapshot-0808'};
function scene(key){
 const s=JSON.parse(readFileSync(new URL(`../src/demo/${FILES[key]}.json`,import.meta.url),'utf8')).approved;
 return {original_levels:[0,1,2,3,4].map(i=>s.recommendations.filter(r=>r.level===i).length),assigned:s.proposal.assignments.length,
  postponed:s.proposal.postponed_count,decision_reason:s.decision.reason,notifications:s.notifications.length};
}
async function offline(page){
 const blocked=[];
 await page.context().route('**/*',route=>{const u=new URL(route.request().url());
  if(u.hostname==='127.0.0.1'&&u.port==='8128'&&!u.pathname.includes('/api/'))return route.continue();
  blocked.push(u.href);return route.abort();});
 return blocked;
}
const nav=(page,name)=>page.locator('nav').getByRole('button',{name:new RegExp(name+'$')}).click();

test('static demo runs the whole operator flow offline under a sub-path',async({page})=>{
 const blocked=await offline(page);
 await page.goto('./');
 // First screen: the 8/10 observed scene opens on its dashboard.
 await expect(page).toHaveURL(/#snapshot-observed$/);
 await expect(page.getByRole('heading',{name:'오늘 판단할 일'})).toBeVisible();
 const demo=scene('demo');
 await expect(page.locator('.decide .big')).toHaveText(`${demo.original_levels[4]}경기 운동 중지`);
 await expect(page.locator('.heat-legend').first()).toContainText('중앙 추정값');
 // Match detail and decision formula.
 await page.locator('.match-row').first().click();
 // Decision card first: value, stage chip, formula and the range as reference.
 const card=page.locator('.decision-card');
 await expect(card.locator('.dc-value')).toBeVisible();await expect(card.locator('.dc-chip')).toContainText('단계');
 await expect(card.locator('.dc-formula')).toContainText('관측 기반 추정');await expect(card.locator('.dc-formula')).toContainText('구장 보정');
 await expect(card.locator('.dc-range')).toContainText('참고용');
 // Detailed tables stay collapsed until opened.
 const more=page.locator('summary',{hasText:'판정값이 나온 과정'});
 await expect(page.getByRole('table',{name:'판정값 계산식'})).toBeHidden();
 await more.click();await expect(more).toHaveAttribute('aria-expanded','true');
 await expect(page.getByRole('table',{name:'판정값 계산식'})).toBeVisible();
 await expect(page.getByRole('table',{name:'판정 기준 비교'})).toContainText('단계');
 // Reschedule from the dashboard, then review.
 await nav(page,'대시보드');
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await expect(page.locator('.decide .big')).toHaveText(`${demo.assigned}경기 배정, ${demo.postponed}경기 연기`);
 await page.getByRole('button',{name:'재편성 비교에서 검토'}).click();
 // Reason typed by the operator, then approval.
 const reason=page.getByLabel('판단 사유');
 await expect(page.getByRole('button',{name:'제안 승인'})).toBeDisabled();
 await reason.fill(demo.decision_reason);
 await page.getByRole('button',{name:'제안 승인'}).click();
 await expect(page.getByText('판단 기록 완료')).toBeVisible();
 // Mock notifications.
 await nav(page,'알림 로그');
 await expect(page.locator('.notification')).toHaveCount(demo.notifications);
 await expect(page.getByText('실제 문자·카카오 메시지는 발송하지 않습니다.')).toBeVisible();
 // Records: pre-generated PDF/CSV and current JSON download.
 await nav(page,'운영 기록');
 await expect(page.getByText('사전 생성된 시연용 기록입니다.')).toBeVisible();
 for(const [label,ext] of [['운영 기록 PDF','pdf'],['CSV 내보내기','csv'],['전체 근거 JSON','json']]){
  const wait=page.waitForEvent('download');await page.getByRole('link',{name:label}).click();
  const file=await wait;expect(file.suggestedFilename()).toBe('heattime-observed-0810.'+ext);
 }
 // Team read-only view (same tab, own route).
 await page.goto('./#snapshot-observed-team');
 await expect(page.getByRole('table',{name:'참가팀 일정'})).toBeVisible();
 // Switch to the 8/8 scene from the replay screen.
 await page.goto('./#snapshot-observed');
 await nav(page,'재현 모드');
 await page.getByRole('group',{name:'시연 장면'}).getByRole('link',{name:/8월 8일/}).click();
 await expect(page).toHaveURL(/#snapshot-observed-0808$/);
 await page.getByRole('button',{name:'스냅샷 재현 실행 →'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 const hot=scene('extreme');
 await expect(page.locator('.postponed-box h3')).toHaveText(`연기 제안 ${hot.postponed}경기`);
 await page.getByRole('link',{name:'이틀 일정으로 다시 짜면'}).click();
 await expect(page).toHaveURL(/#snapshot-observed-0808-2day$/);
 await page.getByRole('button',{name:'스냅샷 재현 실행 →'}).click();
 await expect(page.getByRole('group',{name:'대회 날짜'}).getByRole('button')).toHaveCount(2);
 expect(blocked.filter(u=>!u.includes('/api/'))).toEqual([]);
});

test('after the cache is stored the demo reloads with the network fully off',async({page,context})=>{
 await offline(page);
 await page.goto('./');
 await expect(page.getByText('시연 자료 저장됨')).toBeVisible();
 await context.setOffline(true);
 // Reloading the first-screen address (no hash) opens the 8/10 dashboard again from the cache.
 await page.goto('./');
 await expect(page.getByRole('heading',{name:'오늘 판단할 일'})).toBeVisible();
 await page.reload();
 await expect(page.getByRole('button',{name:'스냅샷 재현 실행 →'})).toBeVisible();
 await page.goto('./#snapshot-observed-0808');
 await page.getByRole('button',{name:'스냅샷 재현 실행 →'}).click();
 await expect(page.getByRole('heading',{name:'오늘 판단할 일'})).toBeVisible();
});
