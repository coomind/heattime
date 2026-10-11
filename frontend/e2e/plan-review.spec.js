import {test,expect} from '@playwright/test';

for(const mode of ['snapshot','snapshot-observed'])test(mode+' stronger proof and fixed-plan review work fully offline',async({page,context})=>{
 let requests=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))requests++;});
 await page.route('**/api/**',r=>r.abort());await page.goto('/#'+mode);
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await context.setOffline(true);await page.reload();
 await page.getByText('실측 없이 확인한 기술 근거 · 더 강한 비교와 조건 변화',{exact:true}).click();
 const proof=page.locator('.no-field-evidence');
 await expect(proof).toContainText('552 → 555건');await expect(proof).toContainText('15 → 15일');
 await expect(proof).toContainText('4.15% 감소');
 await expect(proof.getByRole('table',{name:'단순 방식4종 전체 비교'}).locator('tbody tr')).toHaveCount(5);
 await expect(proof.getByRole('table',{name:'59일 고정 일정 조건 변화'}).locator('tbody tr')).toHaveCount(5);
 await proof.getByText('62일 강한 기준 비교 원자료',{exact:true}).click();
 await expect(proof.getByRole('table',{name:'62일 강한 기준 비교'}).locator('tbody tr')).toHaveCount(62);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await page.getByText('조건 변화 검토 · 추정 상승과 자료 누락',{exact:true}).click();
 const review=page.locator('.plan-review');
 await expect(review.getByRole('table',{name:'고정 일정 조건 변화'}).locator('tbody tr')).toHaveCount(5);
 await expect(review).toContainText('승인 전 자동 제안');await expect(review).toContainText('오차 범위');
 await expect(review.getByRole('table',{name:'고정 일정 조건 변화'})).toContainText('기상 자료 누락');
 await review.getByText('경기별 중지 기준과 판정값의 차이',{exact:true}).click();
 await expect(review.getByRole('table',{name:'경기별 중지 기준 차이'}).locator('tbody tr')).toHaveCount(mode==='snapshot'?1:13); // 2026-08-10 observed snapshot: 13 assigned matches (semi2/final postponed)
 await page.getByRole('button',{name:'제안 승인',exact:true}).click();
 // Approval remounts the review so stale proposed/approved evidence cannot mix.
 await page.getByText('조건 변화 검토 · 추정 상승과 자료 누락',{exact:true}).click();
 await review.getByRole('combobox',{name:'검토할 일정'}).selectOption('approved');
 await expect(review.getByRole('heading',{name:'승인된 일정',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(requests).toBe(0);await context.setOffline(false);
});
