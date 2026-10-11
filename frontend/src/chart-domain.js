// B-2: y-axis from the actual estimate range (the stacked base starts at 0, so dataMin cannot be used).
export function chartDomain(risks,policy){
  const values=risks.flatMap(r=>[r.wbgt_low_c,r.wbgt_high_c]).filter(Number.isFinite);
  const lines=policy?.boundaries||[policy?.cooling_above,policy?.postpone_above].filter(Number.isFinite);
  if(!values.length)return [0,40];
  const lo=Math.floor(Math.min(...values))-1,hi=Math.ceil(Math.max(...values))+1;
  const near=lines.filter(b=>b>=lo-3&&b<=hi+3);
  return [Math.min(lo,...near),Math.max(hi,...near)];
}
export function integerTicks([lo,hi]){const step=hi-lo>12?2:1;const ticks=[];for(let t=lo;t<=hi;t+=step)ticks.push(t);return ticks;}
