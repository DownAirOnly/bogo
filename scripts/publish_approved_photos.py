#!/usr/bin/env python3
"""Merge new strict approvals into the latest GitHub photo database."""
import base64,json,os,time,urllib.error,urllib.request
from pathlib import Path
repo=os.environ.get("GITHUB_REPOSITORY","DownAirOnly/bogo");token=os.environ["GH_TOKEN"]
url=f"https://api.github.com/repos/{repo}/contents/data/product-images.json"
local=json.loads(Path("data/product-images.json").read_text())
def api(method,payload=None):
    req=urllib.request.Request(url,method=method,data=json.dumps(payload).encode() if payload else None,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"bogo-photo-database"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
for attempt in range(5):
    remote=api("GET");current=json.loads(base64.b64decode(remote["content"]))
    merged=dict(current);merged["products"]={**local.get("products",{}),**current.get("products",{})}
    if merged==current:print("No new approved images");break
    payload={"message":"Merge strictly matched product photos","sha":remote["sha"],"content":base64.b64encode((json.dumps(merged,indent=2,ensure_ascii=False)+"\n").encode()).decode()}
    try:api("PUT",payload);print("Published",len(merged["products"]),"approved entries");break
    except urllib.error.HTTPError as e:
        if e.code not in (409,422) or attempt==4:raise
        time.sleep(attempt+2)
