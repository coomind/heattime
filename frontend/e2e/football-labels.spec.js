import {test,expect} from '@playwright/test';
// B-3: a FIFPRO-policy tournament shows the football stage names, not the general policy's.
test('football policy replay uses FIFPRO stage labels',async({page})=>{
 await page.goto('/#live');
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

// W-1: the general policy's stage 0 is shown as '통상 운영'; the guideline label appears only as the sourced reference.
test('general policy stage 0 is labelled 통상 운영 and the source label stays in match detail',async({page})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 const summary=page.locator('.summary');
 await expect(summary).toContainText('통상 운영');await expect(summary).not.toContainText('거의 안전');
 await page.locator('.match-row').first().click();
 await expect(page.locator('.source-labels')).toContainText('원 지침 단계명(출처 표기): 0 거의 안전');
});
