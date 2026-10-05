import bundle from './snapshot.json';
import evidenceURL from './snapshot-evidence.json?url';
import exportsBundle from './snapshot-exports.json';
import {createBundleAPI} from './snapshot-core.js';
export async function createSnapshotAPI(){
 const response=await fetch(evidenceURL);if(!response.ok)throw new Error('스냅샷 상세 근거를 불러오지 못했습니다.');
 return createBundleAPI(bundle,exportsBundle,await response.json());
}
