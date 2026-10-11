const clone=value=>structuredClone(value);
// Same note as backend/exports.stage_display (W-1).
export function stageDisplay(policy){const labels=policy?.labels||[];return {labels_display:labels.map(l=>l==='거의 안전'?'통상 운영':l),note:'policy.labels는 원 지침 단계명(출처: policy.source_ref)입니다. 화면·PDF·CSV는 labels_display를 쓰며, 0단계 "거의 안전"은 안전을 판정·보장하지 않도록 "통상 운영"으로 표시합니다(명세 2.5(D) 2026-10-11 변경).'};}
export function createBundleAPI(bundle,exportsBundle,evidenceBundle=null,inputBundle=null,reviewBundle=null){
 if(bundle.input_fingerprint!==exportsBundle.input_fingerprint)throw new Error('스냅샷과 기록 파일 버전이 다릅니다.');
 if(evidenceBundle&&(bundle.input_fingerprint!==evidenceBundle.input_fingerprint||bundle.approved.id!==evidenceBundle.session_id))throw new Error('스냅샷과 상세 근거 버전이 다릅니다.');
 if(inputBundle&&(bundle.input_fingerprint!==inputBundle.input_fingerprint||bundle.approved.id!==inputBundle.session_id))throw new Error('스냅샷과 입력 근거 버전이 다릅니다.');
 if(reviewBundle&&(bundle.input_fingerprint!==reviewBundle.input_fingerprint||bundle.approved.id!==reviewBundle.session_id))throw new Error('스냅샷과 조건 검토 버전이 다릅니다.');
 let session=null,urls={};
 const accepted=bundle.approved;
 const resources={venues:accepted.venues,tournaments:[accepted.tournament],teams:accepted.teams,matches:accepted.matches};
 function dispose(){Object.values(urls).forEach(u=>URL.revokeObjectURL(u));urls={};}
 function exportHref(format){
  // B-4: pre-built PDF/CSV exist only for the approved snapshot; JSON is the current state.
  if(!session)return null;
  if(!session.decision&&format!=='json')return null;
  if(format==='json'){if(urls.json)URL.revokeObjectURL(urls.json);delete urls.json;}
  if(!urls[format]){
   let blob;
   if(format==='pdf')blob=new Blob([Uint8Array.from(atob(exportsBundle.pdf_base64),c=>c.charCodeAt(0))],{type:'application/pdf'});
   else if(format==='csv')blob=new Blob(['\ufeff'+exportsBundle.csv_utf8],{type:'text/csv;charset=utf-8'});
   else blob=new Blob([JSON.stringify({...session,stage_display:stageDisplay(session.policy)},null,2)],{type:'application/json'});
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
  if(path.startsWith(prefix+'/plan-review')){
   const view=new URLSearchParams(path.split('?')[1]||'').get('view')||'proposed';
   if(!['proposed','approved'].includes(view))throw new Error('알 수 없는 일정 보기입니다.');
   if(view==='approved'&&!session.decision)throw new Error('아직 승인한 일정이 없습니다.');
   if(view==='proposed'&&!session.proposal)throw new Error('자동 제안을 먼저 생성하세요.');
   if(!reviewBundle)throw new Error('조건 검토 자료가 없습니다.');
   return clone(reviewBundle[view]);
  }
  if(path.startsWith(prefix+'/input-evidence?')){
   const params=new URLSearchParams(path.split('?')[1]);const view=params.get('view')||'original';
   if(!['original','proposed','approved'].includes(view))throw new Error('알 수 없는 근거 보기입니다.');
   if(view==='approved'&&!session.decision)throw new Error('아직 승인한 일정이 없습니다.');
   const item=inputBundle?.inputs[params.get('venue_id')+'|'+params.get('valid_time')];
   if(!item)throw new Error('입력 근거를 찾지 못했습니다.');
   return {...clone(item),view};
  }
  if(path===prefix+'/optimize'){
   if(session.decision)throw new Error('스냅샷 재현을 새로 실행하세요.');
   session.proposal=clone(accepted.proposal);return clone(session.proposal);
  }
  if(path===prefix+'/decision'){
   if(session.decision||!session.proposal)throw new Error('스냅샷의 제안·승인 순서를 확인하세요.');
   if(body.action!=='accepted'||body.reason!==accepted.decision.reason)throw new Error('스냅샷은 사전 계산된 승인만 시연합니다.');
   session.decision=clone(accepted.decision);session.notifications=clone(accepted.notifications);return clone(session);
  }
  if(path.startsWith(prefix+'/matches/')&&path.includes('/evidence')){
   const matchId=decodeURIComponent(path.slice((prefix+'/matches/').length).split('/')[0]);
   const view=new URLSearchParams(path.split('?')[1]||'').get('view')||'proposed';
   if(!['proposed','approved'].includes(view))throw new Error('알 수 없는 일정 보기입니다.');
   if(view==='approved'&&!session.decision)throw new Error('아직 승인한 일정이 없습니다.');
   if(view==='proposed'&&!session.proposal)throw new Error('자동 제안을 먼저 생성하세요.');
   const item=evidenceBundle?.matches[matchId];if(!item)throw new Error('경기 상세 근거를 찾지 못했습니다.');
   return {...clone(item),view,state:view==='approved'?'approved':session.decision?'accepted_proposal':'unapproved'};
  }
  const matchId=path.startsWith(prefix+'/matches/')?decodeURIComponent(path.slice((prefix+'/matches/').length)):null;
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
