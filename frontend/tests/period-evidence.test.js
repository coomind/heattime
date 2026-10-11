import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const read=url=>JSON.parse(readFileSync(new URL(url,import.meta.url),'utf8'));
const data=read('../src/demo/period-evidence.json');
const original=read('../../docs/real-data/replay-results.json');
const comparison=read('../../docs/competition-evidence/method-comparison.json');
test('all 62 observed dates and original numeric results are present without favorable filtering',()=>{
  assert.equal(data.days.length,62);
  assert.deepEqual(data.days.map(r=>r.date),original.days.map(r=>r.date));
  for(let i=0;i<62;i++)for(const [key,value] of Object.entries(data.days[i]))assert.deepEqual(value,original.days[i][key]);
  assert.equal(data.days.filter(r=>r.postponed===0).length,15);
  assert.deepEqual(data.days.filter(r=>r.assigned===0).map(r=>r.date),['2026-07-11','2026-07-12','2026-07-13','2026-07-31','2026-08-01','2026-08-03','2026-08-04','2026-08-05','2026-08-06','2026-08-07']);
});
test('comparison includes the adverse common heat result and all daily method comparisons',()=>{
  assert.deepEqual(data.comparison.summary,comparison.summary);
  assert.equal(data.comparison.summary.cp_common_heat-data.comparison.summary.greedy_common_heat,3388);
  for(let i=0;i<62;i++)for(const [key,value] of Object.entries(data.comparison.days[i]))assert.deepEqual(value,key==='common_count'?comparison.days[i].common_match_ids.length:comparison.days[i][key]);
});
test('UI source digests and sample provenance match committed evidence files',()=>{
  for(const name of ['replay-results.json','method-comparison.json']){
    const path=name==='replay-results.json'?'../../docs/real-data/':'../../docs/competition-evidence/';
    const digest=createHash('sha256').update(readFileSync(new URL(path+name,import.meta.url),'utf8').replaceAll('\r\n','\n')).digest('hex');
    assert.equal(data.source_sha256[name],digest);
  }
  assert.equal(data.original_sample_sha256,original.original_sample_sha256);
  assert.equal(data.station.id,'119');
  assert.equal(data.assumptions,'경기장 보정 +2.5℃, 유소년 추정 상단값 판정, 동일 관측소 1곳 공유, 이 가상 대회의 대진·휴식·운영시간·일몰 제약');
});
