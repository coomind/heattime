// E-7: operator-facing names instead of internal ids/enums (ids kept where traceability matters).
export const OPERATOR_ACTIONS={accepted:'제안 승인',modified:'수정안 승인',rejected:'제안 거절'};
export function kstText(value){if(!value)return '—';const t=String(value);return t.slice(0,10)+' '+t.slice(11,16)+' KST';}
export function teamLabel(session,id){if(id.startsWith('winner:'))return id.slice(7)+' 승자';return session.teams?.find(t=>t.id===id)?.name||id;}
export function venueLabel(session,id){return session.venues?.find(v=>v.id===id)?.name||id;}
export function matchLabel(session,id){const m=session.matches?.find(x=>x.id===id);return m?`${m.round} · ${id} · ${teamLabel(session,m.team_a)} vs ${teamLabel(session,m.team_b)}`:id;}
