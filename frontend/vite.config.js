import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
export default defineConfig({
 plugins:[react(),{
  name:'snapshot-precache',
  generateBundle(options,bundle){
   const paths=['/','/index.html','/demo-assets.json','/sw.js',...Object.keys(bundle).map(name=>'/'+name)];
   this.emitFile({type:'asset',fileName:'demo-assets.json',source:JSON.stringify([...new Set(paths)])});
  },
  writeBundle(options,bundle){
   const entries=Object.entries(bundle).sort(([a],[b])=>a.localeCompare(b)).map(([name,item])=>[name,item.type==='asset'?String(item.source):item.code]);
   const version=createHash('sha256').update(JSON.stringify(entries)).digest('hex');
   const template=readFileSync(new URL('./src/demo/service-worker.template.js',import.meta.url),'utf8');
   writeFileSync(resolve(options.dir,'sw.js'),template.replace('__HEATTIME_BUILD_ID__',version));
  }
 }],
 build:{rollupOptions:{output:{manualChunks(id){
  const normalized=id.replaceAll('\\','/');
  if(normalized.endsWith('/snapshot-exports.json'))return 'snapshot-exports';
  if(normalized.includes('/node_modules/')){
   if(/\/node_modules\/(react|react-dom|scheduler|react-is)\//.test(normalized))return 'react';
   if(/\/node_modules\/(recharts|@reduxjs|redux|immer|victory-vendor|d3-|eventemitter3|react-smooth|decimal.js-light)/.test(normalized))return 'charts';
   return 'vendor';
  }
 }}}},
 envDir:false,server:{proxy:{'/api':'http://127.0.0.1:8000'}}
});
