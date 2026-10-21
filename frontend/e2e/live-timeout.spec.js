import {test,expect} from '@playwright/test';
test('timeout keeps cooldown visible and leads to observed offline demonstration',async({page})=>{
 const fixture=await (await page.request.post('/api/live-observations',{data:{mode:'mock'}})).json();
 await page.route('**/api/live-observations',route=>route.fulfill({json:{...fixture,status:'error',observation:null,risks:[],retry_after_seconds:50,
  error:{stage:'네트워크 연결',message:'요청 시간이 초과되었습니다. 호출 간격 후 다시 갱신하거나 시연 스냅샷을 사용하세요.',http_status:null,exception_class:'TimeoutError'}}}));
 await page.goto('/#live');const panel=page.getByRole('region',{name:'최신 관측과 WBGT 추정'});
 await panel.getByLabel('최신 관측 연결').selectOption('api');
 await panel.getByRole('button',{name:'최신 관측 갱신',exact:true}).click();
 await expect(panel.getByRole('alert')).toContainText('요청 시간이 초과');
 await expect(panel).toContainText('50초 후 다시 갱신 가능');
 await expect(panel).toContainText('연결 실패는 키 오류로 단정하지 않습니다');
 await expect(panel.getByRole('table',{name:'최신 WBGT 추정'})).toHaveCount(0);
 let apiCalls=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))apiCalls++;});
 await panel.getByRole('link',{name:'관측 시연 스냅샷으로 이동'}).click();
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await expect(page.locator('h1')).toHaveText('대시보드');expect(apiCalls).toBe(0);
});
