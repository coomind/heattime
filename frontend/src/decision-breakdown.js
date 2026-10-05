// Frozen rounded values only. This explanation cannot change settings or decisions.
export function breakdown(r) {
 const i=r.inputs,v=i.venue,s=i.settings;
 const field=v.field_offset_c,surface=s.surface_offsets[v.surface]||0,calibration=i.calibration?.[0]||0;
 const round=n=>Number(n.toFixed(3));
 const counter=round(r.wbgt_c-field-surface);
 const policyId=i.policy_id;
 return {model:round(r.wbgt_c-field-surface-calibration),field,surface,calibration,
  upper:round(r.decision_wbgt_c-r.wbgt_c),decision:r.decision_wbgt_c,counter,policyId};
}
export function counterLevel(value,policy,policyId) {
 return policyId==='football'?(value>policy.postpone_above?4:value>policy.cooling_above?2:0)
  :policy.boundaries.filter(b=>value>=b).length;
}
export function capturedRiskRows(projected,captured) {
 return projected.map(row=>captured.find(r=>r.venue_id===row.venue_id&&r.valid_time===row.valid_time))
  .filter(row=>row?.inputs);
}
