import bundleURL from './observed-snapshot.json?url';
import exportsBundle from './observed-snapshot-exports.json';
import {createBundleAPI} from './snapshot-core.js';
export async function createSnapshotAPI(){
 const response=await fetch(bundleURL);
 if(!response.ok)throw new Error('관측 스냅샷 자료를 불러오지 못했습니다.');
 return createBundleAPI(await response.json(),exportsBundle);
}
