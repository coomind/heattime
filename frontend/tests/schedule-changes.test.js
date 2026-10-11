import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {scheduleChanges} from '../src/schedule-changes.js';

const observed=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json',import.meta.url),'utf8')).approved;
const synthetic=JSON.parse(readFileSync(new URL('../src/demo/snapshot.json',import.meta.url),'utf8')).approved;
// Demo date 2026-08-10: 13 proposal rows, 2 postponed rows (semi2 by constraints, final by its postponed predecessor).
test('observed change rows preserve all original matches and show thirteen original stop assignments plus two postponements',()=>{
  const before=structuredClone(observed),rows=scheduleChanges(observed);
  assert.equal(rows.length,15);assert.equal(rows.filter(r=>r.movedFromStop).length,13);
  assert.equal(rows.filter(r=>r.proposal).length,13);assert.deepEqual(observed,before);
  const postponed=rows.filter(r=>!r.proposal);
  assert.deepEqual(postponed.map(r=>r.match.id).sort(),['final','semi2']);
  assert.ok(postponed.every(r=>r.postponedReason&&r.deltaMinutes===null&&!r.movedFromStop));
  assert.equal(postponed.find(r=>r.match.id==='final').postponedReason,'선행 경기 연기');
  const group=rows.find(r=>r.match.id==='g1-1');
  assert.equal(group.deltaMinutes,-60);assert.equal(group.proposal.start,'2026-08-10T09:00:00+09:00');
});
test('synthetic postponed matches retain reasons and do not invent new start times',()=>{
  const rows=scheduleChanges(synthetic),postponed=rows.filter(r=>!r.proposal);
  assert.equal(postponed.length,synthetic.proposal.postponed_count);
  assert.ok(postponed.length>0);assert.ok(postponed.every(r=>r.postponedReason&&r.deltaMinutes===null&&!r.movedFromStop));
});
test('proposal absence yields no applied change rows',()=>{
  assert.deepEqual(scheduleChanges({...observed,proposal:null}),[]);
});
test('movement minutes use absolute times across dates and differing timezone offsets',()=>{
  const session={matches:[{id:'m',venue_id:'a',scheduled_start:'2026-07-10T10:00:00+09:00'}],recommendations:[{match_id:'m',level:1}],proposal:{assignments:[{match_id:'m',venue_id:'b',start:'2026-07-11T01:00:00Z',level:1}],postponed:[]}};
  const row=scheduleChanges(session)[0];assert.equal(row.deltaMinutes,1440);assert.equal(row.venueChanged,true);assert.equal(row.movedFromStop,false);
});
