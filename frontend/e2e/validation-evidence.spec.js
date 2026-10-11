import {test,expect} from '@playwright/test';
import {randomUUID} from 'node:crypto';
test('mock work evidence cannot manufacture actual outcomes and retains unfavourable feedback',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:/검증 기록$/}).click();
 await expect(page.getByRole('heading',{name:'운영자 업무 비교와 현장 대조 기록'})).toBeVisible();
 await expect(page.locator('main')).not.toContainText('수상');
 const panel=page.getByRole('region',{name:'운영자 업무 비교 기록'});
 const code='sample_'+randomUUID().slice(0,8);
 await panel.getByLabel('원자료 코드').fill(code);
 await panel.getByLabel('수행·측정 시각 (KST)').fill('2026-07-10T12:00');
 await panel.getByLabel('참여자 코드').fill('MOCK');await panel.getByLabel('사례 코드').fill(code);
 await panel.getByLabel('동일 비교 조건 확인').check();
 for(const [legend,times] of [['현재 방식',[5,10,5]],['HeatTime',[10,10,5]]]){
  const field=panel.locator('fieldset').filter({has:page.locator('legend',{hasText:new RegExp('^'+legend+'$')})});
  for(const [label,time] of [['준비 시간 (분)',times[0]],['변경 시간 (분)',times[1]],['안내·기록 시간 (분)',times[2]]])await field.getByLabel(label,{exact:true}).fill(String(time));
  await field.getByLabel('하드 제약 확인').selectOption('passed');
 }
 await panel.getByLabel('불편·거절 이유').fill('CSV 준비 시간이 더 길었습니다');
 await panel.getByLabel('구매 응답 그대로').fill('도입 거절');
 await panel.getByRole('button',{name:'업무 비교 저장'}).click();
 await expect(page.getByRole('status')).toContainText('근거 기록을 저장했습니다');
 const row=page.getByRole('table',{name:'검증 기록 목록'}).getByRole('row').filter({hasText:code});
 await expect(row).toContainText('가상 예시 · 실제 성과 제외');await expect(row).toContainText('20.00분 → HeatTime 25.00분');
 await expect(row).toContainText('도입 거절');
 const data=await (await page.request.get('/api/validation/summary')).json();
 expect(data.work.actual_records).toBe(0);expect(data.work.median_saved_min).toBeNull();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'검증 원자료 CSV'}).click()]);
 expect(download.suggestedFilename()).toBe('heattime-validation.csv');
 const original=data.work_records.find(r=>r.source_ref===code);
 await page.getByLabel('제외할 기록').selectOption(original.id);
 await page.getByLabel('검토 제외 사유').fill('가상 테스트 기록의 시각 오기입');
 await page.getByRole('button',{name:'사유를 남기고 집계 제외'}).click();
 await expect(row).toContainText('검토 제외: 가상 테스트 기록의 시각 오기입');
 const revised=await (await page.request.get('/api/validation/summary')).json();
 expect(revised.work_records.find(r=>r.id===original.id)).toEqual(original);
 expect(revised.exclusions.find(r=>r.record_id===original.id).reason).toBe('가상 테스트 기록의 시각 오기입');
});

test('snapshot validation remains readonly and makes no API request',async({page})=>{
 let calls=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))calls++;});
 await page.goto('/#snapshot-observed');
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:/검증 기록$/}).click();
 await expect(page.getByRole('heading',{name:'검증 기록은 일반 실행에서 작성합니다'})).toBeVisible();
 await expect(page.getByRole('button',{name:'업무 비교 저장'})).toHaveCount(0);
 expect(calls).toBe(0);
});

test('mock measurement keeps frozen range and explicit field exclusions',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'재현 시뮬레이션 실행 →',exact:true}).click();
 await expect(page.locator('h1')).toHaveText('대시보드');
 await page.getByRole('button',{name:/검증 기록$/}).click();
 const panel=page.getByRole('region',{name:'현장 WBGT 대조 기록'});
 const code='meter_'+randomUUID().slice(0,8);
 await panel.getByLabel('원자료 코드').fill(code);
 await panel.getByLabel('수행·측정 시각 (KST)').fill('2026-08-01T12:00');
 await panel.getByLabel('실측 WBGT ℃').fill('30');await panel.getByLabel('측정기 코드').fill(code);
 await panel.getByLabel('프로토콜 코드').fill('mock_protocol');await panel.getByLabel('측정 높이 m').fill('1.2');
 await panel.getByLabel('측정 위치·표면·그늘').fill('가상 예시 위치');
 await panel.getByRole('button',{name:'현장 대조 저장'}).click();
 await expect(page.getByRole('status')).toContainText('근거 기록을 저장했습니다');
 const row=page.getByRole('table',{name:'검증 기록 목록'}).getByRole('row').filter({hasText:code});
 await expect(row).toContainText('가상 구장');await expect(row).toContainText('합성 기상 입력');await expect(row).toContainText('실측 30.00℃ / 추정');
 const data=await (await page.request.get('/api/validation/summary')).json();
 expect(data.field.included_pairs).toBe(0);expect(data.field.mae_c).toBeNull();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('latest estimate can be frozen for later field comparison with no API credentials',async({page})=>{
 await page.goto('/');const live=page.getByRole('region',{name:'최신 관측과 WBGT 추정'});
 await live.getByRole('button',{name:'최신 관측 갱신',exact:true}).click();
 await expect(live).toContainText('합성 입력 · 가상 예시');
 const observedRequests=[];page.on('request',r=>{if(new URL(r.url()).pathname==='/api/live-observations')observedRequests.push(r);});
 await live.getByRole('button',{name:'현장 대조용 추정 보관'}).click();
 await expect(live).toContainText('추정값을 보관했습니다');
 await live.getByRole('button',{name:'검증 기록 열기'}).click();
 await expect(page.getByLabel('대조할 자료')).toBeVisible();
 await expect(page.getByLabel('대조할 자료')).toContainText('가상 예시 · 합성 최신 입력');
 await expect(page.getByLabel('대조할 추정 기록')).toContainText('추정');
 expect(observedRequests.length).toBe(0);
});
