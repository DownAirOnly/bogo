#!/usr/bin/env python3
"""Discover product photos from Open Food Facts v2 with conservative automated approval.

Only exact brand/product token matches and matching package sizes qualify.
Ambiguous offers remain review candidates. Never fabricates a photograph.
"""
import json,re,time,urllib.parse,urllib.request
from pathlib import Path
from urllib.error import HTTPError,URLError

CAT=Path("data/deals.json"); DB=Path("data/product-images.json"); CAND=Path("data/image-candidates.json")
STOP={"the","and","or","of","oz","size","products","assorted","variety","pack","with","for","flavors","gourmet"}
def norm(s):return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
def tokens(s):return set(re.findall(r"[a-z0-9]+",s.lower()))-STOP
def request(url):
    req=urllib.request.Request(url,headers={"User-Agent":"bogo-product-images/1.0 (https://github.com/DownAirOnly/bogo)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=22) as r:return json.load(r)
def fetch(q):
    params=urllib.parse.urlencode({"search_terms":q,"page_size":15,"fields":"code,product_name,brands,quantity,image_front_url"})
    urls=["https://world.openfoodfacts.org/api/v2/search?"+params,
          "https://world.openfoodfacts.net/api/v2/search?"+params]
    for url in urls:
        try:return request(url).get("products",[])
        except (HTTPError,URLError,TimeoutError,ValueError) as exc:print("Source error:",type(exc).__name__,str(exc)[:70])
    return []
def match(d,p):
    name=(p.get("product_name") or "").strip();brand=(p.get("brands") or "").strip()
    url=p.get("image_front_url") or ""
    if not name or not url.startswith("https://images.openfoodfacts.org/"):return None
    wanted=tokens(d["name"]);found=tokens(name+" "+brand)
    if not wanted or not found:return None
    coverage=len(wanted&found)/len(wanted)
    extra=len(found-wanted)/max(len(found),1)
    score=round(coverage*0.85+(1-extra)*0.15,3)
    size=re.search(r"(\d+(?:\.\d+)?)\s*(oz|fl oz|lb|g|ml|l)\b",d.get("details","").lower())
    q=(p.get("quantity") or "").lower()
    size_ok=bool(size and re.search(r"\b"+re.escape(size.group(1))+r"\s*"+re.escape(size.group(2))+r"\b",q))
    # Never auto-approve variant collections, ambiguous names, or absent size matches.
    ambiguous=bool(re.search(r"\bor\b|/|,|—|–",d["name"],re.I))
    approved=not ambiguous and size_ok and coverage==1 and extra<=0.25 and len(wanted)>=2
    return {"name":name,"brand":brand,"quantity":q,"barcode":p.get("code",""),
            "imageUrl":url,"source":"Open Food Facts","matchScore":score,"exactMatch":approved}
def main():
    catalog=json.loads(CAT.read_text());db=json.loads(DB.read_text());cands=json.loads(CAND.read_text())
    tried=0;approved=0;found=0
    for d in catalog["deals"]:
        if tried>=30:break
        if d.get("image") or "beer" in d["category"].lower() or "wine" in d["category"].lower():continue
        key=norm(d["name"])
        if key in db["products"]:continue
        if key in cands["products"]:continue
        tried+=1
        q=re.split(r"\s+[—–]\s+|\s+or\s+",d["name"])[0]
        options=[x for p in fetch(q) if (x:=match(d,p))]
        options.sort(key=lambda x:-x["matchScore"])
        if options:found+=1
        confident=[x for x in options if x["exactMatch"]]
        if len(confident)==1 and (len(options)==1 or confident[0]["matchScore"]>options[1]["matchScore"]+0.12):
            x=confident[0]
            db["products"][key]={"status":"approved","matchType":"exact","imageUrl":x["imageUrl"],
                 "source":"Open Food Facts","barcode":x["barcode"],"approvalMethod":"strict-automatic-v1"}
            approved+=1
        else:
            cands["products"][key]={"dealName":d["name"],"status":"needs-review","options":options[:5]}
        time.sleep(0.8)
    DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n")
    CAND.write_text(json.dumps(cands,ensure_ascii=False,indent=2)+"\n")
    print(f"Processed {tried}; suggestions for {found}; strictly approved {approved}")
if __name__=="__main__":main()
