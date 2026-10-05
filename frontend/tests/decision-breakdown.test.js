import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {breakdown,counterLevel,capturedRiskRows} from '../src/decision-breakdown.js';
const session=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json',import.meta.url),'utf8')).approved;
test('every frozen observation decision sums and analysis leaves inputs unchanged',()=>{
 const before=JSON.stringify(session);
 for(const r of session.risks){const b=breakdown(r);
  assert.ok(Math.abs(b.model+b.field+b.surface+b.calibration+b.upper-b.decision)<.001);
  assert.equal(b.field,2.5);assert.equal(b.upper,1.5);
  assert.ok(counterLevel(b.counter,session.policy,b.policyId)<=r.level);
 }
 assert.equal(JSON.stringify(session),before);
});
test('football strict boundaries are preserved in display comparison',()=>{
 const p={cooling_above:26,postpone_above:28};
 assert.equal(counterLevel(26,p,'football'),0);assert.equal(counterLevel(26.001,p,'football'),2);
 assert.equal(counterLevel(28,p,'football'),2);assert.equal(counterLevel(28.001,p,'football'),4);
});
test('projected offline risks resolve frozen full inputs by venue and time',()=>{
 const e=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot-evidence.json',import.meta.url),'utf8')).matches['g1-1'];
 assert.ok(e.risks.length>0);assert.ok(e.risks.every(r=>!r.inputs));
 const full=capturedRiskRows(e.risks,session.decision.snapshot.risks);
 assert.equal(full.length,e.risks.length);
 for(let i=0;i<full.length;i++){
  assert.equal(full[i].valid_time,e.risks[i].valid_time);assert.equal(full[i].venue_id,e.risks[i].venue_id);
  assert.equal(breakdown(full[i]).decision,e.risks[i].decision_wbgt_c);
 }
 assert.deepEqual(capturedRiskRows(e.risks,[]),[]);
});
