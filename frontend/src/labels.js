// E-7: operator-facing names instead of internal ids/enums (ids kept where traceability matters).
export const OPERATOR_ACTIONS={accepted:'제안 승인',modified:'수정안 승인',rejected:'제안 거절'};
export function kstText(value){if(!value)return '—';const t=String(value);return t.slice(0,10)+' '+t.slice(11,16)+' KST';}
// f: internal match ids and winner placeholders -> names people use (same rules as backend/display_names.py).
export function matchName(id){
  let m=/^g(\d+)-(\d+)$/.exec(id);if(m)return `${m[1]}조 ${m[2]}경기`;
  m=/^semi(\d+)$/.exec(id);if(m)return `준결승 ${m[1]}`;
  if(id==='final')return '결승';
  return id;
}
// Short marker label for narrow timeline bars; the full name stays in aria-label/title.
export function matchShort(id){
  let m=/^g(\d+)-(\d+)$/.exec(id);if(m)return `${m[1]}조 ${m[2]}`;
  m=/^semi(\d+)$/.exec(id);if(m)return `준결 ${m[1]}`;
  return id==='final'?'결승':id;
}
export function placeholderName(id){
  const ref=id.slice(7);const g=/^group(\d+)$/.exec(ref);
  if(g)return `${g[1]}조 1위`;
  return `${matchName(ref)} 승자`;
}
export function teamLabel(session,id){if(id.startsWith('winner:'))return placeholderName(id);return session.teams?.find(t=>t.id===id)?.name||id;}
export function venueLabel(session,id){return session.venues?.find(v=>v.id===id)?.name||id;}
export function matchLabel(session,id){const m=session.matches?.find(x=>x.id===id);return m?`${m.round} · ${matchName(id)} · ${teamLabel(session,m.team_a)} vs ${teamLabel(session,m.team_b)}`:matchName(id);}
// W-3: same wording as backend/exports.verification_text.
export function verificationText(raw){const head='원문 대조 필요 · ';return raw?.startsWith(head)?`원문 대조: ${raw.slice(head.length)} · 원문 개정 시 다시 대조 필요 · 국내 대회 적용 전 전문가 검토 필요`:raw;}
