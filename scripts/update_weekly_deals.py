#!/usr/bin/env python3
"""Guarded weekly Publix BOGO importer.

Discovers the current iHeartPublix weekly ad or accepts an explicit article URL.
Only publishes when a coherent, dated, substantial BOGO catalog is extracted.
"""
import argparse, datetime as dt, json, re, sys, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT="https://www.iheartpublix.com/"
CATALOG=Path("data/deals.json")
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.lines=[]; self.current=[]; self.href=None; self.skip=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("script","style","nav","footer"):self.skip+=1
        if tag=="a":self.href=a.get("href")
        if tag in ("p","li","h1","h2","h3","h4","br","div"):self.flush()
    def handle_endtag(self,tag):
        if tag in ("script","style","nav","footer"):self.skip=max(0,self.skip-1)
        if tag=="a":self.href=None
        if tag in ("p","li","h1","h2","h3","h4","div"):self.flush()
    def handle_data(self,data):
        if self.skip:return
        value=" ".join(data.split())
        if not value:return
        if self.href:self.links.append((value,self.href))
        self.current.append(value)
    def flush(self):
        value=" ".join(self.current).strip()
        if value:self.lines.append(value)
        self.current=[]
def fetch(url):
    if not url.startswith("https://www.iheartpublix.com/"):raise ValueError("Only iHeartPublix article URLs are supported")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; bogo-weekly-deals/1.0; personal catalog)","Accept":"text/html"})
    with urllib.request.urlopen(req,timeout=35) as response:
        if response.status!=200:raise ValueError("HTTP status "+str(response.status))
        data=response.read(4_000_000)
    p=Page();p.feed(data.decode("utf-8","replace"));p.flush();return p
def discover():
    p=fetch(ROOT)
    links=[]
    for label,url in p.links:
        if "publix-ad-coupons-week-of-" in url:
            links.append(urljoin(ROOT,url).split("?")[0])
    # Article titles are dated; never assume the first link is the current week.
    return list(dict.fromkeys(links))
def parse_dates(url):
    match=re.search(r"week-of-(\d{1,2})-(\d{1,2})-to-(\d{1,2})-(\d{1,2})",url)
    if not match:raise ValueError("Could not identify sale dates from article URL")
    m1,d1,m2,d2=map(int,match.groups())
    year=int(re.search(r"/(20\d{2})/",url).group(1))
    start=dt.date(year,m1,d1)
    end=dt.date(year+(m2<m1),m2,d2)
    if not (5<=(end-start).days<=8):raise ValueError("Unexpected sale length")
    return start,end
def parse(lines,start):
    offers=[];active=False;seen=set()
    categories=("Produce & Deli","Meat & Seafood","Dairy & Refrigerated","Frozen","Pantry","Snacks & Sweets","Beverages","Household & Personal Care")
    cat="Other"
    for line in lines:
        line=re.sub(r"\s+"," ",line).strip()
        if re.search(r"buy one get one free|\bBOGO\b",line,re.I):active=True
        if any(line.lower().startswith(x.lower()) for x in categories):cat=next(x for x in categories if line.lower().startswith(x.lower()))
        if not active or len(line)<12 or len(line)>450:continue
        if re.search(r"coupon|subscribe|advertis|printable|terms|privacy|comment",line,re.I):continue
        # Require explicit price; do not manufacture missing prices.
        match=re.search(r"\$\s*(\d+\.\d{2})(?:\s*[-–]\s*\$?\s*(\d+\.\d{2}))?",line)
        if not match:continue
        name=line[:match.start()].strip(" ,–:-")
        if len(name)<8 or len(name)>180:continue
        if re.search(r"\b(save|off|coupon|limit|each|regular price)\b",name,re.I):continue
        key=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
        if key in seen:continue
        seen.add(key)
        low=float(match.group(1));high=float(match.group(2) or match.group(1))
        if not (0.5<=low<=high<=150):continue
        offers.append({"id":"publix-"+start.isoformat()+"-"+key[:70],"category":cat,"name":name,
            "details":"","price":low if low==high else None,"priceMin":low,"priceMax":high,
            "priceLabel":match.group(1)+("–"+match.group(2) if match.group(2) else ""),
            "coupon":"","notes":"","searchQuery":name})
    return offers
def main():
    a=argparse.ArgumentParser();a.add_argument("--url",default="");a.add_argument("--min-offers",type=int,default=50);args=a.parse_args()
    existing=json.loads(CATALOG.read_text())
    candidates=[args.url] if args.url else discover()
    today=dt.datetime.now(dt.timezone.utc).date()
    for url in candidates:
        try:
            start,end=parse_dates(url)
            if not (start-dt.timedelta(days=5)<=today<=end):continue
            if start.isoformat()==existing.get("saleStart"):
                print("Already published",start);return
            page=fetch(url);deals=parse(page.lines,start)
            if len(deals)<args.min_offers:
                print(f"Rejected {url}: only {len(deals)} plausible offers (minimum {args.min_offers})")
                continue
            # Reuse cached photos only for identical normalized product names.
            old={re.sub(r"[^a-z0-9]+","-",x["name"].lower()).strip("-"):x for x in existing.get("deals",[])}
            for d in deals:
                match=old.get(re.sub(r"[^a-z0-9]+","-",d["name"].lower()).strip("-"))
                if match and match.get("image","").startswith("images/products/"):
                    for k in ("image","imageSource","imageVariant","imageStatus"):
                        if k in match:d[k]=match[k]
            updated={"updated":today.isoformat(),"saleStart":start.isoformat(),"saleEnd":end.isoformat(),
                     "sourceUrl":url,"source":"iHeartPublix weekly ad; automatically extracted (verify store prices)","deals":deals}
            CATALOG.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n")
            print("Prepared",len(deals),"offers for",start,"through",end);return
        except Exception as exc:print("Skipped",url,type(exc).__name__,str(exc)[:150])
    print("No validated new catalog; retaining existing data")
if __name__=="__main__":main()
