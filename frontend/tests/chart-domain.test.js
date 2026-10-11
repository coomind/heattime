import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chartDomain,integerTicks} from '../src/chart-domain.js';
const s=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json',import.meta.url),'utf8')).approved;
test('chart y-axis spans the estimate range with integer ticks, never from 0 or with raw decimals',()=>{
 const risks=s.risks.filter(r=>r.venue_id==='mock-suwon-a');
 const [lo,hi]=chartDomain(risks,s.policy);
 const lows=Math.min(...risks.map(r=>r.wbgt_low_c)),highs=Math.max(...risks.map(r=>r.wbgt_high_c));
 assert.ok(lo>0&&lo<=lows&&hi>=highs,`${lo}~${hi}`);
 assert.ok(Number.isInteger(lo)&&Number.isInteger(hi));
 const ticks=integerTicks([lo,hi]);assert.ok(ticks.every(Number.isInteger));assert.equal(ticks[0],lo);
});
