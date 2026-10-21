import {test,expect} from '@playwright/test';
test('initial observed selection waits for metadata and preserves a later manual date',async({page})=>{
 for(let attempt=0;attempt<3;attempt++){
  await page.route('**/api/observations',async route=>{
   const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,150));await route.fulfill({response});
  });
  // Each attempt must be a full load: a goto to the already-open '/#live' is a same-document hash navigation.
  await page.goto('about:blank');await page.goto('/#live');await expect(page.locator('option[value="observed"]')).toBeEnabled();
  await page.getByRole('combobox',{name:'기상 자료',exact:true}).selectOption('observed');
  const date=page.locator('input[type="date"]').first();
  await expect(date).toHaveValue('2026-08-10');
  await date.fill('2026-07-12');await expect(date).toHaveValue('2026-07-12');
  await page.locator('nav').getByRole('button',{name:'설정'}).click();
  await page.locator('nav').getByRole('button',{name:'재현 모드'}).click();
  await expect(date).toHaveValue('2026-07-12');await page.unroute('**/api/observations');
 }
});
