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
  button.disabled=true;
  button.textContent='Sending…';
  status.textContent='';
  const data=Object.fromEntries(new FormData(form).entries());
  data.positions=Number(data.positions);
  try{
    const response=await fetch('/api/enquiries',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result=await response.json();
    if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Please check the form and try again.');
    status.textContent='Thank you! Your hiring enquiry has been received.';
    form.reset();
  }catch(err){
    status.textContent=err.message||'Something went wrong. Please contact our team.';
  }finally{
    button.disabled=false;
    button.innerHTML='Send hiring enquiry <span>→</span>';
  }
});