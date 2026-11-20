// Tech Talent USA — Phase 1 accessible interactions and candidate form UX.
const cleanUrl=new URL(window.location.href);let removedTrackingParams=false;
for(const key of [...cleanUrl.searchParams.keys()])if(/^utm_/i.test(key)||["gclid","fbclid","msclkid"].includes(key.toLowerCase())){cleanUrl.searchParams.delete(key);removedTrackingParams=true;}
if(removedTrackingParams)window.history.replaceState({},document.title,cleanUrl.pathname+(cleanUrl.search?cleanUrl.search:"")+cleanUrl.hash);
const menu=document.getElementById("menu"),nav=document.getElementById("site-nav");
menu?.addEventListener("click",()=>{const open=nav.classList.toggle("open");menu.setAttribute("aria-expanded",String(open));menu.setAttribute("aria-label",open?"Close navigation menu":"Open navigation menu");menu.textContent=open?"✕":"☰";});
document.getElementById("year").textContent=new Date().getFullYear();
nav?.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>{nav.classList.remove("open");menu?.setAttribute("aria-expanded","false");menu?.setAttribute("aria-label","Open navigation menu");if(menu)menu.textContent="☰";}));
const targets={"/about":"about","/services":"services","/how-we-work":"process","/contact":"contact"},target=targets[location.pathname.replace(/\/$/,"")];
if(target)requestAnimationFrame(()=>document.getElementById(target)?.scrollIntoView({behavior:"instant",block:"start"}));
const form=document.getElementById("enquiry-form");
if(form){
 const status=document.getElementById("form-status"),button=form.querySelector('button[type="submit"]'),resume=form.querySelector('input[name="resume"]'),fill=document.getElementById("progress-fill"),label=document.getElementById("progress-label"),required=[...form.querySelectorAll("[required]")];
 const progress=()=>{const steps=[...form.querySelectorAll("[data-progress-step]")];const valid=n=>{const x=form.querySelector(`[name="${n}"]`);return !!x&&x.value.trim().length>0&&x.validity.valid;};const completed=[valid("name")&&valid("email")&&valid("phone"),valid("skills"),true,!!form.querySelector('input[name="consent"]')?.checked];const done=completed.filter(Boolean).length,pct=Math.round(done/4*100);steps.forEach((step,i)=>{step.classList.toggle("is-complete",completed[i]);const mark=step.querySelector(".form-step-heading b");if(mark)mark.textContent=completed[i]?"Complete":"";});if(fill)fill.style.width=pct+"%";if(label)label.textContent=`${done} of 4 sections complete`;};
 form.addEventListener("input",progress);form.addEventListener("change",progress);progress();
 resume?.addEventListener("change",()=>{const file=resume.files?.[0];if(file&&file.size>5242880){resume.setCustomValidity("Please choose a file that is 5 MB or smaller.");resume.reportValidity();resume.value="";}else resume.setCustomValidity("");});
 form.addEventListener("submit",async e=>{e.preventDefault();if(!form.reportValidity()||button.disabled)return;const original=button.innerHTML;button.disabled=true;button.setAttribute("aria-busy","true");button.textContent="Submitting securely…";status.textContent="Please wait while we send your profile.";status.className="form-status is-pending";
  try{const response=await fetch("/api/enquiries",{method:"POST",body:new FormData(form),headers:{"Accept":"application/json"}});let result={};try{result=await response.json();}catch{}if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"We could not submit your profile. Please try again.");status.textContent="Thank you! Your profile has been received. Our team may contact you if a relevant opportunity comes up.";status.className="form-status is-success";form.reset();progress();}
  catch(err){status.textContent=err.message||"Something went wrong. Please try again, or contact us directly.";status.className="form-status is-error";}
  finally{button.disabled=false;button.removeAttribute("aria-busy");button.innerHTML=original;}
 });
}
const reveal=document.querySelectorAll(".section,.stats,.hero-copy,.hero-art");
if("IntersectionObserver" in window&&!window.matchMedia("(prefers-reduced-motion: reduce)").matches){const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add("is-visible");observer.unobserve(e.target);}}),{threshold:.12});reveal.forEach(el=>{el.classList.add("reveal-ready");observer.observe(el);});}else reveal.forEach(el=>el.classList.add("is-visible"));


// Polished navigation and lightweight page interactions.
(function(){
 const header=document.querySelector(".header"),progress=document.createElement("div");
 progress.id="site-scroll-progress";progress.setAttribute("aria-hidden","true");document.body.append(progress);
 const quick=document.createElement("a");quick.id="quick-profile-link";quick.href="/contact";quick.innerHTML='Share your profile <span aria-hidden="true">↗</span>';quick.setAttribute("aria-label","Go to candidate profile registration");document.body.append(quick);
 const links=[...document.querySelectorAll('#site-nav a[href^="/"]')];
 const sections=[...document.querySelectorAll("main section[id]")];
 let ticking=false;
 const update=()=>{
  const max=document.documentElement.scrollHeight-window.innerHeight;
  const y=window.scrollY;
  progress.style.width=(max>0?Math.min(100,y/max*100):0)+"%";
  header?.classList.toggle("is-scrolled",y>12);
  quick.classList.toggle("is-visible",y>420);
  const current=sections.filter(s=>s.getBoundingClientRect().top<160).at(-1);
  links.forEach(a=>{const href=a.getAttribute("href");const active=current&&((href==="/about"&&current.id==="about")||(href==="/services"&&current.id==="services")||(href==="/how-we-work"&&current.id==="process")||(href==="/contact"&&current.id==="contact"));if(active)a.setAttribute("aria-current","location");else a.removeAttribute("aria-current");});
  ticking=false;
 };
 window.addEventListener("scroll",()=>{if(!ticking){requestAnimationFrame(update);ticking=true;}},{passive:true});
 window.addEventListener("resize",update,{passive:true});update();
})();
