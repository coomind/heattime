// Only static demo assets are cached. API calls are never intercepted/cached.
const PREFIX='heattime-demo-';
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const response=await fetch('/demo-assets.json',{cache:'no-store'});
 const urls=await response.json();
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(urls)));
 const version=Array.from(new Uint8Array(digest)).map(v=>v.toString(16).padStart(2,'0')).join('').slice(0,16);
 const cache=await caches.open(PREFIX+version);await cache.addAll(urls);await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 const keys=(await caches.keys()).filter(k=>k.startsWith(PREFIX));
 await Promise.all(keys.slice(0,-1).map(k=>caches.delete(k)));await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
 event.respondWith((async()=>{
  const keys=(await caches.keys()).filter(k=>k.startsWith(PREFIX));
  const cache=keys.length?await caches.open(keys[keys.length-1]):null;
  const stored=cache?await cache.match(event.request):null;
  if(stored)return stored;
  try{return await fetch(event.request);}catch{return new Response('시연 캐시가 준비되지 않았습니다.',{status:503});}
 })());
});
