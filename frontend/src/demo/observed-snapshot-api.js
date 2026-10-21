import {createBundleAPI} from './snapshot-core.js';
// One entry per observed scene (scenes.js). Large files are fetched/loaded only for the opened scene.
const FILES={
 demo:{bundle:()=>import('./observed-snapshot.json?url'),evidence:()=>import('./observed-snapshot-evidence.json?url'),
  input:()=>import('./observed-snapshot-input-evidence.json?url'),review:()=>import('./observed-snapshot-plan-review.json?url'),
  exports:()=>import('./observed-snapshot-exports.json')},
 extreme:{bundle:()=>import('./observed-snapshot-0808.json?url'),evidence:()=>import('./observed-snapshot-0808-evidence.json?url'),
  input:()=>import('./observed-snapshot-0808-input-evidence.json?url'),review:()=>import('./observed-snapshot-0808-plan-review.json?url'),
  exports:()=>import('./observed-snapshot-0808-exports.json')},
 'extreme-2day':{bundle:()=>import('./observed-snapshot-0808-2day.json?url'),evidence:()=>import('./observed-snapshot-0808-2day-evidence.json?url'),
  input:()=>import('./observed-snapshot-0808-2day-input-evidence.json?url'),review:()=>import('./observed-snapshot-0808-2day-plan-review.json?url'),
  exports:()=>import('./observed-snapshot-0808-2day-exports.json')},
};
export async function createSnapshotAPI(key='demo'){
 const f=FILES[key];if(!f)throw new Error('알 수 없는 시연 장면입니다.');
 const urls=await Promise.all([f.bundle(),f.evidence(),f.input(),f.review()]);
 const responses=await Promise.all(urls.map(u=>fetch(u.default)));
 if(responses.some(r=>!r.ok))throw new Error('관측 스냅샷 자료를 불러오지 못했습니다.');
 const [bundle,evidence,input,review]=await Promise.all(responses.map(r=>r.json()));
 const exportsBundle=(await f.exports()).default;
 return createBundleAPI(bundle,exportsBundle,evidence,input,review);
}
