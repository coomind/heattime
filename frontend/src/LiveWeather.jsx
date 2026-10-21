import React,{useEffect,useRef,useState} from 'react';
const fmt=(value,digits=1)=>value===null||value===undefined?'결측':Number(value).toFixed(digits);
const time=value=>value?new Date(value).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',hour12:false}):'자료 없음';
const stages=['통상 운영','주의','경계','엄중경계','운동 중지'];
export default function LiveWeather({api,tournamentId,engine,snapshotMode,onValidation}){
 const [mode,setMode]=useState('mock'),[station,setStation]=useState('119'),[data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[seconds,setSeconds]=useState(0);
 const pending=useRef(0);
 const [referenceNotice,setReferenceNotice]=useState('');
 async function preserveReference(){setBusy(true);setReferenceNotice('');try{await api('/validation/live-reference',{token:data.reference_token});setReferenceNotice('추정값을 보관했습니다. 현장 측정 시각·위치와 일치하는지 검증 기록에서 확인하세요.');}catch{setReferenceNotice('추정 보관에 실패했습니다. 다른 최신 계산이 있으면 다시 갱신 후 보관하세요.');}finally{setBusy(false);}}
 useEffect(()=>{pending.current++;setData(null);setError('');setBusy(false);setMode('mock');},[tournamentId,snapshotMode]);
 useEffect(()=>{if(!busy)return;const timer=setInterval(()=>setSeconds(n=>n+1),1000);return()=>clearInterval(timer);},[busy]);
 async function update(){const token=++pending.current;setBusy(true);setSeconds(0);setError('');try{const result=await api('/live-observations',{mode,station_id:Number(station),tournament_id:tournamentId,engine_settings:engine});if(token===pending.current)setData(result);}catch{if(token===pending.current)setError('최신 관측 요청에 실패했습니다. 로컬 서버 연결을 확인하세요.');}finally{if(token===pending.current)setBusy(false);}}
 const obs=data?.observation,age=obs?Math.max(0,Math.floor((Date.now()-new Date(obs.valid_time).getTime())/60000)):null;
 return <section className="card live-weather" aria-label="최신 관측과 WBGT 추정"><h3>최신 관측과 WBGT 추정</h3>
 <p>기상청 관측 기온·습도·바람으로 현재 관측 시각의 WBGT를 추정합니다. 현장 WBGT 측정값이나 향후 경기 시각의 예보가 아닙니다. 재현 결과와 승인 일정은 바뀌지 않습니다.</p>
 <div className="form-row"><label>최신 관측 연결<select aria-label="최신 관측 연결" disabled={busy||snapshotMode} value={mode} onChange={e=>{pending.current++;setMode(e.target.value);setData(null);setError('');}}><option value="mock">합성 입력 · 연결 없는 점검</option><option value="api">기상청 API허브 · AWS 매분자료</option></select></label><label>관측 지점번호<input aria-label="관측 지점번호" type="number" min="1" max="9999" disabled={busy||snapshotMode} value={station} onChange={e=>{setStation(e.target.value);setData(null);}}/></label><button className="primary" disabled={busy||snapshotMode||!Number.isInteger(Number(station))||Number(station)<1||Number(station)>9999} onClick={update}>최신 관측 갱신</button></div>
 <p>기본 지점은 수원 119입니다. 다른 지점은 공식 지점표에서 확인 후 입력하세요. 자동 갱신 없이 버튼으로 조회하며, 앱 전체에서 60초 동안 호출을 재사용합니다.</p>
 {snapshotMode&&<p>시연 스냅샷에서는 최신 관측을 호출하지 않습니다. 일반 화면에서 연결하세요.</p>}
 {busy&&<p role="status">관측을 확인하고 있습니다 · {seconds}초 경과</p>}
 {error&&<div className="error" role="alert">{error}</div>}
 {data&&<><p role="status">{data.status==='mock'?'합성 입력 · 가상 예시':data.status==='ready'?'기상청 AWS 관측 자료':data.status==='cached'?'저장된 관측 재사용':data.status==='waiting'?'호출 간격 대기':'갱신 실패 · 이전 관측이 있으면 아래에 표시'}{data.retry_after_seconds>0&&' · '+data.retry_after_seconds+'초 후 다시 갱신 가능'}</p>
 {data.error&&<div className="error" role="alert">{data.error.stage} · {data.error.message}{data.error.http_status&&' · HTTP '+data.error.http_status}{data.error.exception_class&&' · '+data.error.exception_class}</div>}
 {data.status==='error'&&<p>연결 실패는 키 오류로 단정하지 않습니다. 이전 관측의 시각을 확인하세요. 시연은 <a href="#snapshot-observed">관측 시연 스냅샷으로 이동</a>하여 계속할 수 있습니다.</p>}
 {obs&&<><p>{obs.is_mock?'합성 입력':'기상청 관측 자료'}({obs.station_id===119?'수원 ':''}{obs.station_id}) · 관측 시각 {time(obs.valid_time)} KST · 가져온 시각 {time(obs.fetched_at)} KST · 화면 확인 기준 {age}분 전 관측</p>
 <p>관측 지연·결측이 있을 수 있습니다. 이전 자료를 현재 실측으로 해석하지 마세요. 같은 관측소 1곳의 입력을 아래 구장에 공유하며 공간 차이는 미측정입니다.</p>
 <div className="table-scroll" tabIndex={0}><table aria-label="최신 기상 입력"><thead><tr><th>기온 · ℃</th><th>습도 · %</th><th>WS10 · m/s</th><th>현지기압 · hPa</th><th>해면기압 · hPa</th><th>60분 강수 · mm</th></tr></thead><tbody><tr><td>{fmt(obs.ta_c)}</td><td>{fmt(obs.rh_pct)}</td><td>{fmt(obs.ws_ms)}</td><td>{fmt(obs.station_pressure_hpa)}</td><td>{fmt(obs.sea_level_pressure_hpa)}</td><td>{fmt(obs.rain_60m_mm)}</td></tr></tbody></table></div>
 <p>일사·운량은 이 응답에 없습니다. 기존 일사 추정(운량 0.7 가정)을 사용합니다. 기압 관측값은 참고 표시이며 계산에는 기존 스크리닝 기압을 유지합니다. WS10은 10분 평균이며 풍속 입력 높이는 기존 10m 가정입니다. 현장 수동값 보정은 이 최신 관측 계산에 적용하지 않습니다.</p>
 <div className="table-scroll" tabIndex={0}><table aria-label="최신 WBGT 추정"><thead><tr><th>구장</th><th>WBGT 추정 · 범위</th><th>판정값 · 단계</th><th>일사 추정 · 범위</th><th>구장 보정 · 계산 기압</th></tr></thead><tbody>{data.risks.map(r=><tr key={r.venue_id}><td>{r.venue_name}</td><td>{fmt(r.wbgt_c,3)}℃ · {fmt(r.wbgt_low_c,3)}~{fmt(r.wbgt_high_c,3)}℃</td><td>{fmt(r.decision_wbgt_c,3)}℃ · {stages[r.level]}</td><td>{fmt(r.inputs.solar.used_wm2)} W/m² · {fmt(r.inputs.solar.low_wm2)}~{fmt(r.inputs.solar.high_wm2)} W/m²</td><td>{fmt(r.inputs.venue.field_offset_c)}℃ · {fmt(r.inputs.settings.pressure_hpa,2)}hPa</td></tr>)}</tbody></table></div>
 <p>{data.tournament_name} · {data.age_group} · 현재 선택 설정. 범위는 검증된 신뢰구간이 아니며 최종 판단은 운영자가 합니다.</p>
 {data.reference_token&&<div className="buttons"><button disabled={busy||snapshotMode} onClick={preserveReference}>현장 대조용 추정 보관</button><button disabled={busy||snapshotMode} onClick={onValidation}>검증 기록 열기</button></div>}{referenceNotice&&<p role="status">{referenceNotice}</p>}
 <details><summary>최신 계산의 근거·가정</summary>{data.risks.map(r=><div key={r.venue_id}><p>{r.venue_name} · {r.method_version} · 높이 보정 후 풍속 {fmt(r.inputs.wind_2m_ms,3)}m/s</p><p>{r.inputs.assumptions.join(' / ')}</p><code className="evidence-hash">{r.inputs_hash}</code></div>)}</details></>}
 <p>이 앱 사용량: {data.usage.calls}회 / {data.usage.daily_call_limit.toLocaleString()}회 · {data.usage.bytes.toLocaleString()}바이트 / {data.usage.daily_byte_limit.toLocaleString()}바이트. {data.usage.scope}</p>
 </>}
 </section>;
}
