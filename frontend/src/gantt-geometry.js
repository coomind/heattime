// B-5: original matches store pure playing time (duration_min) plus halves/half_break_min,
// while proposals store the total occupied time; draw both as occupied minutes.
export function occupiedMinutes(m){
  if(m.halves!==undefined)return m.duration_min+(m.halves-1)*(m.half_break_min||0);
  return m.duration_min||40;
}
