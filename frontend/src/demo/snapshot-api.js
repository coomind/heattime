import bundle from './snapshot.json';
import evidenceURL from './snapshot-evidence.json?url';
import inputURL from './snapshot-input-evidence.json?url';
import reviewURL from './snapshot-plan-review.json?url';
import exportsBundle from './snapshot-exports.json';
import {createBundleAPI} from './snapshot-core.js';
export async function createSnapshotAPI(){
 const [response,input,review]=await Promise.all([fetch(evidenceURL),fetch(inputURL),fetch(reviewURL)]);if(!response.ok||!input.ok||!review.ok)throw new Error('스냅샷 상세 근거를 불러오지 못했습니다.');
 return createBundleAPI(bundle,exportsBundle,await response.json(),await input.json(),await review.json());
}
