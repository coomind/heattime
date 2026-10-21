import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {scheduleOutcome} from '../src/schedule-outcome.js';

const observed = JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json', import.meta.url), 'utf8')).approved;
const matches = [{id:'a'}, {id:'b'}, {id:'c'}];
const recommendations = [{match_id:'a',level:4}, {match_id:'b',level:4}, {match_id:'c',level:2}];
const proposal = {assignments:[{match_id:'a'},{match_id:'c'}], postponed:[{match_id:'b'}],
  common_match_ids:['a','c'], original_heat_score:100, proposed_heat_score:70};

// Demo date 2026-08-10, rule (나) 2026-10-21: 15 assigned, none postponed, all 4 originally stopped matches assigned.
test('observed August 10 proposal shows 15 assigned, none postponed and all four originally stopped matches', () => {
  const outcome = scheduleOutcome(observed.matches, observed.recommendations, observed.proposal);
  assert.deepEqual({...outcome, reductionPercent:Number(outcome.reductionPercent.toFixed(2))},
    {total:15,assigned:15,postponed:0,originalStop:4,reassignedStop:4,common:15,scoreReduction:1120,reductionPercent:21.24});
  assert.deepEqual(observed.proposal.postponed,[]);
});
test('partial proposal counts postponed separately and uses only the supplied common-game score', () => {
  assert.deepEqual(scheduleOutcome(matches, recommendations, proposal),
    {total:3,assigned:2,postponed:1,originalStop:2,reassignedStop:1,common:2,scoreReduction:30,reductionPercent:30});
});
test('all postponed produces no score comparison rather than a reduction claim', () => {
  const result = scheduleOutcome(matches, recommendations, {...proposal,assignments:[],postponed:matches.map(m=>({match_id:m.id})),common_match_ids:[],original_heat_score:0,proposed_heat_score:0});
  assert.equal(result.assigned,0);assert.equal(result.postponed,3);
  assert.equal(result.common,0);assert.equal(result.scoreReduction,null);assert.equal(result.reductionPercent,null);
});
test('zero original score does not divide by zero or claim a percentage', () => {
  const result = scheduleOutcome(matches, recommendations, {...proposal,original_heat_score:0,proposed_heat_score:7});
  assert.equal(result.scoreReduction,-7);assert.equal(result.reductionPercent,null);
});
test('increased exposure remains a negative reduction and is not presented as improvement', () => {
  const result = scheduleOutcome(matches, recommendations, {...proposal,proposed_heat_score:120});
  assert.equal(result.scoreReduction,-20);assert.equal(result.reductionPercent,-20);
});
test('unchanged exposure has zero change', () => {
  const result = scheduleOutcome(matches, recommendations, {...proposal,proposed_heat_score:100});
  assert.equal(result.scoreReduction,0);assert.equal(result.reductionPercent,0);
});
test('benign original scenario does not invent stopped matches', () => {
  const result = scheduleOutcome(matches, recommendations.map(r=>({...r,level:2})),proposal);
  assert.equal(result.originalStop,0);assert.equal(result.reassignedStop,0);
});
test('counts belong to actual distinct tournament matches and the helper never modifies results', () => {
  const input = {...proposal,assignments:[...proposal.assignments,{match_id:'a'},{match_id:'outside'}],common_match_ids:['a','a','c','outside']};
  const before = structuredClone(input);
  const result = scheduleOutcome(matches,[...recommendations,{match_id:'outside',level:4}],input);
  assert.equal(result.total,3);assert.equal(result.assigned,2);assert.equal(result.common,2);assert.equal(result.originalStop,2);
  assert.deepEqual(input,before);
});
