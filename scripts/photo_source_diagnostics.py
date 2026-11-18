"""Brief, read-only diagnostics for public grocery photo search markup."""
import sys
from html.parser import HTMLParser
from urllib.parse import urlencode
import html
import json
from collections import Counter
from urllib.parse import urlparse
sys.path.insert(0, "scripts")
import build_product_photos as photo

PRODUCTS = [
    "Idahoan Mashed Potatoes",
    "Del Monte Vegetables",
    "Betty Crocker Brownie Mix",
    "Campbell's Cream Soup",
    "Hunt's Tomatoes",
    "Rotel Tomatoes",
]

class Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.alt = []
        self.bing = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img":
            source = a.get("src") or a.get("data-src") or ""
            label = a.get("alt") or a.get("aria-label") or a.get("title") or ""
            if source and ("gstatic" in source or "bing" in source or "google" in source):
                self.alt.append((label[:95], bool(photo.metadata_plausible(self.target, label))))
        if tag == "a" and a.get("m"):
            try:
                meta = json.loads(html.unescape(a["m"]))
                title = meta.get("t") or meta.get("desc") or a.get("title") or ""
                image = meta.get("turl") or ""
                if image:
                    self.bing.append((title[:95], bool(photo.metadata_plausible(self.target,title)), urlparse(image).hostname, photo.allowed_image(image), image))
            except Exception:
                pass

def check(q, provider):
    if provider == "google":
        url = "https://www.google.com/search?" + urlencode({
            "tbm":"isch","q":q+" grocery package product front","num":15,"safe":"active"
        })
    else:
        url = "https://www.bing.com/images/search?" + urlencode({
            "q":q+" grocery package front","first":1,"adlt":"strict"
        })
    try:
        body = photo.get(url,limit=1500000,timeout=8).decode("utf-8","ignore")
    except Exception as exc:
        print(q,provider,"fetch failed",type(exc).__name__,str(exc)[:80],flush=True)
        return
    p=Parse();p.target=q;p.feed(body)
    matches=p.alt if provider=="google" else p.bing
    if provider=="bing":
        print(q,provider,"total",len(matches),"acceptedTitles",sum(x[1] for x in matches),
              "allowHosts",sum(x[3] for x in matches),"hosts",dict(Counter(x[2] for x in matches)),
              "titles",[(a,b,c,d) for a,b,c,d,_ in matches[:5]],flush=True)
        chosen=[x for x in matches if x[1] and x[3]][:2]
        for x in chosen:
            try:
                data=photo.get(x[4],limit=2_000_000,timeout=6)
                print("IMG_PROBE",q,x[2],"bytes",len(data),flush=True)
            except Exception as e:
                print("IMG_PROBE",q,x[2],"FAILED",type(e).__name__,str(e)[:130],flush=True)
    else:
        print(q,provider,"candidates",len(matches),"titles",matches[:3],flush=True)

for q in PRODUCTS:
    for provider in ("google","bing"):
        check(q,provider)

# Separate apostrophe-free query to check why Hunt's is returning K-pop results.
check("Hunts Canned Tomatoes","bing")

import re
from urllib.parse import urlsplit

def ddg(q):
    term=q+" grocery food package"
    url="https://duckduckgo.com/?" + urlencode({"q":term,"iax":"images","ia":"images"})
    try:
        landing=photo.get(url,limit=800_000,timeout=8).decode("utf-8","ignore")
        vqd=re.search(r'vqd[=:" ]+([0-9-]+)',landing) or re.search(r'vqd=([0-9-]+)',landing)
        if not vqd:
            print("DDG",q,"landing",len(landing),"no vqd",re.findall(r"<title[^>]*>(.*?)</title>",landing,re.I|re.S)[:1],flush=True)
            return
        img_url="https://duckduckgo.com/i.js?"+urlencode({"q":term,"vqd":vqd.group(1),"o":"json","l":"us-en","p":"1"})
        body=photo.get(img_url,limit=2_000_000,timeout=8).decode("utf-8","ignore")
        data=json.loads(body)
        items=data.get("results") or []
        print("DDG",q,"results",len(items),"first",[(x.get("title","")[:80],urlsplit(x.get("thumbnail","")).hostname) for x in items[:5]],flush=True)
    except Exception as e:
        print("DDG",q,"FAILED",type(e).__name__,str(e)[:160],flush=True)

for q in ["Idahoan Mashed Potatoes","Del Monte Vegetables","Betty Crocker Brownie Mix","Hunts Canned Tomatoes","Rotel Tomatoes"]:
    ddg(q)
