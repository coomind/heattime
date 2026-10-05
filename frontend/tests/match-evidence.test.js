import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createBundleAPI} from '../src/demo/snapshot-core.js';
const load=name=>JSON.parse(readFileSync(new URL('../src/demo/'+name+'.json',import.meta.url),'utf8'));
for(const prefix of ['snapshot','observed-snapshot'])test(prefix+' details follow replay/proposal/approval without changing frozen source',async()=>{
 const b=load(prefix),x=load(prefix+'-exports'),e=load(prefix+'-evidence'),before=JSON.stringify(b);
 const api=createBundleAPI(b,x,e).api,id=b.approved.id,body={date:b.approved.tournament.date_start,tournament_id:b.approved.tournament.id};
 const mid=b.approved.proposal.assignments[0].match_id;
 await api('/replays',body);
 await assert.rejects(api('/sessions/'+id+'/matches/'+mid+'/evidence'),/자동 제안/);
 await api('/sessions/'+id+'/optimize',{});
 const proposed=await api('/sessions/'+id+'/matches/'+mid+'/evidence');
 assert.equal(proposed.state,'unapproved');assert.equal(proposed.constraints.operating_ok,true);
 await assert.rejects(api('/sessions/'+id+'/matches/'+mid+'/evidence?view=approved'),/승인/);
 await api('/sessions/'+id+'/decision',{action:'accepted',reason:b.approved.decision.reason});
 const approved=await api('/sessions/'+id+'/matches/'+mid+'/evidence?view=approved');
 assert.equal(approved.state,'approved');assert.deepEqual(approved.assignment,proposed.assignment);
 assert.equal(JSON.stringify(b),before);
});
test('a detail asset from a different frozen version is rejected',()=>{
 assert.throws(()=>createBundleAPI(load('snapshot'),load('snapshot-exports'),load('observed-snapshot-evidence')),/버전/);
});
