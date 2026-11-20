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
 const progress=()=>{const done=required.filter(x=>x.type==="checkbox"?x.checked:x.value.trim().length>0).length,pct=Math.round(done/required.length*100);if(fill)fill.style.width=pct+"%";if(label)label.textContent=pct===100?"Required information complete":pct+"% of required information completed";};
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
