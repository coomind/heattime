import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {stageWindow} from '../src/stage-window.js';
for(const name of ['observed-snapshot','snapshot'])test(name+': window stage equals the engine stage for every original and proposed match',()=>{
 const s=JSON.parse(readFileSync(new URL(`../src/demo/${name}.json`,import.meta.url),'utf8')).approved;
 const cool=s.engine_settings.cooling_min;
 for(const m of s.matches){
  const rec=s.recommendations.find(r=>r.match_id===m.id);
  const w=stageWindow(m,s.risks,m.venue_id,m.scheduled_start,cool);
  if(rec.wbgt_c===null){assert.ok(w.missing);continue;}
  assert.equal(w.level,rec.level,m.id);
 }
 for(const a of s.proposal.assignments){
  const m=s.matches.find(x=>x.id===a.match_id);
  assert.equal(stageWindow(m,s.risks,a.venue_id,a.start,cool).level,a.level,a.match_id);
 }
});
