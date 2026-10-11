// Same rule as backend/engine/policy.round_decision: 6-place cleanup, then 0.1 half-up.
export function round1(value){
  const x=Math.round(Number(value)*1e6)/1e6
  const r=Math.sign(x)*Math.round(Math.abs(x)*10+1e-9)/10
  return (Object.is(r,-0)?0:r).toFixed(1)
}
