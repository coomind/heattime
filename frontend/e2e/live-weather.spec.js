import {test,expect} from '@playwright/test';
test('latest weather mock and injected API observation show source, estimates, quota and stale failure',async({page})=>{
 const fixture=await (await page.request.post('/api/live-observations',{data:{mode:'mock'}})).json();
 let liveCalls=0;page.on('request',r=>{if(new URL(r.url()).pathname==='/api/live-observations')liveCalls++;});
 await page.goto('/');const panel=page.getByRole('region',{name:'최신 관측과 WBGT 추정'});
 await expect(panel.getByLabel('최신 관측 연결')).toHaveValue('mock');expect(liveCalls).toBe(0);
 await panel.getByRole('button',{name:'최신 관측 갱신',exact:true}).click();
 await expect(panel).toContainText('합성 입력 · 가상 예시');await expect(panel).toContainText('이 앱 사용량: 0회');
 await expect(panel.getByRole('table',{name:'최신 WBGT 추정'}).locator('tbody tr')).toHaveCount(3);
 const observed={...fixture,status:'ready',usage:{...fixture.usage,calls:1,bytes:300},observation:{...fixture.observation,is_mock:false}};
 let injected=0;
 await page.route('**/api/live-observations',async route=>{
  expect(route.request().postDataJSON().mode).toBe('api');injected++;
  await route.fulfill({json:injected===1?observed:{...observed,status:'error',error:{stage:'HTTP 응답',message:'AWS 매분자료 1.1 활용신청을 확인하세요.',http_status:403,exception_class:'HTTPError'}}});
 });
 await panel.getByLabel('최신 관측 연결').selectOption('api');await expect(panel.getByRole('table',{name:'최신 WBGT 추정'})).toHaveCount(0);
 await panel.getByRole('button',{name:'최신 관측 갱신',exact:true}).click();
 await expect(panel).toContainText('기상청 관측 자료(수원 119)');await expect(panel).toContainText('관측 시각');await expect(panel).toContainText('가져온 시각');
 await expect(panel).toContainText('일사·운량은 이 응답에 없습니다');await expect(panel).toContainText('운량 0.7 가정');
 await expect(panel).toContainText('계정 전체 사용량은 API허브에서 확인');await expect(panel).toContainText('검증된 신뢰구간이 아니며');
 await panel.getByRole('button',{name:'최신 관측 갱신',exact:true}).click();
 await expect(panel.getByRole('alert')).toContainText('HTTP 403');await expect(panel).toContainText('갱신 실패 · 이전 관측');
 await expect(panel.getByRole('table',{name:'최신 WBGT 추정'}).locator('tbody tr')).toHaveCount(3);
 await panel.getByLabel('관측 지점번호').fill('0');await expect(panel.getByRole('button',{name:'최신 관측 갱신',exact:true})).toBeDisabled();
 expect(injected).toBe(2);expect(liveCalls).toBe(3);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('snapshot latest weather stays disabled and never requests API',async({page})=>{
 let calls=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))calls++;});
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 const panel=page.getByRole('region',{name:'최신 관측과 WBGT 추정'});
 await expect(panel.getByRole('button',{name:'최신 관측 갱신',exact:true})).toBeDisabled();
 await expect(panel.getByLabel('최신 관측 연결')).toBeDisabled();
 await expect(panel).toContainText('시연 스냅샷에서는 최신 관측을 호출하지 않습니다');expect(calls).toBe(0);
});
