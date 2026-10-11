import {round1} from './format.js';
// Mirror of backend/config/policies.yaml age.upper_bound_groups (checked by tests/test_frontend_policy_mirror.py).
export const UPPER_BOUND_GROUPS=['U10','U12','U15','senior'];
// Frozen rounded values only. This explanation cannot change settings or decisions.
export function breakdown(r) {
 const i=r.inputs,v=i.venue,s=i.settings;
 const field=v.field_offset_c,surface=s.surface_offsets[v.surface]||0,calibration=i.calibration?.[0]||0;
 const round=n=>Number(n.toFixed(3));
 const counter=round(r.wbgt_c-field-surface);
 const policyId=i.policy_id;
 const upper=UPPER_BOUND_GROUPS.includes(i.age_group)?round(r.wbgt_high_c-r.wbgt_c):0;
 return {model:round(r.wbgt_c-field-surface-calibration),field,surface,calibration,
  upper,unrounded:round(r.wbgt_c+upper),decision:r.decision_wbgt_c,counter,
  counterDecision:Number(round1(counter)),policyId};
}
// Stage of the displayed 0.1℃ value (same rule as backend round_decision + classify).
export function counterLevel(value,policy,policyId) {
 const shown=Number(round1(value));
 return policyId==='football'?(shown>policy.postpone_above?4:shown>policy.cooling_above?2:0)
  :policy.boundaries.filter(b=>shown>=b).length;
}
export function capturedRiskRows(projected,captured) {
 return projected.map(row=>captured.find(r=>r.venue_id===row.venue_id&&r.valid_time===row.valid_time))
  .filter(row=>row?.inputs);
}
