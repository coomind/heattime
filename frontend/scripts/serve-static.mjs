// Minimal static file server for the judge demo (no dependencies, no backend).
// Usage: node scripts/serve-static.mjs <folder> [port] [base path]
//   node scripts/serve-static.mjs dist-demo 8128 /heattime/   -> http://127.0.0.1:8128/heattime/
import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {extname,join,normalize,resolve} from 'node:path';
const [folder='dist-demo',port='8128',base='/']=process.argv.slice(2);
const root=resolve(folder),prefix=base.endsWith('/')?base:base+'/';
const TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8',
 '.json':'application/json; charset=utf-8','.woff':'font/woff','.woff2':'font/woff2','.svg':'image/svg+xml','.png':'image/png',
 '.pdf':'application/pdf','.mp4':'video/mp4','.ico':'image/x-icon','.txt':'text/plain; charset=utf-8'};
createServer(async(req,res)=>{
 const path=decodeURIComponent(new URL(req.url,'http://x').pathname);
 if(path==='/'&&prefix!=='/'){res.writeHead(302,{Location:prefix});return res.end();}
 if(!path.startsWith(prefix)){res.writeHead(404);return res.end('not found');}
 let file=normalize(join(root,path.slice(prefix.length)));
 if(!file.startsWith(root)){res.writeHead(403);return res.end();}
 try{if((await stat(file)).isDirectory())file=join(file,'index.html');
  const body=await readFile(file);res.writeHead(200,{'Content-Type':TYPES[extname(file)]||'application/octet-stream','Cache-Control':'no-cache'});res.end(body);}
 catch{res.writeHead(404);res.end('not found');}
}).listen(Number(port),'127.0.0.1',()=>console.log(`serving ${root} at http://127.0.0.1:${port}${prefix}`));
