import {defineConfig,devices} from '@playwright/test';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
const root=path.resolve('..');
const port=8127;
const database=path.join(root,'data','output','e2e',randomUUID()+'.sqlite3');
const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
export default defineConfig({
 testDir:'./e2e',timeout:90000,expect:{timeout:30000},workers:1,
 use:{baseURL:`http://127.0.0.1:${port}`,trace:'retain-on-failure'},
 projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
 webServer:{command:`"${python}" -m backend.run --host 127.0.0.1 --port ${port} --db "${database}"`,cwd:root,url:`http://127.0.0.1:${port}/api/health`,reuseExistingServer:false,timeout:30000}
});
