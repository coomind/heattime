import {test,expect} from '@playwright/test';
// B-1: a two-day tournament shows each day's heatmap and match blocks separately.
test('two-day tournament heatmap and Gantt switch by date',async({page})=>{
 await page.goto('/#live');
 const base=await (await page.request.get('/api/tournaments/demo')).json();
 const id='twoday-'+Date.now(),day1=base.date_start;
 const d=new Date(day1+'T00:00:00+09:00');d.setDate(d.getDate()+1);
 const day2=d.toLocaleDateString('sv-SE',{timeZone:'Asia/Seoul'});
 expect((await page.request.post('/api/tournaments',{data:{...base,id,name:'이틀 대회 검사 · 가상 예시',date_end:day2}})).status()).toBe(201);
 const teams=(await (await page.request.get('/api/teams')).json()).filter(x=>x.tournament_id==='demo').slice(0,2);
 const ids=[];for(const [i,team] of teams.entries()){const tid=id+'-t'+i;ids.push(tid);expect((await page.request.post('/api/teams',{data:{...team,id:tid,tournament_id:id}})).status()).toBe(201);}
 for(const [mid,day] of [['d1',day1],['d2',day2]])
  expect((await page.request.post('/api/matches',{data:{id:id+'-'+mid,tournament_id:id,round:'조별',team_a:ids[0],team_b:ids[1],venue_id:'mock-suwon-a',scheduled_start:day+'T10:00:00+09:00',duration_min:40,depends_on:[]}})).status()).toBe(201);
 await page.reload();
 // Live mode now defaults to observed 2026-08-10; this synthetic two-day tournament starts on the demo date.
 await page.getByRole('combobox',{name:'기상 자료',exact:true}).selectOption('mock');
 await page.locator('input[type="date"]').first().fill(day1);
 await page.getByRole('combobox',{name:'대회',exact:true}).selectOption(id);
 await page.getByRole('button',{name:'재현 시뮬레이션 실행 →',exact:true}).click();
 const days=page.getByRole('group',{name:'대회 날짜'});
 await expect(days.getByRole('button')).toHaveCount(2);
 const grid=page.locator('.heat-grid');
 await expect(grid.locator('.overlay-match')).toHaveText([id+'-d1']);
 await days.getByRole('button',{name:'2일차 · '+day2}).click();
 await expect(grid.locator('.overlay-match')).toHaveText([id+'-d2']);
 await expect(grid.locator('.heat-cell')).toHaveCount(14);
});
