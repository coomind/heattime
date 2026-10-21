import React from 'react';
// Background facts with sources, embedded as text so they show offline. Wording follows each article
// (checked 2026-10-21); these are context for the problem, not evidence of HeatTime's effect.
export const SOURCES=[
 {topic:'국내 대회 사례',text:'7월 30일 충주에서 시작한 제25회 전국여자축구선수권대회에서 30℃가 넘는 날씨에 경기 직후 중학생 선수가 탈수 증세로 병원에 이송됐습니다(치료 후 복귀). 대회에서 온열질환자 3명이 나왔고, 이후 경기 시작 시각을 1시간씩 늦췄습니다.',source:'YTN',date:'2026.08.07',url:'https://www.ytn.co.kr/_ln/0103_202608071805566486'},
 {topic:'국내 온열질환 통계',text:'2025년 온열질환자는 4,460명(추정 사망 29명)으로, 응급실 감시체계를 운영한 이후 두 번째로 많았습니다.',source:'뉴시스',date:'2026.05.14',url:'https://www.newsis.com/view/NISX20260514_0003629135'},
 {topic:'국내 프로 경기 사례',text:'8월 4일 인천 SSG랜더스필드에서 관중 2명이 쓰러지는 등 25명이 온열질환 의심 증상으로 응급조치를 받았습니다. 이후 KBO는 예정된 5경기를 취소했고, 한국프로축구연맹은 K리그 킥오프를 19:30에서 20:00으로 30분 늦췄습니다.',source:'머니투데이',date:'2026.08.05',url:'https://www.mt.co.kr/sports/2026/08/05/2026080516090110265'},
 {topic:'해외 축구 기준',text:'기사에 소개된 기준입니다. FIFPRO는 WBGT 26℃를 넘으면 쿨링브레이크를 필수로, 28℃를 넘으면 경기 중단을 제시합니다. 호주는 WBGT 28℃ 이상이면 경기 연기나 일정 변경을 권고하고, WBGT 26~27.9℃ 또는 기온 31℃ 이상이면 하프마다 90초 휴식을 둡니다. 일본축구협회는 2024년 5월 21일 개정으로 전·후반 각각 3분 휴식을 의무화하고 WBGT를 실시간으로 측정합니다.',source:'데일리안',date:'2025.07.31',url:'https://www.dailian.co.kr/news/view/1530184/'},
 {topic:'미국 학교 스포츠',text:'Korey Stringer Institute의 Rebecca Stearns는 WBGT로 훈련 조정을 의무화한 주에서 열 관련 질환이 80% 줄었다는 연구 결과를 전했습니다. 기사가 독자적으로 검증한 수치가 아니라 연구자의 발언입니다.',source:'KFF Health News',date:'2022.09.30',url:'https://kffhealthnews.org/republish/news/school-sports-programs-states-northern-heat-safety-score/'},
];
export default function BackgroundEvidence(){
 return <details className="card background-evidence"><summary>폭염 속 경기 운영 사례와 기준 (출처 기사)</summary>
  <p>문제의 배경을 보여 주는 보도 내용입니다. 히트타임의 효과를 보여 주는 자료가 아니며, 링크는 새 탭에서 열립니다.</p>
  <ul>{SOURCES.map(s=><li key={s.url}><b>{s.topic}</b><span>{s.text}</span><a href={s.url} target="_blank" rel="noopener noreferrer">{s.source} {s.date} 기사 열기<span className="sr-only"> (새 탭)</span></a></li>)}</ul>
 </details>;
}
