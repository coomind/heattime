import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {OPERATOR_ACTIONS,kstText,teamLabel,venueLabel,matchLabel} from '../src/labels.js';
const s=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json',import.meta.url),'utf8')).approved;
test('operator-facing labels replace internal ids and enums',()=>{
 assert.equal(OPERATOR_ACTIONS[s.decision.operator_action],'제안 승인');
 assert.equal(kstText('2026-08-10T09:00:00+09:00'),'2026-08-10 09:00 KST');
 assert.equal(venueLabel(s,'mock-suwon-a'),'수원 가상 구장 A · 가상 예시');
 assert.equal(teamLabel(s,'winner:semi1'),'semi1 승자');
 for(const a of s.decision.assignments){const text=matchLabel(s,a.match_id);assert.ok(!/(^|[^a-z])t[0-9]+([^0-9]|$)/.test(text),text);assert.ok(text.includes(a.match_id));}
});
