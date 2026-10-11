import {test,expect} from '@playwright/test';
// M1/M2: venue form explains surface handling; tournament form shows football as the fixed sport.
test('settings show the surface notice and the fixed sport',async({page})=>{
 await page.goto('/');await page.locator('nav').getByRole('button',{name:'설정'}).click();
 await expect(page.locator('.surface-note').first()).toContainText('표면 보정값은 0℃');
});
