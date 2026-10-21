import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {OBSERVED_SCENES,DEFAULT_HASH,parseSceneHash} from '../src/demo/scenes.js';
import {scheduleOutcome} from '../src/schedule-outcome.js';
const load=name=>JSON.parse(readFileSync(new URL(`../src/demo/${name}.json`,import.meta.url),'utf8')).approved;
test('scene hashes and their team views resolve; other hashes are not scenes',()=>{
 assert.equal(DEFAULT_HASH,'#snapshot-observed');
 assert.deepEqual(OBSERVED_SCENES.map(s=>s.key),['demo','extreme','extreme-2day']);
 assert.equal(parseSceneHash('#snapshot-observed-0808').scene.key,'extreme');
 assert.deepEqual(parseSceneHash('#snapshot-observed-0808-2day-team'),{scene:OBSERVED_SCENES[2],team:true});
 assert.equal(parseSceneHash('#snapshot').scene.key,'synthetic');
 for(const h of ['','#live','#team=abc','#snapshot-unknown'])assert.equal(parseSceneHash(h),null);
});
test('8/8 scene: 10 assigned and five postponement candidates; the two-day scene assigns all fifteen',()=>{
 const hot=load('observed-snapshot-0808');
 const o=scheduleOutcome(hot.matches,hot.recommendations,hot.proposal);
 assert.deepEqual([o.assigned,o.postponed,o.originalStop],[10,5,14]);
 assert.deepEqual(hot.proposal.postponed.map(p=>p.match_id).sort(),['final','g1-2','g4-1','semi1','semi2']);
 const two=load('observed-snapshot-0808-2day');
 assert.deepEqual([two.tournament.date_start,two.tournament.date_end],['2026-08-08','2026-08-09']);
 assert.equal(two.proposal.assignments.length,15);assert.equal(two.proposal.postponed_count,0);
 for(const s of [hot,two])assert.ok(s.decision.reason.startsWith('가상 시연입니다.'));
});
