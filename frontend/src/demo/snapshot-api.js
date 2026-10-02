import bundle from './snapshot.json';
import exportsBundle from './snapshot-exports.json';
import {createBundleAPI} from './snapshot-core.js';
export function createSnapshotAPI(){return createBundleAPI(bundle,exportsBundle);}
