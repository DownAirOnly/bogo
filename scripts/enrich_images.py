#!/usr/bin/env python3
"""Conservative image enrichment from Open Food Facts. Uncertain matches stay blank."""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

path = Path("data/deals.json")
catalog = json.loads(path.read_text())
deals = catalog.get("deals", [])
def tokens(s):
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {"the", "and", "or", "of", "oz", "size", "products", "assorted"}
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"bogo-deals/0.1 (noncommercial personal shopping catalog; OpenFoodFacts)"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)
updated = 0
for deal in deals:
    if deal.get("image") or deal.get("category") == "Beer, Wine & Alternatives":
        continue
    query = deal.get("searchQuery") or deal["name"]
    if re.search(r"\bor\b|/", query, re.I):
        continue  # Multiple variants: one photo could be misleading.
    try:
        params = urllib.parse.urlencode({"search_terms":query,"search_simple":1,"action":"process","json":1,"page_size":5,"fields":"product_name,brands,image_front_url,image_url,code"})
        data = get("https://world.openfoodfacts.org/cgi/search.pl?" + params)
        wanted = tokens(query)
        candidates = []
        for product in data.get("products", []):
            name = product.get("product_name") or ""
            photo = product.get("image_front_url") or product.get("image_url")
            found = tokens(name + " " + (product.get("brands") or ""))
            if not photo or not wanted or len(wanted) < 2:
                continue
            coverage = len(wanted & found) / len(wanted)
            if coverage >= 0.85:
                candidates.append((coverage, product))
        if len(candidates) == 1 or (len(candidates)>1 and sorted(candidates,key=lambda x:-x[0])[0][0] > sorted(candidates,key=lambda x:-x[0])[1][0]+0.12):
            product = max(candidates,key=lambda x:x[0])[1]
            deal["image"] = product.get("image_front_url") or product.get("image_url")
            deal["imageSource"] = "Open Food Facts"
            deal["imageProductCode"] = product.get("code")
            updated += 1
    except Exception as exc:
        print("Skipping", query, type(exc).__name__, str(exc)[:120])
    time.sleep(0.4)
if updated:
    path.write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+"\n")
print(f"Matched {updated} of {len(deals)} products; uncertain photos left blank")
