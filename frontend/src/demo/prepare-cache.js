export async function prepareDemoCache(){
 const registration=await navigator.serviceWorker.register('./sw.js');
 try{await registration.update();}catch(error){if(!registration.active)throw error;}
 const pending=registration.installing||registration.waiting;
 if(pending&&pending.state!=='activated')await new Promise((resolve,reject)=>{
  const changed=()=>{
   if(pending.state==='activated'){pending.removeEventListener('statechange',changed);resolve();}
   else if(pending.state==='redundant'){pending.removeEventListener('statechange',changed);reject(new Error('시연 캐시 저장에 실패했습니다.'));}
  };
  pending.addEventListener('statechange',changed);changed();
 });
 await navigator.serviceWorker.ready;
 if(!navigator.serviceWorker.controller)await new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));
}
