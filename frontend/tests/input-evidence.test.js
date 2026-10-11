import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createBundleAPI} from '../src/demo/snapshot-core.js';
const load=name=>JSON.parse(readFileSync(new URL('../src/demo/'+name+'.json',import.meta.url),'utf8'));
for(const prefix of ['snapshot','observed-snapshot'])test(prefix+' input evidence is versioned, preserves zero vs missing and stays readonly',async()=>{
 const b=load(prefix),input=load(prefix+'-input-evidence'),x=load(prefix+'-exports'),before=JSON.stringify(input),id=b.approved.id;
 const {api}=createBundleAPI(b,x,load(prefix+'-evidence'),input);
 await api('/replays',{date:b.approved.tournament.date_start,tournament_id:b.approved.tournament.id});
 assert.equal(Object.keys(input.inputs).length,72);
 for(const r of b.approved.risks){
  const params=new URLSearchParams({venue_id:r.venue_id,valid_time:r.valid_time});
  const e=await api('/sessions/'+id+'/input-evidence?'+params);
  assert.deepEqual(e.risk,r);assert.equal(e.solar_observed,r.inputs.weather.solar_wm2!==null);
  // Regenerated 2026-10-11 bundles carry the captured (empty) manual history.
  assert.equal(e.audit.history_known,true);assert.deepEqual(e.audit.rows,[]);
 }
 assert.equal(JSON.stringify(input),before);
});
test('input evidence from a mismatched snapshot is rejected',()=>{
 assert.throws(()=>createBundleAPI(load('snapshot'),load('snapshot-exports'),load('snapshot-evidence'),load('observed-snapshot-input-evidence')),/버전/);
});
