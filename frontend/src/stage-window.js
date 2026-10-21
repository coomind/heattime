// Mirrors backend/schedule/recommend.py: a match's stage is the highest hourly stage inside the window
// [kickoff, kickoff + length], where length is the pre-shortening play+half-break (plus cooling breaks at stage 2).
const toMin=t=>new Date(t).getTime()/60000;
export function stageWindow(match,risks,venueId,start,coolingMin){
  const base=match.duration_min+(match.halves-1)*match.half_break_min;
  const hourly=new Map(risks.filter(r=>r.venue_id===venueId).map(r=>[toMin(r.valid_time),r]));
  const s=toMin(start);let duration=base,level=0,samples=[];
  for(let i=0;i<3;i++){
    const end=s+duration;samples=[];
    for(let h=Math.floor(s/60)*60;h<=end;h+=60){const r=hourly.get(h);if(!r)return {missing:true,base,duration};samples.push(r);}
    level=Math.max(level,...samples.map(r=>r.level));
    const next=level===2?base+coolingMin*match.halves:base;
    if(level>=3||next===duration)break;
    duration=next;
  }
  return {level,base,duration,startMin:s,endMin:s+duration,hours:samples.map(r=>({time:r.valid_time,level:r.level,decision:r.decision_wbgt_c}))};
}
