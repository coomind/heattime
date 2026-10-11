import {test,expect} from '@playwright/test';
// B-9: in-page hash changes switch views without a reload and never keep the previous route's session.
test('hash route changes switch between team view, snapshot and normal mode',async({page})=>{
 await page.goto('/');
 const run=await page.request.post('/api/replays',{data:{date:'2026-08-01',tournament_id:'demo'}});const session=await run.json();
 await page.request.post('/api/sessions/'+session.id+'/optimize',{data:{}});
 await page.request.post('/api/sessions/'+session.id+'/decision',{data:{action:'accepted',reason:'경로 전환 검사'}});
 await page.evaluate(id=>{location.hash='#team='+id;},session.id);
 await expect(page.getByRole('heading',{name:'참가팀 읽기 전용 일정'})).toBeVisible();
 await expect(page.locator('nav button')).toHaveCount(1);
 await page.evaluate(()=>{location.hash='';});
 await expect(page.locator('nav button')).toHaveCount(8);
 await expect(page.getByRole('heading',{name:'재현 모드',level:1})).toBeVisible();
 await expect(page.getByRole('heading',{name:'참가팀 읽기 전용 일정'})).toHaveCount(0);
 await page.evaluate(()=>{location.hash='#snapshot-observed';});
 await expect(page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true})).toBeVisible();
 await page.evaluate(()=>{location.hash='';});
 await expect(page.getByRole('button',{name:'재현 시뮬레이션 실행 →',exact:true})).toBeVisible();
});
