// Build-stamped static assets only. API calls are never intercepted/cached.
const PREFIX='heattime-demo-';
const BUILD_VERSION='__HEATTIME_BUILD_ID__';
const CACHE_NAME=PREFIX+BUILD_VERSION;
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const response=await fetch(new URL('demo-assets.json',self.registration.scope),{cache:'no-store'});
 const urls=(await response.json()).map(u=>new URL(u,self.registration.scope).href);
 const cache=await caches.open(CACHE_NAME);await cache.addAll(urls);await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 const keys=(await caches.keys()).filter(k=>k.startsWith(PREFIX)&&k!==CACHE_NAME);
 await Promise.all(keys.map(k=>caches.delete(k)));await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
 event.respondWith((async()=>{
  const cache=await caches.open(CACHE_NAME);
  const stored=await cache.match(event.request);
  if(stored)return stored;
  try{return await fetch(event.request);}catch{return new Response('시연 캐시가 준비되지 않았습니다.',{status:503});}
 })());
});
