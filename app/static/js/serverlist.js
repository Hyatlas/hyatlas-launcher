// ───────────────────────────────────────────
//  CLIENT-SIDE  SERVER LIST  (Filter, Join) – ohne Slider
// ───────────────────────────────────────────

/* ----- DOM Refs ----- */
const listEl  = document.getElementById("srv-list");
const msgEl   = document.getElementById("srv-msg");
const inputEl = document.getElementById("srv-search");
const refBtn  = document.getElementById("refresh-btn");
const chanGrp = document.querySelector(".chan-group");

/* ----- State ----- */
let currentChan = "";
let allServers  = [];

/* ----- Server-Liste laden ----- */
async function fetchServers(){
  msgEl.textContent="Loading …";
  listEl.innerHTML="";
  try{
    const url=currentChan?`/api/servers?channel=${encodeURIComponent(currentChan)}`:"/api/servers";
    const res=await fetch(url);
    if(!res.ok)throw new Error("Failed to fetch list");
    allServers=await res.json();
    applyFilter();
  }catch(err){msgEl.textContent=err.message;}
}

/* ----- Filter anwenden ----- */
function applyFilter(){
  const q=inputEl.value.trim().toLowerCase();
  const subset=allServers.filter(s=>!q||s.name.toLowerCase().includes(q));
  listEl.innerHTML=subset.map(makeCard).join("");
  msgEl.textContent=subset.length?"":"No server match.";
}

/* ----- Ping-Bars ----- */
function createPingBars(ms=999){
  const c=ms<80?"#2ecc71":ms<150?"#f1c40f":"#e74c3c";
  return [1,2,3].map(i=>`<span style="display:block;width:5px;margin:1px;height:${i*4}px;background:${c};"></span>`).join("");
}

/* ----- Karte ----- */
function makeCard(s){
  const on=s.online??0, max=s.max??"–", ping=s.ping??999;
  return `
    <article class="srv-card">
      <div class="thumb"></div>
      <div class="srv-content">
        <h3 class="srv-title">${s.name}</h3>
        <p>${s.description??"No description…"}</p>
      </div>
      <div class="srv-actions">
        <div class="player-box"><i class="fa fa-user"></i><span class="pl-numbers">${on}/${max}</span></div>
        <button class="play-btn join-btn" data-srv="${btoa(JSON.stringify(s))}" title="Play"><i class="fa fa-play"></i></button>
        <div class="ping-bars">${createPingBars(ping)}</div>
      </div>
    </article>`;
}

/* ----- Join ----- */
document.addEventListener("click",e=>{
  const btn=e.target.closest(".join-btn"); if(!btn)return;
  const srv=JSON.parse(atob(btn.dataset.srv));
  sessionStorage.setItem("pendingServer",JSON.stringify(srv));
  window.location.href="/loading";
});

/* ----- Channel Buttons ----- */
chanGrp.onclick=e=>{
  if(!e.target.matches(".chan-btn"))return;
  chanGrp.querySelectorAll(".chan-btn").forEach(b=>b.classList.remove("active"));
  e.target.classList.add("active");
  currentChan=e.target.dataset.val;
  fetchServers();
};

/* ----- Suche & Refresh ----- */
inputEl.oninput=applyFilter;
refBtn.onclick =fetchServers;

/* ----- Init ----- */
fetchServers();
