import {test,expect} from '@playwright/test';
// Match detail explains which time window decided the match stage (computed from hourly risks).
test('match detail states the stage window for the original and proposed schedule',async({page})=>{
 await page.route('**/api/**',r=>r.abort());await page.goto('/#snapshot-observed');
 await page.getByRole('button',{name:'스냅샷 재현 실행 →',exact:true}).click();
 await page.getByRole('button',{name:'재편성 실행',exact:true}).click();
 await page.locator('.match-row').first().click();
 // The note sits in the collapsed "자세히" section of the restructured match detail.
 await page.getByText('자세히',{exact:true}).click();
 const note=page.locator('.stage-window');
 // First listed match on 2026-08-10 is the final: original 18:00 (40 min + 5 min half break = 18:45), stage 3 at 18시.
 await expect(note).toContainText('단계 판정 창은 18:00~18:45입니다(45분)');
 await expect(note).toContainText('가장 높은 3단계(엄중경계)를 경기 단계로 씁니다.');
 // Proposed 18:45 kickoff: the window still uses the pre-shortening length, the shortened match ends 19:20.
 await expect(note).toContainText('제안 일정:');await expect(note).toContainText('단축 전 길이 기준');
 await expect(note).toContainText('실제 경기는 시간을 줄여 19:20에 끝납니다.');
});
