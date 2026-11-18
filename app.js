const $=s=>document.querySelector(s);const APP_VERSION="0.10.0";const storeKey="bogo-shopping-v1";let imageIndex={},deals=[],category="All",search="",list=new Set(JSON.parse(localStorage.getItem(storeKey)||"[]"));let view="deals";let favorites=new Set(JSON.parse(localStorage.getItem("bogo-favorites-v1")||"[]"));const icons={deals:"⌂",list:"☷",favorites:"♡"};const numericPrice=n=>(n===null||n===undefined||n==="")?null:(Number.isFinite(Number(n))&&Number(n)>=0?Number(n):null);
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
const browsePreferencesKey="bogo-browse-preferences-v1";
const browseDefaults={sort:"category",couponsOnly:false,hideAlcohol:false,maxBogoPrice:"all"};
let browsePreferences={...browseDefaults},browseFiltersOpen=false;
try{
  const previous=JSON.parse(localStorage.getItem(browsePreferencesKey)||"{}");
  if(previous&&typeof previous==="object"){
    const allowedSort=["category","price-asc","price-desc","name"];
    browsePreferences={
      sort:allowedSort.includes(previous.sort)?previous.sort:"category",
      couponsOnly:previous.couponsOnly===true,
      hideAlcohol:previous.hideAlcohol===true,
      maxBogoPrice:["all","5","10","20"].includes(previous.maxBogoPrice)?previous.maxBogoPrice:"all"
    };
  }
}catch{}
function saveBrowsePreferences(){
  try{localStorage.setItem(browsePreferencesKey,JSON.stringify(browsePreferences))}catch{}
}
function isAlcohol(d){return /beer|wine|alcohol|spirits|liquor/i.test(d.category||"")}
function matchesBrowseFilters(d){
  if(browsePreferences.couponsOnly&&!couponOffers(d).length)return false;
  if(browsePreferences.hideAlcohol&&isAlcohol(d))return false;
  const cap=browsePreferences.maxBogoPrice;
  if(cap!=="all"){
    const range=priceRange(d);
    if(!range||range[1]>Number(cap))return false;
  }
  return true;
}
function compareDealPrices(a,b,descending=false){
  const pa=priceRange(a),pb=priceRange(b);
  if(!pa&&!pb)return compareCategories(a.category||"Other",b.category||"Other")||a.name.localeCompare(b.name);
  if(!pa)return 1;
  if(!pb)return -1;
  const av=descending?pa[1]:pa[0],bv=descending?pb[1]:pb[0];
  return (descending?bv-av:av-bv)||compareCategories(a.category||"Other",b.category||"Other")||a.name.localeCompare(b.name);
}
function compareBrowseDeals(a,b){
  switch(browsePreferences.sort){
    case "price-asc":return compareDealPrices(a,b);
    case "price-desc":return compareDealPrices(a,b,true);
    case "name":return a.name.localeCompare(b.name);
    default:return compareCategories(a.category||"Other",b.category||"Other");
  }
}
function activeFilterCount(){
  return Number(browsePreferences.couponsOnly)+Number(browsePreferences.hideAlcohol)+Number(browsePreferences.maxBogoPrice!=="all");
}
// Coupon notes are sourced from the advertisement, not a live eligibility API.
// Never deduct these potential savings from the shopping-list estimate.
function couponOffers(d){
  const raw=String(d?.coupon||"").trim();
  if(!raw)return[];
  return raw.split(/\s+\|\s+/).map(s=>s.trim()).filter(Boolean).map(note=>{
    const type=/publix digital coupon/i.test(note)?"publix":
      /\bibotta\b/i.test(note)?"ibotta":/printable coupon/i.test(note)?"printable":"other";
    return {note,type};
  });
}
function couponTypeLabel(type){
  return type==="publix"?"Publix digital":type==="ibotta"?"Ibotta rebate":
    type==="printable"?"Printable coupon":"Offer";
}
function couponSourceLink(type){
  if(type==="publix")return '<a href="https://www.publix.com/savings/digital-coupons" target="_blank" rel="noopener noreferrer">View Publix coupons</a>';
  if(type==="ibotta")return '<a href="https://home.ibotta.com/" target="_blank" rel="noopener noreferrer">Check Ibotta offers</a>';
  return "";
}
function couponDetailsHTML(d){
  const offers=couponOffers(d);
  if(!offers.length)return"";
  return '<details class="coupon-details"><summary>'+offers.length+' coupon'+
    (offers.length===1?" / rebate note": " / rebate notes")+'</summary>'+
    '<div class="coupon-detail-body">'+offers.map(o=>
      '<div class="coupon-offer"><span class="coupon-provider">'+couponTypeLabel(o.type)+'</span>'+
      '<span class="coupon-note">'+esc(o.note)+'</span>'+couponSourceLink(o.type)+'</div>'
    ).join("")+
    '<p>From the ad listing. Check current availability, product size, purchase requirements and stacking rules. Not included in estimated totals.</p></div></details>';
}


// Keep product choices across weekly IDs, without requiring an account.
const listNameStorage="bogo-shopping-names-v1",favoriteNameStorage="bogo-favorite-names-v1";
let listNames=new Set(),favoriteNames=new Set();
try{listNames=new Set(JSON.parse(localStorage.getItem(listNameStorage)||"[]"))}catch{}
try{favoriteNames=new Set(JSON.parse(localStorage.getItem(favoriteNameStorage)||"[]"))}catch{}
function productKey(d){
  return String(d.name||"").split(/\s+[—–]\s+|,/)[0].toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
}
const shoppingItemsStorage="bogo-shopping-items-v2",shoppingMigrationKey="bogo-shopping-items-migrated-v2";
let shoppingItems={},shoppingItemsReady=false;
try{
  const stored=JSON.parse(localStorage.getItem(shoppingItemsStorage)||"{}");
  if(stored&&typeof stored==="object"&&!Array.isArray(stored))shoppingItems=stored;
}catch{}
function shoppingItemKey(d){
  return String((d.name||"")+"|"+(d.details||d.size||"")).toLowerCase()
    .normalize("NFKD").replace(/[\u0300-\u036f]/g,"")
    .replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
}
function shoppingItemCount(){return Object.keys(shoppingItems).length}
function isListed(d){
  return Boolean(shoppingItems[shoppingItemKey(d)])||
    (!shoppingItemsReady&&(list.has(d.id)||listNames.has(productKey(d))));
}
function isFavorite(d){return favorites.has(d.id)||favoriteNames.has(productKey(d))}
function save(){
  try{
    localStorage.setItem(storeKey,JSON.stringify([...list]));
    localStorage.setItem(listNameStorage,JSON.stringify([...listNames]));
    localStorage.setItem(shoppingItemsStorage,JSON.stringify(shoppingItems));
  }catch(error){console.warn("Could not save shopping list",error)}
}
function snapshotDeal(d){
  const w=weekCatalogs.find(w=>w.id===selectedWeekId);
  return {id:d.id,name:d.name,details:d.details||d.size||"",category:d.category||"Other",
    price:d.price??null,priceMin:d.priceMin??null,priceMax:d.priceMax??null,
    priceLabel:d.priceLabel||"",coupon:d.coupon||"",image:d.image||"",
    imageProductCode:d.imageProductCode||"",saleStart:w?.catalog.saleStart||"",
    saleEnd:w?.catalog.saleEnd||"",quantity:2,checked:false};
}
function addShoppingItem(d){
  const key=shoppingItemKey(d);
  if(!key)return;
  if(shoppingItems[key])return;
  shoppingItems[key]=snapshotDeal(d);
  list.add(d.id);listNames.add(productKey(d));save();
}
function removeShoppingItem(d){
  const key=shoppingItemKey(d);
  delete shoppingItems[key];
  list.delete(d.id);listNames.delete(productKey(d));
  save();
}
function toggleShoppingItem(d){isListed(d)?removeShoppingItem(d):addShoppingItem(d)}
function migrateShoppingItems(){
  if(localStorage.getItem(shoppingMigrationKey)==="yes"){shoppingItemsReady=true;return}
  const known=[...importedDeals,...weekCatalogs.flatMap(w=>w.catalog.deals)];
  for(const d of known){
    if((list.has(d.id)||listNames.has(productKey(d)))&&!shoppingItems[shoppingItemKey(d)]){
      shoppingItems[shoppingItemKey(d)]=snapshotDeal(d);
    }
  }
  shoppingItemsReady=true;
  save();
  try{localStorage.setItem(shoppingMigrationKey,"yes")}catch{}
}
function saveFavorites(){localStorage.setItem("bogo-favorites-v1",JSON.stringify([...favorites]));localStorage.setItem(favoriteNameStorage,JSON.stringify([...favoriteNames]))}function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}// Product photos are resolved inside the app. No manual photo links or user setup.
const imageCacheKey="bogo-product-photos-v3";
let imageCache={};
try{imageCache=JSON.parse(localStorage.getItem(imageCacheKey)||"{}")}catch{}
const pendingImages=new WeakSet();
let imageObserver=null,activeImages=0;
const imageQueue=[];
const photoTokens=s=>String(s||"").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g," ").split(/\s+/).filter(x=>x.length>2&&!["the","and","for","with","size","pack","products","organic","assorted","variety","brand","flavor","flavored"].includes(x));
function photoCacheKey(d){
  // Do not conflate products with similar brands or shared first words.
  // Include the full name and the advertised package size when available.
  return String((d.name||"")+"|"+(d.details||d.size||"")).toLowerCase()
    .normalize("NFKD").replace(/[\u0300-\u036f]/g,"")
    .replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
}
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
  const key=photoCacheKey(d);
  const sources=[
    "./images/products/"+encodeURIComponent(d.id)+".webp",
    d.image,
    imageCache[key]
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
// Dated weekly catalogs: current deals and an optional validated preview.
const weekCatalogs=[];
let selectedWeekId="primary",importedDeals=[];
function todayIso(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-")}
function dateLabel(iso){if(!iso)return"";const d=new Date(iso+"T12:00:00");return Number.isFinite(d.getTime())?d.toLocaleDateString("en-US",{month:"short",day:"numeric"}):""}
function weekState(c){
  if(!c)return"missing";
  const today=todayIso();
  return today<c.saleStart?"upcoming":today>c.saleEnd?"expired":"active";
}
function weekTitle(w){const state=weekState(w.catalog);return state==="active"?"This Week":state==="expired"?"Previous Ad":w.id==="next"?"Next Week":"Upcoming"}
function dealHeading(){const w=weekCatalogs.find(w=>w.id===selectedWeekId);const state=weekState(w?.catalog);return state==="upcoming"?"Upcoming deals":state==="expired"?"Previous deals":dealHeading()}
function weekBanner(){
  const w=weekCatalogs.find(w=>w.id===selectedWeekId);
  if(!w)return"";
  const c=w.catalog,state=weekState(c);
  const label=state==="active"?"On sale now":state==="upcoming"?"Upcoming sale":"Sale has ended";
  return '<div class="sale-banner'+(state==="expired"?' expired':"")+'"><span class="sale-state">'+label+'</span><span>'+esc(dateLabel(c.saleStart)+" – "+dateLabel(c.saleEnd))+'</span></div>';
}
function changeWeek(id){
  const w=weekCatalogs.find(w=>w.id===id);
  if(!w)return;
  selectedWeekId=id;deals=[...importedDeals,...w.catalog.deals];
  category="All";view="deals";render();
}
// One-page shopping checklist. Estimates assume Publix BOGO is buy two,
// pay the shelf price of one. Odd quantities pay for the extra individual item.
const hideCheckedStorage="bogo-hide-checked-v1";
let hideChecked=false;
try{hideChecked=localStorage.getItem(hideCheckedStorage)==="yes"}catch{}
function saveHideChecked(){
  try{localStorage.setItem(hideCheckedStorage,hideChecked?"yes":"no")}catch{}
}
function quantityOf(record){
  const n=Number(record.quantity);
  return Number.isInteger(n)?Math.min(99,Math.max(1,n)):2;
}
function shoppingListRecords(){
  const liveByKey=new Map(deals.map(d=>[shoppingItemKey(d),d]));
  return Object.entries(shoppingItems).filter(([,record])=>record&&record.name).map(([key,record])=>{
    const live=liveByKey.get(key);
    return {key,record,deal:live||record,live:!!live};
  }).sort((a,b)=>compareCategories(a.deal.category||"Other",b.deal.category||"Other")||
    a.deal.name.localeCompare(b.deal.name));
}
function estimateShoppingItem(entry){
  const qty=quantityOf(entry.record);
  const selected=weekCatalogs.find(w=>w.id===selectedWeekId);
  if(!entry.live)return {available:false,reason:"Not in selected ad"};
  if(selected&&weekState(selected.catalog)==="expired")
    return {available:false,reason:"Sale has ended"};
  if(priceUnit(entry.deal)==="/lb")
    return {available:false,reason:"Price per lb; weight needed"};
  const range=priceRange(entry.deal);
  if(!range)return {available:false,reason:"Price not listed"};
  const paid=Math.ceil(qty/2),free=Math.floor(qty/2);
  return {available:true,low:Math.round(range[0]*paid*100)/100,
    high:Math.round(range[1]*paid*100)/100,
    savedLow:Math.round(range[0]*free*100)/100,
    savedHigh:Math.round(range[1]*free*100)/100};
}
function moneyRange(low,high){
  return money(low)+(Math.abs(low-high)>.005?"–"+money(high):"");
}
function listEstimateText(entry){
  const estimate=estimateShoppingItem(entry);
  return estimate.available?moneyRange(estimate.low,estimate.high):estimate.reason;
}
function shoppingTotals(records){
  let low=0,high=0,savedLow=0,savedHigh=0,priced=0,excluded=0,checked=0;
  for(const entry of records){
    if(entry.record.checked)checked++;
    const e=estimateShoppingItem(entry);
    if(!e.available){excluded++;continue}
    low+=e.low;high+=e.high;savedLow+=e.savedLow;savedHigh+=e.savedHigh;priced++;
  }
  return {low,high,savedLow,savedHigh,priced,excluded,checked,total:records.length};
}
function shoppingSummaryHTML(records){
  const t=shoppingTotals(records);
  return '<div class="shopping-progress"><strong>Shopping list</strong><span>'+t.checked+' of '+t.total+' checked</span></div>'+'<div class="shopping-progress-track" role="progressbar" aria-label="Items checked" aria-valuemin="0" aria-valuemax="'+t.total+'" aria-valuenow="'+t.checked+'"><span style="width:'+(t.total?Math.round(t.checked/t.total*100):0)+'%"></span></div>'+
    '<div class="shopping-totals"><div><span>Estimated spend</span><strong>'+(t.priced?moneyRange(t.low,t.high):"—")+'</strong></div>'+
    '<div><span>BOGO savings</span><strong>'+(t.priced?moneyRange(t.savedLow,t.savedHigh):"—")+'</strong></div></div>'+
    '<p class="shopping-disclaimer">Estimates use two-for-one pricing, without tax or coupons.'+
    (t.excluded?' '+t.excluded+' item'+(t.excluded===1?" is":"s are")+' excluded from totals (missing price, per-pound, or not in this ad).':"")+'</p>';
}
function updateShoppingListUI(){
  const records=shoppingListRecords();
  const summary=document.querySelector(".shopping-summary");
  if(summary)summary.innerHTML=shoppingSummaryHTML(records);
  for(const entry of records){
    const row=document.querySelector('[data-list-key="'+entry.key+'"]');
    if(!row)continue;
    row.classList.toggle("is-checked",!!entry.record.checked);
    const count=row.querySelector("[data-count]");
    if(count)count.textContent=String(quantityOf(entry.record));
    const estimate=row.querySelector(".list-line-total");
    if(estimate)estimate.textContent=listEstimateText(entry);
    const minus=row.querySelector('[data-delta="-1"]');
    if(minus)minus.disabled=quantityOf(entry.record)<=1;
  }
}
function drawShoppingList(el){
  const all=shoppingListRecords();
  const visible=all.filter(e=>(!hideChecked||!e.record.checked)&&
    (e.deal.name+" "+(e.deal.details||"")).toLowerCase().includes(search.toLowerCase()));
  const grouped=new Map();
  for(const entry of visible){
    const c=entry.deal.category||"Other";
    if(!grouped.has(c))grouped.set(c,[]);
    grouped.get(c).push(entry);
  }
  el.innerHTML='<div class="shopping-summary">'+shoppingSummaryHTML(all)+'</div>'+
    (all.length?'<div class="list-tools"><span>'+visible.length+' of '+all.length+' products</span>'+
    '<div class="list-tool-actions"><button id="list-toggle-checked" type="button">'+(hideChecked?"Show checked":"Hide checked")+'</button>'+'<button id="list-copy" type="button">Copy list</button></div></div>':
    '<div class="empty">Your list is empty. Add BOGO deals from the Deals tab.</div>')+
    (all.length&&!visible.length?'<div class="empty">'+(hideChecked&&all.every(e=>e.record.checked)?"Everything is checked off. Use Show checked to review.":"No items match the current view.")+'</div>':"")+
    [...grouped.entries()].map(([group,entries])=>
      '<section class="list-category"><h3>'+esc(group)+' <span>'+entries.length+'</span></h3>'+
      entries.map(e=>{
        const d=e.deal,r=e.record,q=quantityOf(r),key=esc(e.key);
        return '<article class="shopping-row'+(r.checked?" is-checked":"")+'" data-list-key="'+key+'">'+
          '<input class="shopping-check" type="checkbox" data-check="'+key+'" aria-label="Mark '+esc(d.name)+' purchased"'+(r.checked?" checked":"")+'>'+
          '<div class="list-thumb"><div class="photo-placeholder" data-photo-id="'+esc(d.id)+'" data-name="'+esc(d.name)+'"><span class="placeholder-category">'+esc(d.category||"Grocery")+'</span><span class="placeholder-label">Loading…</span></div></div>'+
          '<div class="list-row-main"><div class="list-product-name">'+esc(d.name)+'</div>'+
          (d.details||d.size?'<div class="list-product-size">'+esc(d.details||d.size)+'</div>':"")+
          '<div class="list-product-price">BOGO '+priceText(d)+(e.live?"":' · <span>Not in selected ad</span>')+'</div>'+couponDetailsHTML(d)+
          '<div class="list-row-actions"><div class="quantity-control" aria-label="Quantity for '+esc(d.name)+'">'+
          '<button type="button" data-step="'+key+'" data-delta="-1" aria-label="Decrease quantity"'+(q<=1?" disabled":"")+'>−</button>'+
          '<span data-count="'+key+'">'+q+'</span>'+
          '<button type="button" data-step="'+key+'" data-delta="1" aria-label="Increase quantity">+</button></div>'+
          '<div class="list-line-total">'+esc(listEstimateText(e))+'</div></div>'+
          '<button type="button" class="list-remove" data-remove="'+key+'">Remove</button></div></article>';
      }).join("")+'</section>').join("")+
    (all.length?'<p class="shopping-footnote">A single item is full price; two cost the regular price of one. Prices vary by store.</p>':"");
  observeImages(visible.map(x=>x.deal));
  document.querySelectorAll("[data-check]").forEach(el=>el.onchange=()=>{
    const item=shoppingItems[el.dataset.check];
    if(!item)return;
    item.checked=el.checked;save();if(hideChecked&&item.checked)draw();else updateShoppingListUI();
  });
  document.querySelectorAll("[data-step]").forEach(btn=>btn.onclick=()=>{
    const item=shoppingItems[btn.dataset.step];
    if(!item)return;
    item.quantity=Math.min(99,Math.max(1,quantityOf(item)+Number(btn.dataset.delta)));
    save();updateShoppingListUI();
  });
  document.querySelectorAll("[data-remove]").forEach(btn=>btn.onclick=()=>{
    const key=btn.dataset.remove,item=shoppingItems[key];
    if(!item)return;
    removeShoppingItem(item);
    draw();
    const count=$("#listbtn");
    if(count)count.textContent="List ("+shoppingItemCount()+")";
  });
  if($("#list-toggle-checked"))$("#list-toggle-checked").onclick=()=>{
    hideChecked=!hideChecked;saveHideChecked();draw();
  };
  if($("#list-copy"))$("#list-copy").onclick=()=>{
    const text=all.map(e=>(e.record.checked?"✓ ":"☐ ")+quantityOf(e.record)+" × "+e.deal.name+
      " — "+(estimateShoppingItem(e).available?listEstimateText(e):"Price not confirmed")).join("\n");
    navigator.clipboard.writeText(text).catch(error=>console.warn("Copy unavailable",error));
  };
}
function render(){let cats=["All",...[...new Set(deals.map(x=>x.category||"Other"))].sort(compareCategories)];const browseTools=view==="deals"?
  '<div class="browse-tools"><label class="sort-control" for="deal-sort"><span>Sort</span><select id="deal-sort" aria-label="Sort deals"><option value="category"'+(browsePreferences.sort==="category"?' selected':"")+
  '>My category order</option><option value="price-asc"'+(browsePreferences.sort==="price-asc"?' selected':"")+
  '>Lowest BOGO price</option><option value="price-desc"'+(browsePreferences.sort==="price-desc"?' selected':"")+
  '>Highest BOGO price</option><option value="name"'+(browsePreferences.sort==="name"?' selected':"")+
  '>Name A–Z</option></select></label><button class="action browse-filter-toggle" id="filter-toggle" type="button" aria-expanded="'+browseFiltersOpen+'">Filters'+(activeFilterCount()?' ('+activeFilterCount()+')':"")+'</button></div>'+
  '<div class="browse-filters" id="browse-filters"'+(browseFiltersOpen?"":' hidden')+'><label class="filter-check"><input type="checkbox" id="filter-coupons"'+(browsePreferences.couponsOnly?" checked":"")+'> Coupons only</label>'+
  '<label class="filter-check"><input type="checkbox" id="filter-alcohol"'+(browsePreferences.hideAlcohol?" checked":"")+'> Hide alcohol</label>'+
  '<label class="filter-limit" for="filter-price"><span>Maximum BOGO price</span><select id="filter-price">'+
  [['all','Any price'],['5','$5 or less'],['10','$10 or less'],['20','$20 or less']].map(([val,label])=>'<option value="'+val+'"'+(browsePreferences.maxBogoPrice===val?" selected":"")+'>'+label+'</option>').join("")+'</select></label>'+
  '<button class="filter-import" id="import" type="button">Import deal text</button><button class="filter-reset" id="filter-reset" type="button">Reset filters</button></div>'
  :"";const weekSwitcher=weekCatalogs.length>1?'<div class="week-switch">'+weekCatalogs.map(w=>'<button data-week="'+w.id+'" class="'+(w.id===selectedWeekId?"active":"")+'">'+weekTitle(w)+'<small>'+dateLabel(w.catalog.saleStart)+'–'+dateLabel(w.catalog.saleEnd)+'</small></button>').join("")+'</div>':"";$("#app").innerHTML='<header class="site-header"><div class="header-inner"><div class="brandline" aria-label="bogo."><span class="brand-initial">b</span><span class="brand-rest">ogo</span><span class="brand-period" aria-hidden="true"></span></div><button class="version-trigger" id="versionbtn" aria-label="View version history">v'+APP_VERSION+'</button></div></header><main class="wrap"><div class="controls"><input id="search" placeholder="Search products and brands" value="'+esc(search)+'"><button class="action" id="listbtn">List ('+shoppingItemCount()+')</button></div><div class="tabs">'+cats.map(c=>'<button data-cat="'+esc(c)+'" class="'+(c===category?"active":"")+'">'+esc(c)+'</button>').join("")+'</div>'+weekSwitcher+browseTools+'<div id="body"></div></main><nav class="bottom-nav" aria-label="Main navigation"><button data-view="deals" class="'+(view==="deals"?"active":"") +'"><span class="nav-symbol">⌂</span><small>Deals</small></button><button data-view="list" class="'+(view==="list"?"active":"") +'"><span class="nav-symbol">☷</span><small>Lists</small></button><button data-view="favorites" class="'+(view==="favorites"?"active":"") +'"><span class="nav-symbol">♡</span><small>Favorites</small></button></nav>';if(view!=="deals"){const cats=$(".tabs");if(cats)cats.hidden=true;const weeks=$(".week-switch");if(weeks)weeks.hidden=true}$("#versionbtn").onclick=()=>{view="changelog";render()};$("#search").addEventListener("input",e=>{search=e.target.value;draw()});document.querySelectorAll("[data-cat]").forEach(b=>b.onclick=()=>{category=b.dataset.cat;view="deals";render()});document.querySelectorAll("[data-week]").forEach(b=>b.onclick=()=>changeWeek(b.dataset.week));$("#listbtn").onclick=()=>{view="list";render()};if($("#import"))$("#import").onclick=()=>{view="import";render()};
if($("#deal-sort"))$("#deal-sort").onchange=e=>{
  browsePreferences.sort=e.target.value;saveBrowsePreferences();draw();
};
if($("#filter-toggle"))$("#filter-toggle").onclick=()=>{
  browseFiltersOpen=!browseFiltersOpen;
  const panel=$("#browse-filters"),btn=$("#filter-toggle");
  panel.hidden=!browseFiltersOpen;
  btn.setAttribute("aria-expanded",String(browseFiltersOpen));
};
function updateFilter(key,value){
  browsePreferences[key]=value;
  saveBrowsePreferences();
  const b=$("#filter-toggle");
  if(b)b.textContent="Filters"+(activeFilterCount()?" ("+activeFilterCount()+")":"");
  draw();
}
if($("#filter-coupons"))$("#filter-coupons").onchange=e=>updateFilter("couponsOnly",e.target.checked);
if($("#filter-alcohol"))$("#filter-alcohol").onchange=e=>updateFilter("hideAlcohol",e.target.checked);
if($("#filter-price"))$("#filter-price").onchange=e=>updateFilter("maxBogoPrice",e.target.value);
if($("#filter-reset"))$("#filter-reset").onclick=()=>{
  browsePreferences={...browsePreferences,...browseDefaults};
  saveBrowsePreferences();
  render();
};document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>{view=b.dataset.view;search="";render();window.scrollTo(0,0)});draw()}function draw(){let el=$("#body");if(view==="changelog"){el.innerHTML='<section class="panel"><h2>Version history</h2><p>Current version: v'+APP_VERSION+'</p><div class="changelog"><h3>v0.10.0 — Shopping list</h3><p>One-page list with quantities, purchased checkboxes, grouped categories, and estimated BOGO spending and savings. Saved products survive catalog changes; incomplete prices are excluded rather than guessed.</p><h3>v0.9.9 — Deal browsing and filters</h3><p>Added compact sorting by category, price and product name, with an optional filter drawer for coupons, alcohol and maximum deal price. Preferences are saved on-device and do not change the default category order.</p><h3>v0.9.8 — Faster, more reliable photos</h3><p>Prioritizes locally cached images before third-party requests, avoids photo collisions between similar products, and preserves found photos across weekly catalog changes.</p><h3>v0.9.7 — Dated weekly ads</h3><p>Shows sale dates and current, upcoming, or expired status; lets you switch weeks when a verified preview is available.</p><h3>v0.9.6 — Compact deal cards</h3><p>Removed stretched vertical gaps between product names, sizes and prices, and hid empty size labels.</p><h3>v0.9.5 — Automatic PWA updates</h3><p>On launch, return, and while open, the app checks the latest deployed build and silently refreshes when a new one is available. The service worker prefers network-fresh code and deals, using cache only offline.</p><h3>v0.9.4 — Photo brightness and category preferences</h3><p>Corrected dark product images by blending against a light warm image surface, and reordered categories to prioritize frozen, pantry, dairy, produce and meat.</p><h3>v0.9.3 — Shopping order and card cleanup</h3><p>Essential grocery categories first, alcohol last, concise per-item pricing, and safe formatting for unknown prices. Warmer photo presentation.</p><h3>v0.8.1 — Simpler image browsing</h3><p>One-tap Google Images search for every deal. Automated image discovery paused to keep maintenance lightweight.</p><h3>v0.8 — Weekly automation</h3><p>Scheduled deal imports, validation and safe publishing, with manual ad URL fallback.</p><h3>v0.7 — Photo database</h3><p>Persistent image suggestions, manual approval and automated caching.</p><h3>v0.6 — Product photos</h3><p>Cached and validated product photos, card image containment, image attribution.</p><h3>v0.5 — Full weekly catalog</h3><p>150 Publix offers, price ranges and photo matching.</p><h3>v0.4 — Navigation</h3><p>Deals, Lists, Favorites, saved favorites.</p><h3>v0.3 — Everyday design</h3><p>Dark layout, shared typography and consistent cards.</p><h3>v0.2 — Gold branding</h3><p>Gold color system, b. logo and icons.</p><h3>v0.1 — First build</h3><p>Search, filters, shopping list, import and GitHub Pages.</p></div><p>Development milestones reconstructed from GitHub commits.</p><button class="action" id="back-to-deals">Back to deals</button></section>';$("#back-to-deals").onclick=()=>{view="deals";render()};return}if(view==="import"){el.innerHTML='<section class="panel"><h2>Import deal text</h2><p>Paste lines like: Product Name, 16 oz, BOGO $5.99. Imports are saved on this device.</p><textarea id="raw" placeholder="Paste BOGO listings here"></textarea><div class="actions"><button class="action primary" id="parse">Import text</button></div><p id="status"></p></section>';$("#parse").onclick=()=>{let lines=$("#raw").value.split(/\n+/).map(x=>x.trim()).filter(x=>/BOGO/i.test(x));let added=lines.map((s,i)=>{let m=s.match(/BOGO\s*\$([\d.]+)/i);return{id:"manual-"+Date.now()+"-"+i,name:s.split(/,?\s*BOGO/i)[0],category:"Imported",price:m?Number(m[1]):null,details:s}});deals=[...added,...deals];localStorage.setItem("bogo-imports",JSON.stringify(added.concat(JSON.parse(localStorage.getItem("bogo-imports")||"[]"))));$("#status").textContent=added.length+" listings imported.";view="deals";render()};return}if(view==="list"){drawShoppingList(el);return}let items=deals.filter(d=>(view==="list"?isListed(d):view==="favorites"?isFavorite(d):true)&&(category==="All"||view==="list"||d.category===category)&&((d.name+" "+(d.details||"")).toLowerCase().includes(search.toLowerCase()))&&(view!=="deals"||matchesBrowseFilters(d)));if(view==="deals")items.sort(compareBrowseDeals);else items.sort((a,b)=>compareCategories(a.category||"Other",b.category||"Other"));el.innerHTML=(view==="deals"?weekBanner():"")+'<div class="meta">'+(view==="list"?"Shopping list":view==="favorites"?"Favorite products":"Available deals")+' · '+items.length+' items'+(view==="list"?'<button class="action" id="copy" style="float:right">Copy list</button>':"")+'</div><div class="grid">'+items.map(d=>'<article class="deal"><div class="picture"><div class="photo-placeholder" data-photo-id="'+esc(d.id)+'" data-name="'+esc(d.name)+'"><span class="placeholder-category">'+esc(d.category||"Grocery")+'</span><span class="placeholder-label">Loading photo…</span></div></div><div class="info">'+'<div class="name">'+esc(d.name)+'</div>'+(d.imageVariant?'<div class="image-variant">Representative: '+esc(d.imageVariant)+'</div>':'')+(d.details||d.size?'<div class="size">'+esc(d.details||d.size)+'</div>':"")+'<div class="price">BOGO '+priceText(d)+'</div>'+(eachPrice(d)?'<div class="each">'+eachPrice(d)+'</div>':"")+couponDetailsHTML(d)+'<button data-id="'+esc(d.id)+'">'+(isListed(d)?"Remove from list":"+ Add to list")+'</button><button class="favorite-btn" data-fav="'+esc(d.id)+'" aria-label="Toggle favorite">'+(isFavorite(d)?'♥ Favorited':'♡ Favorite')+'</button></div></article>').join("")+'</div>'+(items.length?"":'<div class="empty">No matching deals.</div>');observeImages(items);document.querySelectorAll("[data-id]").forEach(b=>b.onclick=()=>{const d=deals.find(x=>x.id===b.dataset.id);if(!d)return;toggleShoppingItem(d);if(view==="deals"){b.textContent=isListed(d)?"Remove from list":"+ Add to list";const count=$("#listbtn");if(count)count.textContent="List ("+shoppingItemCount()+")"}else render()});document.querySelectorAll("[data-fav]").forEach(b=>b.onclick=()=>{const d=deals.find(x=>x.id===b.dataset.fav);if(!d)return;if(isFavorite(d)){favorites.delete(d.id);favoriteNames.delete(productKey(d))}else{favorites.add(d.id);favoriteNames.add(productKey(d))}saveFavorites();if(view==="deals")b.textContent=isFavorite(d)?"♥ Favorited":"♡ Favorite";else render()});if($("#copy"))$("#copy").onclick=()=>navigator.clipboard.writeText(items.map(x=>x.name+" — BOGO "+priceText(x)).join("\n"))}async function init(){
  async function readWeek(path,optional=false){
    try{
      const response=await fetch(path,{cache:"no-store"});
      if(!response.ok)throw Error("Catalog unavailable: "+path);
      const raw=await response.json();
      if(!Array.isArray(raw.deals)||!raw.saleStart||!raw.saleEnd)return null;
      return {...raw,deals:raw.deals.map((d,i)=>({...d,id:String(d.id??"deal-"+i),
        name:d.name||d.title||"Unnamed product",price:d.price??d.bogoPrice??null}))};
    }catch(error){if(!optional)console.warn(error);return null}
  }
  const primary=await readWeek("./data/deals.json");
  const next=await readWeek("./data/next-deals.json",true);
  if(primary)weekCatalogs.push({id:"primary",catalog:primary});
  if(next&&(!primary||next.saleStart>primary.saleStart))weekCatalogs.push({id:"next",catalog:next});
  for(const w of weekCatalogs)for(const d of w.catalog.deals){
    if(list.has(d.id))listNames.add(productKey(d));
    if(favorites.has(d.id))favoriteNames.add(productKey(d));
  }
  saveFavorites();
  try{importedDeals=JSON.parse(localStorage.getItem("bogo-imports")||"[]")}catch{importedDeals=[]}
  if(!Array.isArray(importedDeals))importedDeals=[];
  migrateShoppingItems();
  const chosen=weekCatalogs.find(w=>weekState(w.catalog)==="active")||
    weekCatalogs.find(w=>weekState(w.catalog)==="upcoming")||
    weekCatalogs[weekCatalogs.length-1];
  if(chosen){selectedWeekId=chosen.id;deals=[...importedDeals,...chosen.catalog.deals]}
  else deals=[...importedDeals];
  render();
}
init();