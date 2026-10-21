// Precomputed demo scenes. The hash is the address; '<hash>-team' opens that scene's read-only team view.
export const OBSERVED_SCENES=[
 {hash:'#snapshot-observed',key:'demo',title:'8월 10일: 재편성으로 전부 소화하는 날',file:'heattime-observed-0810'},
 {hash:'#snapshot-observed-0808',key:'extreme',title:'8월 8일: 재편성해도 연기가 생기는 날',file:'heattime-observed-0808'},
 {hash:'#snapshot-observed-0808-2day',key:'extreme-2day',title:'8월 8~9일: 같은 대회를 이틀 일정으로 다시 짠 경우',file:'heattime-observed-0808-0809'},
];
export const SYNTHETIC_SCENE={hash:'#snapshot',key:'synthetic',title:'합성 날씨(기능 시험용)',file:'heattime-synthetic'};
export const DEFAULT_HASH=OBSERVED_SCENES[0].hash;
const ALL=[...OBSERVED_SCENES,SYNTHETIC_SCENE];
// '#snapshot-observed-0808-team' -> {scene, team:true}; non-snapshot hashes -> null.
export function parseSceneHash(hash){
 if(!hash.startsWith('#snapshot'))return null;
 const team=hash.endsWith('-team');const base=team?hash.slice(0,-5):hash;
 const scene=ALL.find(s=>s.hash===base);
 return scene?{scene,team}:null;
}
