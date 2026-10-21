import {test,expect} from '@playwright/test';
// M1/M2: venue form explains surface handling; tournament form shows football as the fixed sport.
test('settings show the surface notice and the fixed sport',async({page})=>{
 await page.goto('/#live');await page.locator('nav').getByRole('button',{name:'설정'}).click();
 await expect(page.locator('.surface-note').first()).toContainText('표면 보정값은 0℃');
 // M2: sport is shown as football (fixed for the MVP).
 await expect(page.getByText('종목: 축구 (MVP 고정)',{exact:true})).toBeVisible();
 await expect(page.getByRole('textbox',{name:/종목/})).toHaveValue('축구');
});
