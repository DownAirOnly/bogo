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
    params=urllib.parse.urlencode({'search_terms':q,'search_simple':1,'action':'process','json':1,'page_size':12,'fields':'product_name,brands,image_front_url,code,quantity'})
    urls=['https://world.openfoodfacts.org/cgi/search.pl?'+params,'https://world.openfoodfacts.net/cgi/search.pl?'+params]
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'bogo-photo-guide/0.7 (github.com/DownAirOnly/bogo)'})
            with urllib.request.urlopen(req,timeout=18) as response:
                return json.load(response).get('products',[])
        except Exception as exc:
            print('Source unavailable',type(exc).__name__,str(exc)[:100])
            time.sleep(2)
    return []
def commons_search(q):
    """Search Wikimedia Commons file titles; candidates require manual review."""
    params=urllib.parse.urlencode({
        "action":"query","generator":"search","gsrsearch":q+" filetype:bitmap",
        "gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo",
        "iiprop":"url|extmetadata","iiurlwidth":640,"format":"json"
    })
    req=urllib.request.Request("https://commons.wikimedia.org/w/api.php?"+params,
        headers={"User-Agent":"bogo-photo-guide/0.8 (https://github.com/DownAirOnly/bogo)"})
    with urllib.request.urlopen(req,timeout=15) as response:
        pages=json.load(response).get("query",{}).get("pages",{})
    result=[]
    for page in pages.values():
        info=(page.get("imageinfo") or [{}])[0]
        url=info.get("thumburl") or info.get("url")
        if not url or not url.startswith("https://"):continue
        title=page.get("title","").removeprefix("File:")
        match=score(q,{"brands":"","product_name":title.replace("_"," ")})
        if match<0.45:continue
        meta=info.get("extmetadata",{})
        result.append({"name":title,"brand":"","quantity":"","barcode":"",
            "imageUrl":url,"source":"Wikimedia Commons","sourcePage":info.get("descriptionurl",""),
            "license":re.sub("<[^>]+>","",meta.get("LicenseShortName",{}).get("value","")),
            "matchScore":match})
    return result
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
        key=re.sub(r"[^a-z0-9]+","-",d["name"].lower()).strip("-")
        if d.get("image") or key in db["products"]: continue
        existing=candidates["products"].get(key)
        if existing and (existing.get("options") or existing.get("status")!="needs-review"):continue
        if attempted>=15: break
        attempted+=1
        if any(word in d.get("category","").lower() for word in ("beer","wine","alcohol")): continue
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
            if not options:
                try: options=commons_search(q)
                except Exception as exc: print("Commons unavailable:",type(exc).__name__,str(exc)[:90])
            options.sort(key=lambda x:-x["matchScore"])
            candidates["products"][key]={"dealName":d["name"],"status":"needs-review","options":options[:5]}
            added+=1
        except Exception as exc:
            print("Search unavailable:",q,type(exc).__name__,str(exc)[:80])
        time.sleep(1.2)
    CANDIDATES.write_text(json.dumps(candidates,indent=2,ensure_ascii=False)+"\n")
    print(f"Created {added} candidate records; {sum(bool(x['options']) for x in candidates['products'].values())} have image suggestions")
if __name__=="__main__":main()
