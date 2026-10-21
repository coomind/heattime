import {test,expect} from '@playwright/test';
// Match detail explains which time window decided the match stage (computed from hourly risks).
test('match detail states the stage window for the original and proposed schedule',async({page})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await page.locator('.match-row').first().click();
 const note=page.locator('.stage-window');
 await expect(note).toContainText('단계 판정 창은 10:00~10:45입니다(45분)');
 await expect(note).toContainText('가장 높은 4단계(운동 중지)를 경기 단계로 씁니다.');
 await expect(note).toContainText('제안 일정:');await expect(note).toContainText('단축 전 길이 기준');
 await expect(note).toContainText('실제 경기는 시간을 줄여 09:35에 끝납니다.');
});
