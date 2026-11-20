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
 const status=document.getElementById("form-status"),button=form.querySelector('button[type="submit"]'),resume=form.querySelector('input[name="resume"]');
 resume?.addEventListener("change",()=>{const file=resume.files?.[0];if(file&&file.size>5242880){resume.setCustomValidity("Please choose a file that is 5 MB or smaller.");resume.reportValidity();resume.value="";}else resume.setCustomValidity("");});
 form.addEventListener("submit",async e=>{e.preventDefault();if(!form.reportValidity()||button.disabled)return;const original=button.innerHTML;button.disabled=true;button.setAttribute("aria-busy","true");button.textContent="Submitting securely…";status.textContent="Please wait while we send your profile.";status.className="form-status is-pending";
  try{const response=await fetch("/api/enquiries",{method:"POST",body:new FormData(form),headers:{"Accept":"application/json"}});let result={};try{result=await response.json();}catch{}if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"We could not submit your profile. Please try again.");status.textContent="Thank you! Your profile has been received. Our team may contact you if a relevant opportunity comes up.";status.className="form-status is-success";form.reset();progress();}
  catch(err){status.textContent=err.message||"Something went wrong. Please try again, or contact us directly.";status.className="form-status is-error";}
  finally{button.disabled=false;button.removeAttribute("aria-busy");button.innerHTML=original;}
 });
}
const reveal=document.querySelectorAll(".section,.stats,.hero-copy,.hero-art");
if("IntersectionObserver" in window&&!window.matchMedia("(prefers-reduced-motion: reduce)").matches){const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add("is-visible");observer.unobserve(e.target);}}),{threshold:.12});reveal.forEach(el=>{el.classList.add("reveal-ready");observer.observe(el);});}else reveal.forEach(el=>el.classList.add("is-visible"));


// Subtle pointer parallax for the 3D hero scene (disabled on touch/reduced-motion).
(()=>{const scene=document.getElementById("hero-scene");if(!scene||!("matchMedia" in window)||window.matchMedia("(prefers-reduced-motion: reduce)").matches||!("PointerEvent" in window))return;const fine=window.matchMedia("(pointer:fine)").matches;if(!fine)return;const reset=()=>{scene.style.transform="";};scene.addEventListener("pointermove",e=>{const r=scene.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;scene.style.transform=`rotateX(${-y*3}deg) rotateY(${x*4}deg)`;});scene.addEventListener("pointerleave",reset);})();
