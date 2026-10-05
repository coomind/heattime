import React,{useEffect,useRef,useState} from 'react';
const labels={insert:'신규 경기',update:'기존 경기 수정',unchanged:'기존 경기 동일'};
export default function CsvImport({api,tournamentId,disabled,readonly,run,onSaved}){
 const [text,setText]=useState(null),[preview,setPreview]=useState(null),[fileName,setFileName]=useState(''),[generation,setGeneration]=useState(0);
 const request=useRef(0);
 useEffect(()=>{request.current++;setText(null);setPreview(null);setFileName('');setGeneration(g=>g+1);},[tournamentId,readonly]);
 async function readFile(file){if(!file)return;const token=++request.current,content=await file.text();if(token!==request.current)return;setPreview(null);setText(content);setFileName(file.name);await run(async()=>{const checked=await api('/tournaments/'+encodeURIComponent(tournamentId)+'/matches/csv-preview',{csv_text:content});if(token===request.current)setPreview(checked);});}
 async function save(){await run(async()=>{await api('/tournaments/'+encodeURIComponent(tournamentId)+'/matches/csv',{csv_text:text,expected_revision:preview.revision});setPreview(null);setText(null);setFileName('');setGeneration(g=>g+1);await onSaved();});}
 return <section className="csv-import" aria-label="CSV 저장 전 미리보기"><h3>CSV 저장 전 미리보기</h3>
  <p>선택 대회: {tournamentId} · 파일 선택만으로 저장하지 않습니다. 오류를 확인한 뒤 저장하세요.</p>
  {!disabled&&<a className="button" href={'/api/tournaments/'+encodeURIComponent(tournamentId)+'/matches/csv-template'} download>CSV 양식 내려받기</a>}
  <p>양식은 선택 대회의 기존 경기 1행을 포함합니다. 그대로 올리면 동일 경기 확인, ID를 바꾸면 신규 경기입니다. 선행 경기 ID는 세미콜론, 시각은 +09:00으로 표시합니다.</p>
  <label className="file-label">CSV 파일 선택<input key={generation} disabled={disabled} type="file" accept=".csv,text/csv" onChange={e=>readFile(e.target.files[0])}/></label>
  {readonly&&<p>스냅샷은 고정된 자료입니다. 일반 재현에서 CSV를 확인·저장하세요.</p>}
  {preview&&<><p>{fileName} · {preview.tournament_name} · 신규 {preview.summary.insert} / 수정 {preview.summary.update} / 동일 {preview.summary.unchanged}경기</p>
   {!preview.valid&&<div className="error" role="alert">저장 불가{preview.errors.map((e,i)=><p key={i}>{e.line?'행 '+e.line+' · ':''}{e.message}</p>)}</div>}
   <div className="table-scroll"><table aria-label="CSV 저장 예정 경기"><thead><tr><th>행 / 변경</th><th>경기·팀</th><th>구장·KST 일정</th><th>선행 경기 / 변경 필드</th></tr></thead><tbody>{preview.rows.map((row,i)=><tr key={i}><td>{row.line} · {labels[row.operation]}</td><td>{row.match.id} · {row.match.round}<br/>{row.team_a_name} / {row.team_b_name}</td><td>{row.venue_name}<br/>{row.match.scheduled_start} · 경기시간 {row.match.duration_min}분</td><td>{row.match.depends_on.join(', ')||'없음'}<br/>{row.changed_fields.join(', ')||'변경 없음'}</td></tr>)}</tbody></table></div>
   <div className="buttons"><button className="primary" disabled={disabled||!preview.valid} onClick={save}>확인한 CSV 저장</button><button disabled={disabled} onClick={()=>{setPreview(null);setText(null);setFileName('');setGeneration(g=>g+1);}}>CSV 확인 취소</button><button disabled={disabled} onClick={()=>run(async()=>setPreview(await api('/tournaments/'+encodeURIComponent(tournamentId)+'/matches/csv-preview',{csv_text:text})))}>CSV 다시 확인</button></div>
   <p>저장 시 같은 검사를 다시 실행합니다. 확인 후 등록 자료가 바뀌면 저장을 중단하고 다시 확인해야 합니다.</p>
  </>}
 </section>;
}
