import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createBundleAPI} from '../src/demo/snapshot-core.js';
const load=name=>JSON.parse(readFileSync(new URL('../src/demo/'+name+'.json',import.meta.url),'utf8'));
for(const prefix of ['snapshot','observed-snapshot'])test(prefix+' condition review preserves proposal/approval gates and immutable references',async()=>{
 const b=load(prefix),review=load(prefix+'-plan-review'),before=JSON.stringify(review),id=b.approved.id;
 const {api}=createBundleAPI(b,load(prefix+'-exports'),null,null,review);
 await api('/replays',{date:b.approved.tournament.date_start,tournament_id:b.approved.tournament.id});
 await assert.rejects(api('/sessions/'+id+'/plan-review'),/제안/);
 await api('/sessions/'+id+'/optimize',{});
 const proposed=await api('/sessions/'+id+'/plan-review');assert.deepEqual(proposed,review.proposed);
 assert.equal(proposed.scenarios.length,4);assert.equal(proposed.base.needs_review,false);
 proposed.matches.length=0;assert.deepEqual(await api('/sessions/'+id+'/plan-review'),review.proposed);
 await assert.rejects(api('/sessions/'+id+'/plan-review?view=approved'),/승인/);
 await assert.rejects(api('/sessions/'+id+'/plan-review?view=invalid'),/보기/);
 await api('/sessions/'+id+'/decision',{action:'accepted',reason:b.approved.decision.reason});
 assert.deepEqual(await api('/sessions/'+id+'/plan-review?view=approved'),review.approved);
 assert.equal(JSON.stringify(review),before);
});
test('condition review refuses mismatched or missing snapshot evidence',async()=>{
 assert.throws(()=>createBundleAPI(load('snapshot'),load('snapshot-exports'),null,null,load('observed-snapshot-plan-review')),/버전/);
 const b=load('snapshot'),{api}=createBundleAPI(b,load('snapshot-exports'));
 await api('/replays',{date:b.approved.tournament.date_start,tournament_id:b.approved.tournament.id});
 await api('/sessions/'+b.approved.id+'/optimize',{});
 await assert.rejects(api('/sessions/'+b.approved.id+'/plan-review'),/자료/);
});
test('strong baseline evidence covers all dates, favourable baseline choice and common-game aggregates',()=>{
 const data=load('no-field-analysis');assert.equal(data.days.length,62);
 let assigned=0,heat=0,cpHeat=0,complete=0;
 for(const d of data.days){
  const names=Object.keys(d.baselines).filter(n=>n!=='best_of_four');
  names.sort((a,b)=>d.baselines[b].assigned-d.baselines[a].assigned||d.baselines[a].secondary_cost-d.baselines[b].secondary_cost||a.localeCompare(b));
  const best=d.baselines.best_of_four;assert.equal(best.selected_method,names[0]);
  assigned+=best.assigned;complete+=best.postponed===0;
  heat+=d.comparisons.best_of_four.baseline_common_heat;cpHeat+=d.comparisons.best_of_four.cp_common_heat;
  assert.equal(best.assigned+best.postponed,15);
  if(!d.cp.assigned)assert(d.plan_review.scenarios.every(s=>!s.applicable&&!s.same_choices_valid));
 }
 assert.equal(data.summary.baselines.best_of_four.assigned,assigned);
 assert.equal(data.summary.baselines.best_of_four.complete_days,complete);
 assert.equal(data.summary.baselines.best_of_four.baseline_common_heat,heat);
 assert.equal(data.summary.baselines.best_of_four.cp_common_heat,cpHeat);
});
