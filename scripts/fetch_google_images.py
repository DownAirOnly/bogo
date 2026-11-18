#!/usr/bin/env python3
"""Resolve first Google Images results once, save tiny static JSON; requires SERPAPI_KEY."""
import json,os,time,urllib.parse,urllib.request,sys
from pathlib import Path
deals=json.loads(Path("data/deals.json").read_text())["deals"]
path=Path("data/google-images.json")
out=json.loads(path.read_text())
key=os.getenv("SERPAPI_KEY")
if not key:sys.exit("SERPAPI_KEY missing: no images fetched or changed.")
count=0
for deal in deals:
    ident=deal["id"]
    if out["images"].get(ident):continue
    name=deal["name"].split(" — ")[0].split(", ")[0].strip()
    query=f"{name} product packaging front label"
    params=urllib.parse.urlencode({"engine":"google_images","q":query,"gl":"us","hl":"en","api_key":key})
    req=urllib.request.Request("https://serpapi.com/search.json?"+params,headers={"User-Agent":"bogo/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=25) as resp:data=json.load(resp)
        results=data.get("images_results",[])
        if not results:
            print("No image",ident);continue
        first=results[0]
        url=first.get("original") or first.get("thumbnail")
        if not url or not url.startswith("https://"):continue
        out["images"][ident]={"url":url,"thumbnail":first.get("thumbnail",""),"title":first.get("title",""),"source":first.get("source",""),"query":query}
        count+=1
    except Exception as exc:print("Search failed",ident,type(exc).__name__,str(exc)[:100])
    if count%10==0 and count:path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    time.sleep(.2)
path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print(f"Added {count} first-result image URLs; total {len(out['images'])}/{len(deals)}")
