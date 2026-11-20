// Remove external campaign/tracking parameters from the visible address bar.
// Keep functional query parameters and the current page/section intact.
const cleanUrl = new URL(window.location.href);
let removedTrackingParams = false;
for (const key of [...cleanUrl.searchParams.keys()]) {
  if (/^utm_/i.test(key) || ['gclid','fbclid','msclkid'].includes(key.toLowerCase())) {
    cleanUrl.searchParams.delete(key);
    removedTrackingParams = true;
  }
}
if (removedTrackingParams) {
  const cleanPath = cleanUrl.pathname + (cleanUrl.search ? cleanUrl.search : '') + cleanUrl.hash;
  window.history.replaceState({}, document.title, cleanPath);
}

const menu=document.getElementById('menu');
const nav=document.querySelector('nav');
menu?.addEventListener('click',()=>nav.classList.toggle('open'));
document.getElementById('year').textContent=new Date().getFullYear();
document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>nav.classList.remove('open')));

// Clean page URLs currently display the matching section on the shared homepage.
const routeTargets={'/about':'about','/services':'services','/how-we-work':'process','/contact':'contact'};
const currentPath=window.location.pathname.replace(/\/$/,'');
const targetId=routeTargets[currentPath];
if(targetId){requestAnimationFrame(()=>document.getElementById(targetId)?.scrollIntoView({behavior:'instant',block:'start'}));}

const form=document.getElementById('enquiry-form');
form?.addEventListener('submit',async e=>{
  e.preventDefault();
  const status=document.getElementById('form-status');
  const button=form.querySelector('button');
  const originalButton=button.innerHTML;
  button.disabled=true;
  button.textContent='Submitting…';
  status.textContent='';
  const data=new FormData(form);
  try{
    const response=await fetch('/api/enquiries',{method:'POST',body:data});
    const result=await response.json();
    if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Please check the form and try again.');
    status.textContent='Thank you! Your profile has been submitted successfully.';
    form.reset();
  }catch(err){
    status.textContent=err.message||'Something went wrong. Please try again.';
  }finally{
    button.disabled=false;
    button.innerHTML=originalButton;
  }
});
