// Fast, offline regression tests for weekly BOGO comparison heuristics.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("app.js","utf8");
const from = source.indexOf("const dealStopWords=");
const to = source.indexOf("function previousWeekCatalog()",from);
assert(from>=0 && to>from,"Deal-comparison helpers not found in app.js");
const context = vm.createContext({});
vm.runInContext(source.slice(from,to)+
  "\nthis.comparableDeals=comparableDeals;",context,{timeout:1000});
const same=(a,b)=>context.comparableDeals({name:a},{name:b});

assert(same("Del Monte Vegetables, 14.5 to 15.25 oz can","Del Monte Vegetables"),
  "same Del Monte vegetable offer");
assert(!same("Del Monte Fruit","Del Monte Vegetables"),
  "different Del Monte grocery categories");
assert(!same("Birds Eye Vegetables","Birds Eye Voila! Skillet Meals"),
  "brand overlap is not product identity");
assert(same("Hunt’s Tomatoes or Sauce","Hunt’s Tomatoes, Tomato Sauce or Purée"),
  "same Hunt's tomato family despite alternate punctuation");
assert(!same("Betty Crocker Brownie Mix","Betty Crocker Frosting"),
  "different Betty Crocker products");
assert(same("General Mills Cereal","General Mills Cereal, 12 to 27 oz"),
  "same cereal family with changed size details");
console.log("BOGO cross-week matching: 6 quick regression checks passed");
