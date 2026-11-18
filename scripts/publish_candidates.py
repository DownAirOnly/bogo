#!/usr/bin/env python3
"""Merge discovered photo candidates into the latest GitHub file without rebase conflicts."""
import base64,json,os,time,urllib.error,urllib.request
from pathlib import Path
repo=os.environ.get("GITHUB_REPOSITORY","DownAirOnly/bogo")
token=os.environ["GH_TOKEN"]
url=f"https://api.github.com/repos/{repo}/contents/data/image-candidates.json"
local=json.loads(Path("data/image-candidates.json").read_text())
def api(method,data=None):
    req=urllib.request.Request(url,method=method,data=json.dumps(data).encode() if data else None,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"bogo-photo-database"})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
for attempt in range(5):
    remote=api("GET")
    current=json.loads(base64.b64decode(remote["content"]).decode())
    merged=dict(current)
    merged["products"]={**current.get("products",{}),**local.get("products",{})}
    # Keep existing reviewed candidate records and nonempty suggestions.
    for key,existing in current.get("products",{}).items():
        proposed=local.get("products",{}).get(key)
        if existing.get("status")!="needs-review" or (existing.get("options") and not (proposed or {}).get("options")):
            merged["products"][key]=existing
    if merged==current:
        print("No new candidates")
        break
    payload={"message":"Merge product image review candidates","sha":remote["sha"],"content":base64.b64encode((json.dumps(merged,indent=2,ensure_ascii=False)+"\n").encode()).decode()}
    try:
        api("PUT",payload)
        print("Saved",len(merged["products"]),"candidate records")
        break
    except urllib.error.HTTPError as e:
        if e.code not in (409,422) or attempt==4:raise
        time.sleep(1+attempt)
