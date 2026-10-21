import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
// Every screen: no serious/critical axe violations (snapshot mode for decided flows, live mode for settings).
const serious=async page=>(await new AxeBuilder({page}).analyze()).violations.filter(v=>['serious','critical'].includes(v.impact)).map(v=>`${v.id}: ${v.nodes.slice(0,3).map(n=>n.target.join(' ')).join(' | ')}`);
test('snapshot flow screens have no serious accessibility violations',async({page})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 const found={};
 found['재현 모드']=await serious(page);
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await expect(page.getByRole('heading',{name:'구장 × 시간 위험도'})).toBeVisible();
 found['대시보드']=await serious(page);
 await page.locator('.match-row').first().click();await expect(page.locator('.stage-window')).toBeVisible();
 found['경기 상세']=await serious(page);
 const nav=name=>page.locator('nav').getByRole('button',{name});
 await nav('재편성 비교').click();await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await expect(page.locator('.original-issues')).toBeVisible();
 found['재편성 비교']=await serious(page);
 await page.getByRole('button',{name:'제안 승인',exact:true}).click();
 await nav('알림 로그').click();await expect(page.locator('.notification').first()).toBeVisible();
 found['알림 로그']=await serious(page);
 await nav('운영 기록').click();found['운영 기록']=await serious(page);
 await nav('검증 기록').click();found['검증 기록']=await serious(page);
 await page.goto('/#snapshot-observed-team');await expect(page.getByRole('heading',{name:'참가팀 읽기 전용 일정'})).toBeVisible();
 found['팀 일정']=await serious(page);
 expect(found).toEqual(Object.fromEntries(Object.keys(found).map(k=>[k,[]])));
});
test('live settings screen has no serious accessibility violations',async({page})=>{
 await page.goto('/');await page.locator('nav').getByRole('button',{name:'설정'}).click();
 await expect(page.getByRole('heading',{name:'구장 등록·수정'})).toBeVisible();
 expect(await serious(page)).toEqual([]);
});
