import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
 plugins:[react(),{
  name:'snapshot-precache',
  generateBundle(options,bundle){
   const paths=['/','/index.html','/demo-assets.json',...Object.keys(bundle).map(name=>'/'+name)];
   this.emitFile({type:'asset',fileName:'demo-assets.json',source:JSON.stringify([...new Set(paths)])});
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
