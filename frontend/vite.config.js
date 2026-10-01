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
 envDir:false,server:{proxy:{'/api':'http://127.0.0.1:8000'}}
});
