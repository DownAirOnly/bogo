// Fast smoke tests of production app functions without modifying user data.
// Run: node tests/test_app_smoke.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const src = fs.readFileSync("app.js", "utf8");
let passed = 0;
function check(label, run) {
  run();
  passed += 1;
  console.log("PASS " + label);
}
function codeBetween(begin, end) {
  const a = src.indexOf(begin), b = src.indexOf(end, a);
  assert(a >= 0 && b > a, "Missing implementation section: " + begin);
  return src.slice(a, b);
}
function makeContext(code, globals = {}, functions = []) {
  const ctx = vm.createContext({...globals});
  vm.runInContext(code + "\n" + functions.map(f => "this."+f+"="+f+";").join("\n"),ctx,{timeout:2000});
  return ctx;
}

const pricing = makeContext(
  codeBetween("function quantityOf(record){", "function shoppingSummaryHTML(records){"),
  {
    selectedShoppingList:()=>({weekStart:"2026-11-19"}),
    adForDate:()=>({saleStart:"2026-11-19",saleEnd:"2026-11-25"}),
    weekState:()=> "active",
    shoppingItems:{},
    shoppingItemKey:d=>d.name,
    compareCategories:()=>0,
    priceUnit:d=>/\/lb/.test(d.priceLabel||"")?"/lb":"/ea",
    priceRange:d=>d.priceMin==null?null:[d.priceMin,d.priceMax??d.priceMin],
    money:n=>"$"+Number(n).toFixed(2)
  },["quantityOf","estimateShoppingItem","shoppingTotals"]
);
const deal={name:"Test Grocery",priceMin:5,priceMax:5,priceLabel:"5.00"};
const entry=(quantity,checked=false,info=deal,live=true)=>({
  deal:info,record:{name:info.name,quantity,checked},live
});
check("BOGO prices 1–4 units with odd quantities at full price",()=>{
  const expected=[[1,5,0],[2,5,5],[3,10,5],[4,10,10]];
  for(const [n,spend,savings] of expected) {
    const result=pricing.estimateShoppingItem(entry(n));
    assert.equal(result.available,true);
    assert.equal(result.low,spend);
    assert.equal(result.savedLow,savings);
  }
});
check("list totals and still-to-buy exclude checked items",()=>{
  const totals=pricing.shoppingTotals([entry(2,true),entry(3,false)]);
  assert.equal(totals.low,15);
  assert.equal(totals.savedLow,10);
  assert.equal(totals.remainingLow,10);
  assert.equal(totals.checked,1);
});
check("unpriced, per-pound, and outside-ad items are excluded",()=>{
  assert.equal(pricing.estimateShoppingItem(entry(2,false,{name:"Unpriced",priceMin:null})).available,false);
  assert.equal(pricing.estimateShoppingItem(entry(2,false,{name:"Loose produce",priceMin:5,priceLabel:"5/lb"})).available,false);
  assert.equal(pricing.estimateShoppingItem(entry(2,false,deal,false)).available,false);
  assert.equal(pricing.quantityOf({quantity:120}),99);
  assert.equal(pricing.quantityOf({quantity:-3}),1);
});
const coupon = makeContext(
  codeBetween("function couponOffers(d){","function couponTypeLabel(type){") +
  codeBetween("function couponQuantityWarningHTML(d,quantity){","function wireCouponDetails(root=document){"),
  {},["couponOffers","couponQuantityWarningHTML"]
);
check("coupon 2-unit requirement warns for one, clears for two",()=>{
  const d={coupon:"$1 off 2 Chobani multipack — Publix digital coupon"};
  assert.equal(coupon.couponOffers(d)[0].minQuantity,2);
  assert.match(coupon.couponQuantityWarningHTML(d,1),/at least 2 units/);
  assert.equal(coupon.couponQuantityWarningHTML(d,2),"");
});
check("dollar-spend thresholds are not mistaken for quantity rules",()=>{
  const d={coupon:"$5 off $15 participating General Mills products — Publix digital coupon"};
  assert.equal(coupon.couponOffers(d)[0].minQuantity,null);
  assert.equal(coupon.couponQuantityWarningHTML(d,1),"");
});
const lists = {
  first:{id:"first",weekStart:"2026-11-12",weekEnd:"2026-11-18",items:{}},
  second:{id:"second",weekStart:"2026-11-19",weekEnd:"2026-11-25",items:{}}
};
let current=lists.first,saves=0;
const key=d=>d.name+"|"+(d.details||d.size||"");
const listFns = makeContext(
  codeBetween("function snapshotDeal(d){","function createShoppingList(name,weekStart){"),
  {
    shoppingLists:lists,
    targetShoppingList:()=>current,
    currentAd:()=>({saleStart:current.weekStart,saleEnd:current.weekEnd}),
    shoppingItemKey:key,
    isListed:(d,id)=>!!(id?lists[id]:current).items[key(d)],
    save:()=>{saves++}
  },["addShoppingItem","toggleShoppingItem"]
);
check("different sale-week lists remain isolated and toggles persist",()=>{
  listFns.addShoppingItem(deal,"first");
  assert.equal(Object.keys(lists.first.items).length,1);
  assert.equal(Object.keys(lists.second.items).length,0);
  listFns.addShoppingItem(deal,"second");
  assert.equal(Object.keys(lists.second.items).length,1);
  listFns.toggleShoppingItem(deal,"first");
  assert.equal(Object.keys(lists.first.items).length,0);
  assert.equal(Object.keys(lists.second.items).length,1);
  assert(saves>=3);
});
const favorite = makeContext(
  codeBetween("function favoriteSnapshot(d){","function matchingFavoriteSnapshot(d){"),
  {shoppingItemKey:key,productSourceUrl:()=> "https://www.iheartpublix.com/2026/11/example/"},
  ["favoriteSnapshot"]
);
check("favorite snapshots retain product and original source",()=>{
  const snapshot=favorite.favoriteSnapshot(deal);
  assert.equal(snapshot.name,deal.name);
  assert.equal(snapshot.priceMin,5);
  assert.match(snapshot.sourceUrl,/iheartpublix/);
});
check("current UI contains the recently added controls",()=>{
  for(const snippet of [
    "New this week","Bring over unchecked items","Still to buy",
    "Coupons and rebates to check","product-source-link","list-share",
    "favoriteSnapshotsStorage","selectedSaleStorage"
  ])assert(src.includes(snippet),"Missing control: "+snippet);
});
console.log("APP_SMOKE_RESULT "+passed+" passed, 0 failed");
