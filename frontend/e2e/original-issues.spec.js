import {test,expect} from '@playwright/test';
// The comparison screen lists the original schedule's hard-constraint issues automatically.
for(const offline of [true,false])test(`comparison lists original schedule issues ${offline?'offline snapshot':'live replay'}`,async({page})=>{
 if(offline){await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();}
 else{await page.goto('/');await page.getByRole('button',{name:'재현 시뮬레이션 실행 →',exact:true}).click();await expect(page.getByRole('heading',{name:'구장 × 시간 위험도'})).toBeVisible();}
 await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 const box=page.locator('.original-issues');
 await expect(box).toContainText('원래 일정은 작성자가 정한 가상 기준이며 다음 제약을 충족하지 않습니다.');
 await expect(box).toContainText('1조 1경기(10:00~10:45)와 4조 1경기(10:45~11:30)');
 await expect(box).toContainText('구장 정리 5분이 확보되지 않음');
});
