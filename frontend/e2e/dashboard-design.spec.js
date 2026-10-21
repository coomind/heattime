import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'node:path';
// Design A dashboard on the 8/10 observed snapshot: requirements a-h, whole day visible at 1280/390, no serious axe issues.
async function openProposal(page){
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await expect(page.getByRole('heading',{name:'자동 재편성 제안'})).toBeVisible();
}
test('dashboard puts the proposal first and explains every number',async({page},testInfo)=>{
 await openProposal(page);
 const decide=page.locator('.decide');
 // d: one readable sentence instead of "13 / 14"
 await expect(decide).toContainText('15경기 배정, 0경기 연기');
 await expect(decide).toContainText('원래 일정에서 운동 중지 단계였던 4경기 중 4경기를 다른 시간이나 구장으로 옮겨 배정했습니다.');
 await expect(decide).toContainText('5,273점에서 4,153점으로');
 // c: rule (나) leaves no postponement on 8/10, so no postponed box (8/8 box is checked below)
 await expect(page.locator('.postponed-box')).toHaveCount(0);
 // a: the big cell number is the decision value, legend says which value decides
 const cell=page.getByRole('button',{name:/구장 A.* 13시 입력 근거/});
 await expect(cell.locator('.dv')).toHaveText('31.3');await expect(cell.locator('.stg')).toHaveText('4 운동 중지');
 await expect(cell.locator('.cr')).toContainText('29.8~32.8');
 await expect(page.locator('.heat-legend').first()).toContainText('구장 보정 2.5℃를 더한 WBGT 중앙 추정값');
 // e: same-station note; f: no internal ids anywhere on the dashboard
 await expect(page.locator('.same-note')).toContainText('같은 관측소(수원 119)');
 const text=await page.locator('main').innerText();
 for(const raw of ['winner:','group1','semi1 승자','semi2 ','final '])expect(text).not.toContain(raw);
 // b: both original and proposed kickoffs are drawn; list leads with the change
 await expect(page.locator('.mk.overlay-match')).toHaveCount(15);await expect(page.locator('.mk.proposed')).toHaveCount(15);
 await expect(page.locator('.match-row .move').first()).toContainText('→');
 await expect(page.locator('.match-row')).toHaveCount(15);
 // g: whole day visible without horizontal scrolling; h: markers never cover cell numbers
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const grid=page.locator('.heat-grid');
 expect(await grid.evaluate(g=>g.scrollWidth<=g.clientWidth+1)).toBe(true);
 const overlap=await page.evaluate(()=>{const cells=[...document.querySelectorAll('.heat-cell')].map(c=>c.getBoundingClientRect());
  return [...document.querySelectorAll('.mk')].some(m=>{const r=m.getBoundingClientRect();return cells.some(c=>r.left<c.right-1&&r.right>c.left+1&&r.top<c.bottom-1&&r.bottom>c.top+1);});});
 expect(overlap).toBe(false);
 const hours=await page.evaluate(()=>{const g=document.querySelector('.heat-grid').getBoundingClientRect();return [...document.querySelectorAll('.heat-cell')].filter(c=>{const r=c.getBoundingClientRect();return r.left>=g.left-1&&r.right<=g.right+1;}).length;});
 expect(hours).toBe(42);
 await page.screenshot({path:path.resolve('../data/output/design/'+testInfo.project.name+'-dashboard.png'),fullPage:true});
});
test('8/8 dashboard lists the five postponed matches with reasons and links the two-day scene',async({page})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed-0808');
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 const box=page.locator('.postponed-box');
 await expect(box.locator('h3')).toHaveText('연기 제안 5경기');
 for(const name of ['1조 2경기','4조 1경기','준결승 1','준결승 2','결승'])await expect(box).toContainText(name);
 await expect(box).toContainText('앞선 경기(준결승 1, 준결승 2)가 연기되어 함께 연기합니다.');
 await box.getByRole('link',{name:'이틀 일정으로 다시 짜면'}).click();
 await expect(page).toHaveURL(/#snapshot-observed-0808-2day$/);
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await expect(page.getByRole('group',{name:'대회 날짜'}).getByRole('button')).toHaveCount(2);
});
test('dashboard has no serious or critical accessibility violations',async({page})=>{
 await openProposal(page);
 const result=await new AxeBuilder({page}).include('main').analyze();
 const bad=result.violations.filter(v=>['serious','critical'].includes(v.impact)).map(v=>v.id+': '+v.nodes.length);
 expect(bad).toEqual([]);
});
