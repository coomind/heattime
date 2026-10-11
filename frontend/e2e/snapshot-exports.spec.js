import {test,expect} from '@playwright/test';
// B-4: before approval, snapshot PDF/CSV are disabled with a reason (no dead '#' links); JSON works.
test('snapshot exports before approval are explained and after approval download',async({page,context})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.locator('nav').getByRole('button',{name:'운영 기록'}).click();
 await expect(page.getByRole('button',{name:'운영 기록 PDF'})).toBeDisabled();
 await expect(page.getByRole('button',{name:'CSV 내보내기'})).toBeDisabled();
 await expect(page.getByText('제안을 승인한 뒤 내려받으세요',{exact:false})).toBeVisible();
 await expect(page.getByRole('link',{name:'전체 근거 JSON'})).toHaveAttribute('href',/^blob:/);
 await page.locator('nav').getByRole('button',{name:'재편성 비교'}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await page.getByRole('button',{name:'제안 승인',exact:true}).click();
 await page.locator('nav').getByRole('button',{name:'운영 기록'}).click();
 await expect(page.getByRole('link',{name:'운영 기록 PDF'})).toHaveAttribute('href',/^blob:/);
 await expect(page.getByRole('link',{name:'CSV 내보내기'})).toHaveAttribute('href',/^blob:/);
});
