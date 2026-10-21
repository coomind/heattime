import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../src/BackgroundEvidence.jsx',import.meta.url),'utf8');
test('background facts are embedded with sources, open in a new tab and make no effect claims',()=>{
 for(const url of ['ytn.co.kr/_ln/0103_202608071805566486','newsis.com/view/NISX20260514_0003629135','mt.co.kr/sports/2026/08/05/2026080516090110265','dailian.co.kr/news/view/1530184','kffhealthnews.org/republish/news/school-sports-programs-states-northern-heat-safety-score'])assert.ok(src.includes(url),url);
 assert.ok(src.includes('target="_blank" rel="noopener noreferrer"'));
 assert.ok(src.includes('히트타임의 효과를 보여 주는 자료가 아니며'));
 for(const banned of ['국내 최초','사고 예방','안전 보장','안전을 보장'])assert.ok(!src.includes(banned),banned);
});
