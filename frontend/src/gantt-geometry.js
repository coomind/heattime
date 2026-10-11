// B-5: original matches store pure playing time (duration_min) plus halves/half_break_min,
// while proposals store the total occupied time; draw both as occupied minutes.
export function occupiedMinutes(m){
  if(m.halves!==undefined)return m.duration_min+(m.halves-1)*(m.half_break_min||0);
  return m.duration_min||40;
}

// B-1: times are stored with +09:00, so the first 10 characters are the KST date.
export function dayOf(time){return String(time).slice(0,10);}
export function tournamentDays(session){
  if(!session)return [];
  return [...new Set((session.risks||[]).map(r=>dayOf(r.valid_time)))].sort();
}
