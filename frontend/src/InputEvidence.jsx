import React from 'react';
const n=v=>v===null||v===undefined?'자료 없음':Number(v).toFixed(3);
const t=v=>v?new Date(v).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}):'자료 없음';
export default function InputEvidence({data:e,onClose}){
 const r=e.risk,w=e.weather,a=e.audit;
 return <section className="card input-evidence" aria-label="입력 근거와 현장 보정 이력"><div className="section-head"><h2>입력 근거와 현장 보정 이력</h2><button className="chip" onClick={onClose}>근거 닫기</button></div>
  <p>{e.venue_name} · {t(r.valid_time)} KST · {e.view==='approved'?'승인 시점 고정 근거':'재현 시점 고정 근거'}</p>
  <p className="evidence-assumptions">{e.label} · {w.is_mock?'합성 기상 · 가상 예시':'관측 기상 입력 · 현장 WBGT 실측 아님'}</p>
  <p>WBGT 추정 {n(r.wbgt_c)}℃ · 범위 {n(r.wbgt_low_c)}~{n(r.wbgt_high_c)}℃ · 판정값 {n(r.decision_wbgt_c)}℃ / 단계 {r.level}<br/>이 범위는 현장 검증된 신뢰구간이 아닙니다. 현재 시각의 실황과 과거 재현을 구분하세요.</p>
  <div className="table-scroll" tabIndex={0}><table aria-label="계산 입력과 단위"><tbody>
   <tr><th>자료 시각 / 가져온 시각</th><td>{t(w.valid_time)} / {t(w.fetched_at)} · 지점 {w.station_id||'없음'}</td></tr>
   <tr><th>기온 / 습도 / 원풍속</th><td>{n(w.ta_c)}℃ / {n(w.rh_pct)}% / {n(w.ws_ms)}m/s</td></tr>
   <tr><th>풍속 높이 보정</th><td>10m 입력 가정 → 2m · 지수 {e.wind_exponent} · {n(e.wind_2m_ms)}m/s · {r.inputs.fallback_reason?'간이 폴백 일사 항 최소 처리 후 '+n(e.fallback_wind_ms):'Liljegren 입력 최소 처리 후 '+n(e.engine_wind_ms)}m/s</td></tr>
   <tr><th>기압 입력</th><td>{n(e.pressure_hpa)}hPa · 기존 해수면 스크리닝 가정</td></tr>
   <tr><th>사용 일사</th><td>{e.solar_observed?'관측 일사 사용':'일사 결측/미제공 · 모델 추정 사용'} · {n(e.solar.used_wm2)}W/m² · {e.solar.source}</td></tr>
   {e.solar_energy_mj_m2!==null&&<tr><th>관측 일사 원값과 변환</th><td>{n(e.solar_energy_mj_m2)}MJ/m² × 1,000,000 / 3,600 → {n(w.solar_wm2)}W/m²<br/>위험 구간과 같은 1시간 {t(e.solar_interval_start)}~{t(e.solar_interval_end)} (구간 끝 정시 관측)</td></tr>}
   <tr><th>일사 모델 추정</th><td>{n(e.solar.estimated_wm2)}W/m² · 범위 {n(e.solar.low_wm2)}~{n(e.solar.high_wm2)}W/m² · 엔진 복사 입력 {n(e.engine_solar_wm2)}W/m²</td></tr>
   <tr><th>구장 / 표면 보정</th><td>{n(e.field_offset_c)}℃ / {n(e.surface_offset_c)}℃<br/><small className="surface-note">표면 유형(인조잔디·천연잔디·흙·실내)은 현재 WBGT 판정에 반영되지 않습니다. 표면 보정값은 0℃이며, 전문가 검토 전에는 새 보정값을 만들지 않습니다.</small></td></tr>
   <tr><th>계산 방법</th><td>{r.method_version}<br/>{r.inputs.fallback_reason?'폴백 사유: '+r.inputs.fallback_reason:'폴백 사유 없음'}</td></tr>
   {e.solar_missing_hours!==null&&<tr><th>재현 기간 일사 결측</th><td>{e.solar_missing_hours}시간 · 동일 관측소 기준, 구장 수 중복 집계 없음</td></tr>}
  </tbody></table></div>
  <h3>현장 보정 적용 이력</h3><p>{a.calibration?'현재 결과의 보정 잔차 '+n(a.calibration[0])+'℃ / 기록된 잔차 크기 '+n(a.calibration[1])+'℃':'해당 시각 결과에 현장 보정 없음'}</p>
  {!a.history_known?<p>이 세션에는 수동 입력 이력이 보존되지 않았습니다. 측정 여부를 단정하지 않습니다.</p>:!a.rows.length?<p>이 재현 시점에 보존된 해당 구장 입력 이력 없음</p>:<div className="table-scroll" tabIndex={0}><table aria-label="현장 보정 적용 이력"><thead><tr><th>자료 구분</th><th>측정 시각 / 값</th><th>적용 여부와 이유</th></tr></thead><tbody>{a.rows.map(row=><tr key={row.id}><td>{row.is_mock?'가상 예시 · 모의 입력':'현장 실측 입력'}</td><td>{t(row.valid_time)} / {n(row.wbgt_c)}℃</td><td>{row.status}<br/>참고 자료 {t(row.reference_time)}</td></tr>)}</tbody></table></div>}
  <details><summary>입력 가정과 근거 지문</summary><p>{r.inputs.assumptions.join(' / ')}</p><p className="fingerprint">{r.inputs_hash}</p></details>
  <p>현장 대조·국내 구장 보정·전문가 검토는 별도 검증이 필요합니다. 최종 운영 판단은 운영자가 합니다.</p>
 </section>;
}
