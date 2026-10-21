import {defineConfig,devices} from '@playwright/test';
// Static judge demo (dist-demo) served under a sub-path with no backend; every non-local request is blocked in the specs.
const port=8128;
export default defineConfig({
 testDir:'./e2e-demo',timeout:90000,expect:{timeout:30000},workers:1,
 use:{baseURL:`http://127.0.0.1:${port}/heattime/`,trace:'retain-on-failure',acceptDownloads:true},
 projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
 webServer:{command:`node scripts/serve-static.mjs dist-demo ${port} /heattime/`,url:`http://127.0.0.1:${port}/heattime/`,reuseExistingServer:false,timeout:30000}
});
