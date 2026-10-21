import {test,expect} from '@playwright/test';
for(const snapshot of [false,true])test(`decision assumptions are visible without changing settings ${snapshot?'offline snapshot':'observed replay'}`,async({page})=>{
 await page.goto(snapshot?'/#snapshot-observed':'/#live');
 if(!snapshot){await expect(page.locator('option[value="observed"]')).toBeEnabled();await page.getByRole('combobox',{name:'기상 자료',exact:true}).selectOption('observed');}
 await page.getByRole('button',{name:snapshot?'스냅샷 재현 실행 →':'재현 시뮬레이션 실행 →',exact:true}).click();
 await expect(page.getByRole('heading',{name:'그날의 관측 기상과 판정 가정'})).toBeVisible();
 // 2026-08-10 observed: max air 31.6C, humidity 44~68% over 24 h and 44~67% in operating hours.
 await expect(page.getByText('시간자료 최고기온 31.6℃',{exact:false})).toBeVisible();
 await expect(page.getByText('운영시간 습도 44~67%',{exact:false})).toBeVisible();
 await expect(page.getByText('습도 44~68% (24시간)',{exact:false})).toBeVisible();
 await page.locator('.match-row').first().click();
 // The formula table is in a collapsed section; the stage-window hours come first and the whole day is nested below.
 await page.locator('summary',{hasText:'판정값이 나온 과정'}).click();
 const table=page.getByRole('table',{name:'판정값 계산식',exact:true});
 await expect(table).toBeVisible();
 await page.locator('summary',{hasText:'하루 전체 계산식 보기'}).click();
 const day=page.getByRole('table',{name:'하루 전체 판정값 계산식'});
 await expect(day).toBeVisible();await expect(day.locator('tbody tr')).toHaveCount(24);
 // Rule (나): observed estimate + venue offset 2.500 = central estimate; the ±1.5℃ range is reference only.
 await expect(table).toContainText('2.500');await expect(page.locator('.decision-breakdown')).toContainText('추정 범위는 중앙 추정 ±1.5℃');
 // E-1: every WBGT column is labelled as an estimate and the range column shows low~high.
 await expect(table.locator('thead')).toContainText('판정값 ℃');await expect(table.locator('thead')).toContainText('추정 범위 ℃ (참고)');
 await expect(table.locator('tbody tr').first().locator('td').last()).toContainText('~');
 await expect(page.getByText('설정, 일정, 운영자 승인은 바꾸지 않습니다.',{exact:false})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
