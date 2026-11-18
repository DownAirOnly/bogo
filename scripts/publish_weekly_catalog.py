#!/usr/bin/env python3
"""Publish validated catalog via GitHub contents API with conflict protection."""
import base64,datetime as dt,json,os,time,urllib.error,urllib.request
from pathlib import Path
repo=os.environ.get("GITHUB_REPOSITORY","DownAirOnly/bogo")
token=os.environ["GH_TOKEN"]
url=f"https://api.github.com/repos/{repo}/contents/data/deals.json"
proposed=json.loads(Path("data/deals.json").read_text())
assert len(proposed["deals"])>=50
assert proposed["saleStart"]<proposed["saleEnd"]
def api(method,payload=None):
    req=urllib.request.Request(url,method=method,data=json.dumps(payload).encode() if payload else None,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"bogo-weekly-catalog"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
for attempt in range(5):
    remote=api("GET")
    current=json.loads(base64.b64decode(remote["content"]))
    if proposed["saleStart"]<=current.get("saleStart",""):
        print("Existing catalog is same week or newer; nothing to publish")
        break
    payload={"message":f"Publish validated BOGO deals for {proposed['saleStart']}",
             "sha":remote["sha"],"content":base64.b64encode((json.dumps(proposed,indent=2,ensure_ascii=False)+"\n").encode()).decode()}
    try:
        api("PUT",payload)
        print("Published",len(proposed["deals"]),"offers")
        break
    except urllib.error.HTTPError as e:
        if e.code not in (409,422) or attempt==4:raise
        time.sleep(attempt+2)
