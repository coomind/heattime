import {test,expect} from '@playwright/test';
import {createServer} from 'node:http';
import {readFileSync,readdirSync} from 'node:fs';
import path from 'node:path';

test('new build replaces cached snapshot before offline reload',async({page,context})=>{
 const files=new Map();const root=path.resolve('dist');
 function collect(directory){
  for(const item of readdirSync(directory,{withFileTypes:true})){
   const full=path.join(directory,item.name);
   if(item.isDirectory())collect(full);
   else files.set('/'+path.relative(root,full).replaceAll('\\','/'),readFileSync(full));
  }
 }
 collect(root);
 const builtWorker=files.get('/sw.js').toString();
 expect(builtWorker).toMatch(/const BUILD_VERSION='[a-f0-9]{64}'/);
 expect(builtWorker).not.toContain('__HEATTIME_BUILD_ID__');
 let version='upgrade-A';
 const server=createServer((request,response)=>{
  const pathname=new URL(request.url,'http://localhost').pathname;
  const name=pathname==='/'?'/index.html':pathname;
  let body=files.get(name);
  if(!body){response.writeHead(404);response.end();return;}
  if(name==='/index.html')body=Buffer.from(body.toString().replace(/<title>[^<]*<\/title>/,`<title>${version}</title>`));
  if(name==='/sw.js')body=Buffer.from(body.toString().replace(/const BUILD_VERSION='[^']*'/,`const BUILD_VERSION='${version}'`));
  const type=name.endsWith('.js')?'text/javascript':name.endsWith('.html')?'text/html':name.endsWith('.json')?'application/json':name.endsWith('.css')?'text/css':'application/octet-stream';
  response.writeHead(200,{'Content-Type':type,'Cache-Control':'no-store'});response.end(body);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url=`http://127.0.0.1:${server.address().port}/#snapshot`;
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto(url);
  await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
  await expect(page).toHaveTitle('upgrade-A');
  version='upgrade-B';
  await page.evaluate(async()=>{await (await navigator.serviceWorker.getRegistration()).update();});
  await expect.poll(()=>page.evaluate(()=>caches.keys())).toEqual(['heattime-demo-upgrade-B']);
  await context.setOffline(true);await page.reload();
  await expect(page).toHaveTitle('upgrade-B');
  await expect(page.getByText('시연 자료 저장됨 · 연결 없이 새로고침 가능',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'스냅샷 재현 실행 →'}).click();
  await expect(page.locator('.heat-cell')).toHaveCount(42);
  expect(errors).toEqual([]);
 }finally{
  await context.setOffline(false);await page.goto('about:blank');
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
 }
});
