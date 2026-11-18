const $=s=>document.querySelector(s);const APP_VERSION="0.9.4";const storeKey="bogo-shopping-v1";let imageIndex={},deals=[],category="All",search="",list=new Set(JSON.parse(localStorage.getItem(storeKey)||"[]"));let view="deals";let favorites=new Set(JSON.parse(localStorage.getItem("bogo-favorites-v1")||"[]"));const icons={deals:"⌂",list:"☷",favorites:"♡"};const numericPrice=n=>(n===null||n===undefined||n==="")?null:(Number.isFinite(Number(n))&&Number(n)>=0?Number(n):null);
const money=n=>{const v=numericPrice(n);return v===null?"Price not listed":"$"+(Math.round((v+Number.EPSILON)*100)/100).toFixed(2)};
function priceRange(d){
  const label=String(d.priceLabel||"");
  const found=(label.match(/\d+(?:\.\d+)?/g)||[]).map(Number);
  const lo=numericPrice(d.priceMin)??(found.length?found[0]:null)??numericPrice(d.price);
  if(lo===null)return null;
  const hi=numericPrice(d.priceMax)??(found.length>1?found[1]:null)??lo;
  return [Math.min(lo,hi),Math.max(lo,hi)];
}
const priceUnit=d=>/\/\s*lb\b/i.test(String(d.priceLabel||""))?"/lb":"/ea";
function priceText(d){
  const range=priceRange(d);
  if(!range)return"price varies";
  return money(range[0])+(range[1]!==range[0]?"–"+money(range[1]):"")+(priceUnit(d)==="/lb"?"/lb":"");
}
function eachPrice(d){
  const range=priceRange(d);
  if(!range)return"";
  return money(range[0]/2)+(range[1]!==range[0]?"–"+money(range[1]/2):"")+priceUnit(d);
}
const categoryOrder=["Frozen Foods","Pantry, Snacks & Drinks","Dairy & Refrigerated","Produce & Deli","Meat & Seafood","Home, Health & Cleaning"];
function categoryRank(c){
  if(/beer|wine|alcohol|spirits|liquor/i.test(c))return 1000;
  const i=categoryOrder.indexOf(c);
  return i===-1?100:i;
}
function compareCategories(a,b){return categoryRank(a)-categoryRank(b)||a.localeCompare(b)}
function save(){localStorage.setItem(storeKey,JSON.stringify([...list]))}function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}// Product photos are resolved inside the app. No manual photo links or user setup.
const imageCacheKey="bogo-product-photos-v2";
let imageCache={};
try{imageCache=JSON.parse(localStorage.getItem(imageCacheKey)||"{}")}catch{}
const pendingImages=new WeakSet();
let imageObserver=null,activeImages=0;
const imageQueue=[];
const photoTokens=s=>String(s||"").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g," ").split(/\s+/).filter(x=>x.length>2&&!["the","and","for","with","size","pack","products","organic","assorted","variety","brand","flavor","flavored"].includes(x));
function imageQuery(d){
  return String(d.searchQuery||d.name||"").split(/\s+[—–]\s+/)[0].replace(/\s+(?:or|and\/or)\s+.+$/i,"").replace(/\s*[,;\/]\s+.*$/,"").replace(/\([^)]*\)/g,"").trim();
}
function scoreProduct(p,wanted){
  const available=photoTokens((p.brands||"")+" "+(p.product_name||"")+" "+(p.product_name_en||""));
  if(!available.length||!wanted.length)return 0;
  const hits=wanted.filter(t=>available.some(a=>a===t||a.startsWith(t)||t.startsWith(a))).length;
  const brandHit=wanted[0]&&available.includes(wanted[0])?0.15:0;
  return hits/wanted.length+brandHit;
}
function safeImage(url){
  if(typeof url!=="string"||!url)return"";
  try{const u=new URL(url,location.href);return ["https:","http:"].includes(u.protocol)?u.href:""}catch{return""}
}
async function fetchJson(url,ms=8500){
  const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),ms);
  try{const r=await fetch(url,{signal:ctrl.signal,mode:"cors",cache:"force-cache"});if(!r.ok)throw Error("Photo search returned "+r.status);return await r.json()}
  finally{clearTimeout(timer)}
}
function tryPhoto(el,url){
  return new Promise(resolve=>{
    if(!el.isConnected||!safeImage(url))return resolve(false);
    const img=new Image();
    img.alt=el.dataset.name||"Product photo";
    img.referrerPolicy="no-referrer";
    img.decoding="async";
    let finished=false;
    const timer=setTimeout(()=>finish(false),8500);
    function finish(ok){
      if(finished)return;
      finished=true;clearTimeout(timer);
      img.onload=null;img.onerror=null;
      if(ok&&el.isConnected){el.classList.add("has-photo");el.replaceChildren(img);resolve(true)}
      else resolve(false);
    }
    img.onload=()=>finish(img.naturalWidth>=32&&img.naturalHeight>=32);
    img.onerror=()=>finish(false);
    img.src=url;
  });
}
function imageFromProduct(p){return safeImage(p?.image_front_url||p?.image_front_small_url||p?.image_url)}
async function openFoodFactsCandidates(d){
  const result=[];
  const code=d.imageProductCode;
  if(code){
    try{
      const u="https://world.openfoodfacts.org/api/v2/product/"+encodeURIComponent(code)+".json?fields=product_name,brands,image_front_url,image_front_small_url,image_url";
      const j=await fetchJson(u);
      const p=j.product;
      const url=imageFromProduct(p);
      if(url)result.push(url);
    }catch(e){console.debug("Barcode photo lookup failed",e)}
  }
  const query=imageQuery(d),wanted=photoTokens(query);
  if(!query)return result;
  const variants=[query];
  const words=query.split(/\s+/);
  if(words.length>3)variants.push(words.slice(0,3).join(" "));
  for(const q of variants){
    try{
      const params=new URLSearchParams({search_terms:q,page_size:"20",fields:"product_name,product_name_en,brands,image_front_url,image_front_small_url,image_url"});
      const j=await fetchJson("https://world.openfoodfacts.org/api/v2/search?"+params);
      const candidates=(j.products||[]).filter(p=>imageFromProduct(p)).map(p=>({url:imageFromProduct(p),score:scoreProduct(p,wanted)})).sort((a,b)=>b.score-a.score);
      // Prefer an identifiable brand/product; retain the closest result for broader listings.
      for(const c of candidates.filter(c=>c.score>=0.45).slice(0,5))if(!result.includes(c.url))result.push(c.url);
      if(result.length)break;
    }catch(e){console.debug("Product photo lookup failed",e)}
  }
  return result;
}
async function commonsCandidates(d){
  const query=imageQuery(d);
  if(!query)return[];
  try{
    const p=new URLSearchParams({action:"query",generator:"search",gsrsearch:query+" product package",gsrnamespace:"6",gsrlimit:"12",prop:"imageinfo",iiprop:"url|mime",iiurlwidth:"500",format:"json",origin:"*"});
    const j=await fetchJson("https://commons.wikimedia.org/w/api.php?"+p);
    const pages=Object.values(j.query?.pages||{});
    const wanted=photoTokens(query);
    return pages.filter(p=>p.imageinfo?.[0]&&/\.(jpe?g|png|webp)$/i.test(p.title||""))
      .map(p=>({url:safeImage(p.imageinfo[0].thumburl||p.imageinfo[0].url),score:scoreProduct({product_name:p.title,brands:""},wanted)}))
      .filter(x=>x.url&&x.score>=0.45).sort((a,b)=>b.score-a.score).slice(0,3).map(x=>x.url);
  }catch(e){console.debug("Alternate photo lookup failed",e);return[]}
}
async function lookupImage(d,el){
  const key=imageQuery(d);
  const sources=[
    imageCache[key],
    d.image,
    "./images/products/"+encodeURIComponent(d.id)+".webp"
  ].filter(Boolean);
  for(const url of sources){
    if(await tryPhoto(el,url)){
      if(key){imageCache[key]=safeImage(url);try{localStorage.setItem(imageCacheKey,JSON.stringify(imageCache))}catch{}}
      return;
    }
    if(imageCache[key]===url){delete imageCache[key];try{localStorage.setItem(imageCacheKey,JSON.stringify(imageCache))}catch{}}
  }
  const candidates=[...await openFoodFactsCandidates(d),...await commonsCandidates(d)];
  for(const url of [...new Set(candidates)]){
    if(!el.isConnected)return;
    if(await tryPhoto(el,url)){
      if(key){imageCache[key]=url;try{localStorage.setItem(imageCacheKey,JSON.stringify(imageCache))}catch{}}
      return;
    }
  }
  if(el.isConnected)el.innerHTML='<span class="placeholder-category">'+esc(d.category||"Grocery")+'</span><span class="placeholder-label">Photo not available</span>';
}
function pumpImages(){
  while(activeImages<4&&imageQueue.length){
    const {deal,el}=imageQueue.shift();
    if(!el.isConnected)continue;
    activeImages++;
    lookupImage(deal,el).catch(e=>{console.warn("Photo unavailable",deal.name,e);if(el.isConnected)el.textContent="Photo not available"}).finally(()=>{activeImages--;pumpImages()});
  }
}
function observeImages(items){
  imageObserver?.disconnect();
  imageQueue.length=0;
  if(!("IntersectionObserver" in window)){
    document.querySelectorAll("[data-photo-id]").forEach(el=>{const deal=items.find(x=>x.id===el.dataset.photoId);if(deal){imageQueue.push({deal,el})}});
    pumpImages();return;
  }
  const byId=new Map(items.map(d=>[d.id,d]));
  imageObserver=new IntersectionObserver(entries=>{
    for(const entry of entries){
      if(!entry.isIntersecting)continue;
      imageObserver.unobserve(entry.target);
      const deal=byId.get(entry.target.dataset.photoId);
      if(deal&&!pendingImages.has(entry.target)){pendingImages.add(entry.target);imageQueue.push({deal,el:entry.target})}
    }
    pumpImages();
  },{rootMargin:"500px"});
  document.querySelectorAll("[data-photo-id]").forEach(el=>imageObserver.observe(el));
}
function render(){let cats=["All",...[...new Set(deals.map(x=>x.category||"Other"))].sort(compareCategories)];$("#app").innerHTML='<header class="site-header"><div class="header-inner"><div class="brandline" aria-label="bogo."><span class="brand-initial">b</span><span class="brand-rest">ogo</span><span class="brand-period" aria-hidden="true"></span></div><button class="version-trigger" id="versionbtn" aria-label="View version history">v'+APP_VERSION+'</button></div></header><main class="wrap"><div class="controls"><input id="search" placeholder="Search products and brands" value="'+esc(search)+'"><button class="action" id="listbtn">List ('+list.size+')</button></div><div class="tabs">'+cats.map(c=>'<button data-cat="'+esc(c)+'" class="'+(c===category?"active":"")+'">'+esc(c)+'</button>').join("")+'</div><div class="actions"><button class="action" id="browse">Browse</button><button class="action" id="import">Import deals</button></div><div id="body"></div></main><nav class="bottom-nav" aria-label="Main navigation"><button data-view="deals" class="'+(view==="deals"?"active":"") +'"><span class="nav-symbol">⌂</span><small>Deals</small></button><button data-view="list" class="'+(view==="list"?"active":"") +'"><span class="nav-symbol">☷</span><small>Lists</small></button><button data-view="favorites" class="'+(view==="favorites"?"active":"") +'"><span class="nav-symbol">♡</span><small>Favorites</small></button></nav>';$("#versionbtn").onclick=()=>{view="changelog";render()};$("#search").addEventListener("input",e=>{search=e.target.value;draw()});document.querySelectorAll("[data-cat]").forEach(b=>b.onclick=()=>{category=b.dataset.cat;view="deals";render()});$("#listbtn").onclick=()=>{view="list";draw()};$("#browse").onclick=()=>{view="deals";draw()};$("#import").onclick=()=>{view="import";render()};document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>{view=b.dataset.view;search="";render();window.scrollTo(0,0)});draw()}function draw(){let el=$("#body");if(view==="changelog"){el.innerHTML='<section class="panel"><h2>Version history</h2><p>Current version: v'+APP_VERSION+'</p><div class="changelog"><h3>v0.9.4 — Photo brightness and category preferences</h3><p>Corrected dark product images by blending against a light warm image surface, and reordered categories to prioritize frozen, pantry, dairy, produce and meat.</p><h3>v0.9.3 — Shopping order and card cleanup</h3><p>Essential grocery categories first, alcohol last, concise per-item pricing, and safe formatting for unknown prices. Warmer photo presentation.</p><h3>v0.8.1 — Simpler image browsing</h3><p>One-tap Google Images search for every deal. Automated image discovery paused to keep maintenance lightweight.</p><h3>v0.8 — Weekly automation</h3><p>Scheduled deal imports, validation and safe publishing, with manual ad URL fallback.</p><h3>v0.7 — Photo database</h3><p>Persistent image suggestions, manual approval and automated caching.</p><h3>v0.6 — Product photos</h3><p>Cached and validated product photos, card image containment, image attribution.</p><h3>v0.5 — Full weekly catalog</h3><p>150 Publix offers, price ranges and photo matching.</p><h3>v0.4 — Navigation</h3><p>Deals, Lists, Favorites, saved favorites.</p><h3>v0.3 — Everyday design</h3><p>Dark layout, shared typography and consistent cards.</p><h3>v0.2 — Gold branding</h3><p>Gold color system, b. logo and icons.</p><h3>v0.1 — First build</h3><p>Search, filters, shopping list, import and GitHub Pages.</p></div><p>Development milestones reconstructed from GitHub commits.</p><button class="action" id="back-to-deals">Back to deals</button></section>';$("#back-to-deals").onclick=()=>{view="deals";render()};return}if(view==="import"){el.innerHTML='<section class="panel"><h2>Import deal text</h2><p>Paste lines like: Product Name, 16 oz, BOGO $5.99. Imports are saved on this device.</p><textarea id="raw" placeholder="Paste BOGO listings here"></textarea><div class="actions"><button class="action primary" id="parse">Import text</button></div><p id="status"></p></section>';$("#parse").onclick=()=>{let lines=$("#raw").value.split(/\n+/).map(x=>x.trim()).filter(x=>/BOGO/i.test(x));let added=lines.map((s,i)=>{let m=s.match(/BOGO\s*\$([\d.]+)/i);return{id:"manual-"+Date.now()+"-"+i,name:s.split(/,?\s*BOGO/i)[0],category:"Imported",price:m?Number(m[1]):null,details:s}});deals=[...added,...deals];localStorage.setItem("bogo-imports",JSON.stringify(added.concat(JSON.parse(localStorage.getItem("bogo-imports")||"[]"))));$("#status").textContent=added.length+" listings imported.";view="deals";render()};return}let items=deals.filter(d=>(view==="list"?list.has(d.id):view==="favorites"?favorites.has(d.id):true)&&(category==="All"||view==="list"||d.category===category)&&((d.name+" "+(d.details||"")).toLowerCase().includes(search.toLowerCase())));if(view==="deals")items.sort((a,b)=>compareCategories(a.category||"Other",b.category||"Other"));el.innerHTML='<div class="meta">'+(view==="list"?"Shopping list":view==="favorites"?"Favorite products":"Available deals")+' · '+items.length+' items'+(view==="list"?'<button class="action" id="copy" style="float:right">Copy list</button>':"")+'</div><div class="grid">'+items.map(d=>'<article class="deal"><div class="picture"><div class="photo-placeholder" data-photo-id="'+esc(d.id)+'" data-name="'+esc(d.name)+'"><span class="placeholder-category">'+esc(d.category||"Grocery")+'</span><span class="placeholder-label">Loading photo…</span></div></div><div class="info">'+'<div class="name">'+esc(d.name)+'</div>'+(d.imageVariant?'<div class="image-variant">Representative: '+esc(d.imageVariant)+'</div>':'')+'<div class="size">'+esc(d.details||d.size||"")+'</div><div class="price">BOGO '+priceText(d)+'</div>'+(eachPrice(d)?'<div class="each">'+eachPrice(d)+'</div>':"")+(d.coupon?'<div class="coupon">'+esc(d.coupon)+'</div>':"")+'<button data-id="'+esc(d.id)+'">'+(list.has(d.id)?"Remove from list":"+ Add to list")+'</button><button class="favorite-btn" data-fav="'+esc(d.id)+'" aria-label="Toggle favorite">'+(favorites.has(d.id)?'♥ Favorited':'♡ Favorite')+'</button></div></article>').join("")+'</div>'+(items.length?"":'<div class="empty">No matching deals.</div>');observeImages(items);document.querySelectorAll("[data-id]").forEach(b=>b.onclick=()=>{list.has(b.dataset.id)?list.delete(b.dataset.id):list.add(b.dataset.id);save();render()});document.querySelectorAll("[data-fav]").forEach(b=>b.onclick=()=>{favorites.has(b.dataset.fav)?favorites.delete(b.dataset.fav):favorites.add(b.dataset.fav);localStorage.setItem("bogo-favorites-v1",JSON.stringify([...favorites]));render()});if($("#copy"))$("#copy").onclick=()=>navigator.clipboard.writeText(items.map(x=>x.name+" — BOGO "+money(x.price)).join("\n"))}async function init(){try{let r=await fetch("./data/deals.json",{cache:"no-store"});if(!r.ok)throw Error("Catalog unavailable");let j=await r.json();deals=(Array.isArray(j)?j:j.deals||[]).map((d,i)=>({...d,id:String(d.id??"deal-"+i),name:d.name||d.title||"Unnamed product",price:d.price??d.bogoPrice??null}));}catch(e){console.warn(e)}deals=[...JSON.parse(localStorage.getItem("bogo-imports")||"[]"),...deals];render()}init();