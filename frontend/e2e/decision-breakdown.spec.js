import {test,expect} from '@playwright/test';
for(const snapshot of [false,true])test(`decision assumptions are visible without changing settings ${snapshot?'offline snapshot':'observed replay'}`,async({page})=>{
 await page.goto(snapshot?'/#snapshot-observed':'/');
 if(!snapshot){await expect(page.locator('option[value="observed"]')).toBeEnabled();await page.getByRole('combobox',{name:'기상 자료',exact:true}).selectOption('observed');}
 await page.getByRole('button',{name:snapshot?'스냅샷 재현 실행 →':'재현 시뮬레이션 실행 →',exact:true}).click();
 await expect(page.getByRole('heading',{name:'그날의 관측 기상과 판정 가정'})).toBeVisible();
 await expect(page.getByText('시간자료 최고기온 28.4℃',{exact:false})).toBeVisible();
 await expect(page.getByText('습도 75~90%',{exact:false})).toBeVisible();
 await expect(page.getByText('습도 75~93%',{exact:false})).toBeVisible();
 await page.locator('.match-row').first().click();
 const table=page.getByRole('table',{name:'판정값 분해와 분석용 비교'});
 await expect(table).toBeVisible();await expect(table.locator('tbody tr')).toHaveCount(24);
 await expect(table).toContainText('2.500');await expect(table).toContainText('1.500');
 await expect(page.getByText('설정·일정·운영자 승인을 바꾸지 않습니다.',{exact:false})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
