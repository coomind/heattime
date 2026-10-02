const clone=value=>structuredClone(value);
export function createBundleAPI(bundle,exportsBundle){
 if(bundle.input_fingerprint!==exportsBundle.input_fingerprint)throw new Error('스냅샷과 기록 파일 버전이 다릅니다.');
 let session=null,urls={};
 const accepted=bundle.approved;
 const resources={venues:accepted.venues,tournaments:[accepted.tournament],teams:accepted.teams,matches:accepted.matches};
 function dispose(){Object.values(urls).forEach(u=>URL.revokeObjectURL(u));urls={};}
 function exportHref(format){
  if(!session?.decision) return '#';
  if(!urls[format]){
   let blob;
   if(format==='pdf')blob=new Blob([Uint8Array.from(atob(exportsBundle.pdf_base64),c=>c.charCodeAt(0))],{type:'application/pdf'});
   else if(format==='csv')blob=new Blob(['\ufeff'+exportsBundle.csv_utf8],{type:'text/csv;charset=utf-8'});
   else blob=new Blob([JSON.stringify(session,null,2)],{type:'application/json'});
   urls[format]=URL.createObjectURL(blob);
  }
  return urls[format];
 }
 async function api(path,body,method='POST'){
  if(body===undefined&&resources[path.slice(1)])return clone(resources[path.slice(1)]);
  if(path==='/snapshot-info')return {label:bundle.label,reason:accepted.decision.reason,date:accepted.tournament.date_start,data_origin:accepted.data_origin||'synthetic'};
  if(path==='/replays'){
   if(body?.date!==accepted.tournament.date_start||body?.tournament_id!==accepted.tournament.id)throw new Error('스냅샷의 날짜·대회는 사전 계산된 예시로 고정됩니다.');
   for(const [name,values] of [['engine_settings',accepted.engine_settings],['schedule_settings',accepted.schedule_settings]]){
    if(Object.entries(body?.[name]||{}).some(([k,v])=>JSON.stringify(v)!==JSON.stringify(values[k])))throw new Error('스냅샷에서는 사전 계산된 운영 설정을 사용합니다.');
   }
   dispose();session=clone(accepted);session.proposal=null;session.decision=null;session.notifications=[];
   return clone(session);
  }
  if(path==='/team-view/'+accepted.id)return clone(session?.decision?session:accepted);
  if(!session)throw new Error('시연 스냅샷을 먼저 실행하세요.');
  const prefix='/sessions/'+session.id;
  if(path===prefix+'/optimize'){
   if(session.decision)throw new Error('스냅샷 재현을 새로 실행하세요.');
   session.proposal=clone(accepted.proposal);return clone(session.proposal);
  }
  if(path===prefix+'/decision'){
   if(session.decision||!session.proposal)throw new Error('스냅샷의 제안·승인 순서를 확인하세요.');
   if(body.action!=='accepted'||body.reason!==accepted.decision.reason)throw new Error('스냅샷은 사전 계산된 승인만 시연합니다.');
   session.decision=clone(accepted.decision);session.notifications=clone(accepted.notifications);return clone(session);
  }
  const matchId=path.startsWith(prefix+'/matches/')?path.slice((prefix+'/matches/').length):null;
  if(matchId){
   const match=session.matches.find(m=>m.id===matchId);if(!match)throw new Error('경기를 찾지 못했습니다.');
   return clone({match,risks:session.risks.filter(r=>r.venue_id===match.venue_id),recommendation:session.recommendations.find(r=>r.match_id===matchId),policy:session.policy});
  }
  if(path==='/team-view/'+session.id)return clone(session);
  if(path===prefix)return clone(session);
  throw new Error('스냅샷에서는 등록·수정·실측 입력을 저장하지 않습니다. 일반 재현 모드를 사용하세요.');
 }
 return {api,exportHref,dispose,sessionId:accepted.id};
}
