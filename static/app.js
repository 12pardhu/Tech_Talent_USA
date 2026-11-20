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
menu?.addEventListener('click',()=>{const isOpen=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(isOpen));menu.setAttribute('aria-label',isOpen?'Close navigation menu':'Open navigation menu');menu.textContent=isOpen?'✕':'☰';});
document.getElementById('year').textContent=new Date().getFullYear();
document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');menu?.setAttribute('aria-expanded','false');menu?.setAttribute('aria-label','Open navigation menu');if(menu)menu.textContent='☰';}));

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


// Phase 1: gentle reveal effects and accessible form feedback.
const revealTargets=document.querySelectorAll('.section,.stats,.hero-copy,.hero-art');
revealTargets.forEach((el,index)=>{el.classList.add('reveal-ready');});
if('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
    if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}
  }),{threshold:0.12});
  revealTargets.forEach(el=>observer.observe(el));
}else{revealTargets.forEach(el=>el.classList.add('is-visible'));}

const resumeInput=form?.querySelector('input[name="resume"]');
resumeInput?.addEventListener('change',()=>{
  const file=resumeInput.files?.[0];
  if(file && file.size>5*1024*1024){
    resumeInput.setCustomValidity('Please choose a file smaller than 5 MB.');
    resumeInput.reportValidity();
    resumeInput.value='';
  }else{resumeInput.setCustomValidity('');}
});
