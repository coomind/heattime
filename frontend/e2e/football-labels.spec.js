import {test,expect} from '@playwright/test';
// B-3: a FIFPRO-policy tournament shows the football stage names, not the general policy's.
test('football policy replay uses FIFPRO stage labels',async({page})=>{
 await page.goto('/');
 const t=await (await page.request.get('/api/tournaments/demo')).json();
 const id='fifpro-'+Date.now();
 expect((await page.request.post('/api/tournaments',{data:{...t,id,name:'축구 정책 검사 · 가상 예시',policy_id:'football'}})).status()).toBe(201);
 const teams=(await (await page.request.get('/api/teams')).json()).filter(x=>x.tournament_id==='demo').slice(0,2);
 const ids=[];for(const [i,team] of teams.entries()){const tid=id+'-t'+i;ids.push(tid);expect((await page.request.post('/api/teams',{data:{...team,id:tid,tournament_id:id}})).status()).toBe(201);}
 expect((await page.request.post('/api/matches',{data:{id:id+'-m1',tournament_id:id,round:'조별',team_a:ids[0],team_b:ids[1],venue_id:'mock-suwon-a',scheduled_start:t.date_start+'T10:00:00+09:00',duration_min:40,depends_on:[]}})).status()).toBe(201);
 await page.reload();
 await page.getByRole('combobox',{name:'대회',exact:true}).selectOption(id);
 await page.getByRole('button',{name:'재현 시뮬레이션 실행 →',exact:true}).click();
 const summary=page.locator('.summary');
 await expect(summary).toContainText('연기 권고');await expect(summary).toContainText('냉각 조치');
 await expect(summary).not.toContainText('운동 중지');
});
