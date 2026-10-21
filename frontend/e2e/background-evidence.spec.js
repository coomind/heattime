import {test,expect} from '@playwright/test';
test('background cases and standards are readable offline with sources in new tabs',async({page,context})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
 await context.setOffline(true);await page.reload();
 await page.getByText('폭염 속 경기 운영 사례와 기준 (출처 기사)',{exact:true}).click();
 const card=page.locator('.background-evidence');
 await expect(card).toContainText('온열질환자 3명');await expect(card).toContainText('4,460명');await expect(card).toContainText('25명이 온열질환 의심 증상');
 await expect(card.getByRole('link')).toHaveCount(5);
 for(const link of await card.getByRole('link').all())await expect(link).toHaveAttribute('target','_blank');
 await context.setOffline(false);
});
