/* ───────────── Dummy-Daten ───────────── */
const ITEMS = {
  legs: [
    {id:1, img:"/static/img/pants_1.png"},
    {id:2, img:"/static/img/pants_2.png"},
    {id:3, img:"/static/img/pants_3.png"},
  ],
  /* … head / body / feet … */
};
const COLORS = [
  "#202020","#ffffff","#ffce00","#ff8243","#c84848","#59b0ff",
  "#7acb59","#9c59ff","#ff59b0","#ff7f7f","#32c8c8","#ff641f"
];

/* DOM */
const gallery   = document.getElementById("gallery");
const colorBar  = document.getElementById("color-bar");
const partTabs  = document.getElementById("part-tabs");
const partTitle = document.getElementById("part-title");

let currentPart = "legs";
let selected = { legs:null, color:null };

/* Build Gallery */
function loadPart(part){
  currentPart = part;
  partTitle.textContent = part.charAt(0).toUpperCase()+part.slice(1);
  gallery.innerHTML="";
  ITEMS[part].forEach(it=>{
    const d=document.createElement("div");
    d.className="item";
    d.style.backgroundImage=`url(${it.img})`;
    d.onclick=()=> selectItem(part,it.id,d);
    gallery.appendChild(d);
  });
}

/* Build Color dots */
COLORS.forEach(c=>{
  const dot=document.createElement("div");
  dot.className="color-dot";
  dot.style.background=c;
  dot.onclick=()=> selectColor(c,dot);
  colorBar.appendChild(dot);
});

/* Select HANDLERS */
function selectItem(part,id,node){
  gallery.querySelectorAll(".selected").forEach(el=>el.classList.remove("selected"));
  node.classList.add("selected");
  selected[part]=id;
}
function selectColor(col,node){
  colorBar.querySelectorAll(".selected").forEach(el=>el.classList.remove("selected"));
  node.classList.add("selected");
  selected.color=col;
}

/* Tabs */
partTabs.querySelectorAll("button").forEach(btn=>{
  btn.onclick=()=>{
    partTabs.querySelector(".active").classList.remove("active");
    btn.classList.add("active");
    loadPart(btn.dataset.part);
  };
});

/* Init */
loadPart(currentPart);
