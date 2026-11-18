"""Brief, read-only diagnostics for public grocery photo search markup."""
import sys
from html.parser import HTMLParser
from urllib.parse import urlencode
import html
import json
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
                    self.bing.append((title[:95], bool(photo.metadata_plausible(self.target,title))))
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
    print(q,provider,"html_bytes",len(body),"candidates",len(matches),
          "accepted",sum(ok for _,ok in matches),"titles",matches[:7],flush=True)

for q in PRODUCTS:
    for provider in ("google","bing"):
        check(q,provider)
