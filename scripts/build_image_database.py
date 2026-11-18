#!/usr/bin/env python3
"""Build a reusable, reviewable product-photo database from Open Food Facts.

Search results are candidates, not approved photos. Only manually reviewed
records with status=approved may appear in the public catalog.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

DEALS = Path("data/deals.json")
DATABASE = Path("data/product-images.json")
CANDIDATES = Path("data/image-candidates.json")
STOP = {"the","and","or","of","oz","size","products","assorted","variety","pack","with","for","flavors"}
def words(s):
    return set(re.findall(r"[a-z0-9]+", str(s).lower())) - STOP
def search(q):
    params = urllib.parse.urlencode({"search_terms":q,"search_simple":1,"action":"process","json":1,"page_size":12,"fields":"product_name,brands,image_front_url,code,quantity"})
    request = urllib.request.Request("https://world.openfoodfacts.org/cgi/search.pl?"+params,headers={"User-Agent":"bogo-grocery-photo-database/0.2 (personal project; github.com/DownAirOnly/bogo)"})
    with urllib.request.urlopen(request,timeout=16) as r:
        return json.load(r).get("products",[])
def score(q,p):
    wanted = words(q)
    found = words((p.get("brands") or "")+" "+(p.get("product_name") or ""))
    if not wanted or not found: return 0
    overlap = len(wanted & found)
    return round(overlap/len(wanted)*0.75 + overlap/max(len(found),1)*0.25,3)
def main():
    catalog=json.loads(DEALS.read_text())
    db=json.loads(DATABASE.read_text()) if DATABASE.exists() else {"schemaVersion":1,"products":{}}
    candidates=json.loads(CANDIDATES.read_text()) if CANDIDATES.exists() else {"schemaVersion":1,"products":{}}
    added=0
    attempted=0
    for d in catalog["deals"]:
        key=d["id"]
        if d.get("image") or key in db["products"] or key in candidates["products"]: continue
        if attempted>=20: break
        attempted+=1
        q=d.get("searchQuery") or d["name"]
        # Broad offer groups may cover several products; keep suggestions review-only.
        try:
            options=[]
            for p in search(q):
                url=p.get("image_front_url")
                if not url or not url.startswith("https://images.openfoodfacts.org/"):continue
                rank=score(q,p)
                if rank<0.4:continue
                options.append({"name":p.get("product_name",""),"brand":p.get("brands",""),"quantity":p.get("quantity",""),"barcode":p.get("code",""),"imageUrl":url,"source":"Open Food Facts","matchScore":rank})
            options.sort(key=lambda x:-x["matchScore"])
            candidates["products"][key]={"dealName":d["name"],"status":"needs-review","options":options[:5]}
            added+=1
        except Exception as exc:
            print("Search unavailable:",q,type(exc).__name__,str(exc)[:80])
        time.sleep(1.2)
    CANDIDATES.write_text(json.dumps(candidates,indent=2,ensure_ascii=False)+"\n")
    print(f"Created {added} candidate records; {sum(bool(x['options']) for x in candidates['products'].values())} have image suggestions")
if __name__=="__main__":main()
