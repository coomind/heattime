import {defineConfig,devices} from '@playwright/test';
import path from 'node:path';
const root=path.resolve('..');
const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
export default defineConfig({
 testDir:'./e2e',timeout:90000,expect:{timeout:30000},workers:1,
 use:{baseURL:'http://127.0.0.1:8000',trace:'retain-on-failure'},
 projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
 webServer:{command:`"${python}" -m backend.run --host 127.0.0.1 --port 8000`,cwd:root,url:'http://127.0.0.1:8000/api/health',reuseExistingServer:true,timeout:30000}
});
