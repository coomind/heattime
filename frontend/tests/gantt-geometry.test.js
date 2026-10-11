import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {occupiedMinutes} from '../src/gantt-geometry.js';
const s=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json',import.meta.url),'utf8')).approved;
test('original and proposed blocks use the same occupied-time basis',()=>{
 for(const m of s.matches){
  const rec=s.recommendations.find(r=>r.match_id===m.id);
  // Nominal occupied time = play + half break; recommendations may add cooling or shorten from it.
  assert.equal(occupiedMinutes(m),m.duration_min+(m.halves-1)*m.half_break_min);
  if(rec.action==='none')assert.equal(occupiedMinutes(m),rec.duration_min);
 }
 for(const a of s.proposal.assignments)assert.equal(occupiedMinutes(a),a.duration_min);
 const original=s.matches.find(m=>m.id==='g1-1');assert.ok(occupiedMinutes(original)>original.duration_min);
});
