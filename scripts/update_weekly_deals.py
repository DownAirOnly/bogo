#!/usr/bin/env python3
"""Automatically discover and stage dated Publix BOGO advertisements.

The main catalog remains untouched if extraction fails. When a genuinely newer
ad is published ahead of its sale week it is staged as next-deals.json. During
the sale week it is promoted to deals.json. No manual action is required.
"""
import argparse
import datetime as dt
import json
import hashlib
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = "https://www.iheartpublix.com/"
ARTICLE_CACHE = {}
MAIN = Path("data/deals.json")
NEXT = Path("data/next-deals.json")
PREVIOUS = Path("data/previous-deals.json")
ARTICLE = re.compile(r"/20\d\d/\d\d/publix-ad-coupons-week-of-\d{1,2}-\d{1,2}-to-\d{1,2}-\d{1,2}", re.I)
BOGO = re.compile(r"\bBOGO\b|\bbuy\s+one\s+get\s+one\s+free\b", re.I)
PRICE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)(?:\s*[-–—]\s*\$?\s*(\d+(?:\.\d{1,2})?))?", re.I)
NO_PRICE = re.compile(r"no\s+price\s+(?:listed|given)|price\s+(?:not\s+listed|varies)", re.I)
CATEGORY_NAMES = (
    "Frozen Foods", "Pantry, Snacks & Drinks", "Dairy & Refrigerated",
    "Produce & Deli", "Meat & Seafood", "Home, Health & Cleaning",
    "Beer, Wine & Alternatives",
)

class HTMLLines(HTMLParser):
    """Retain text blocks and links without JavaScript, ads, nav or footer."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.links, self.parts = [], [], []
        self.skip = 0
        self.skip_tags = {"script", "style", "nav", "footer", "noscript", "svg"}
        self.block_tag = "text"
    def flush(self):
        text = " ".join(self.parts).strip()
        if text:
            self.blocks.append((self.block_tag, re.sub(r"\s+", " ", text)))
        self.parts = []
        self.block_tag = "text"
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.skip_tags:
            self.flush()
            self.skip += 1
        if self.skip:
            return
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "br", "tr"):
            self.flush()
            self.block_tag = tag
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "br", "tr", "div"):
            self.flush()
    def handle_data(self, data):
        if self.skip:
            return
        value = " ".join(data.split())
        if value:
            self.parts.append(value)

def get(url, timeout=25):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.iheartpublix.com":
        raise ValueError("Only public iHeartPublix URLs are allowed")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; bogo-weekly/2.0; personal ad viewer)",
        "Accept": "text/html,application/rss+xml,application/json,application/xml;q=0.9,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("Unexpected HTTP status")
        return response.read(5_000_000).decode("utf-8", "replace")

def read_catalog(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data.get("deals"), list) and data.get("saleStart") and data.get("saleEnd"):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return None

def sale_dates(url):
    match = re.search(r"/(20\d\d)/\d\d/publix-ad-coupons-week-of-(\d{1,2})-(\d{1,2})-to-(\d{1,2})-(\d{1,2})", url, re.I)
    if not match:
        raise ValueError("Unrecognized ad dates")
    year, m1, d1, m2, d2 = map(int, match.groups())
    start = dt.date(year, m1, d1)
    end = dt.date(year + int(m2 < m1), m2, d2)
    if not 5 <= (end - start).days <= 8:
        raise ValueError("Sale window must be roughly one week")
    return start, end

def discover():
    """Try multiple public discovery surfaces so a stale homepage isn't fatal."""
    links = []
    for path in ("", "publix-ads-coupons/", "feed/"):
        try:
            raw = get(urljoin(ROOT, path), timeout=14)
            if path == "feed/":
                try:
                    root = ET.fromstring(raw)
                    for item in root.findall(".//item"):
                        link = item.findtext("link", "").strip()
                        if link:
                            links.append(link)
                            html = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
                            if html:
                                ARTICLE_CACHE[link.split("?")[0]] = html
                except ET.ParseError:
                    pass
            page = HTMLLines()
            page.feed(raw)
            links += page.links
        except (OSError, ValueError, urllib.error.URLError) as exc:
            print("Discovery source unavailable:", path or "homepage", str(exc)[:100])
    # WP REST is optional; not every WordPress site exposes it.
    try:
        raw = get(urljoin(ROOT, "wp-json/wp/v2/posts?per_page=30&_fields=link,content"), timeout=12)
        for post in json.loads(raw):
            if not isinstance(post, dict):
                continue
            url = post.get("link", "")
            if url:
                links.append(url)
                body = post.get("content", {})
                if isinstance(body, dict) and isinstance(body.get("rendered"), str):
                    ARTICLE_CACHE[url.split("?")[0]] = body["rendered"]
    except (OSError, ValueError, urllib.error.URLError):
        pass
    valid = []
    for raw_url in links:
        url = urljoin(ROOT, raw_url or "").split("#")[0].split("?")[0]
        if not ARTICLE.search(url) or not url.startswith(ROOT):
            continue
        try:
            start, _ = sale_dates(url)
        except ValueError:
            continue
        valid.append((start, url))
    return [url for _, url in sorted(set(valid), reverse=True)]

def category_heading(line, previous):
    s = re.sub(r"[^a-z ]", " ", line.lower()).strip()
    if not 2 <= len(s) <= 65:
        return previous
    if "wine" in s or "beer" in s or "alcohol" in s or "liquor" in s:
        return "Beer, Wine & Alternatives"
    if "frozen" in s:
        return "Frozen Foods"
    if any(x in s for x in ("dairy", "refrigerated", "cheese and yogurt")):
        return "Dairy & Refrigerated"
    if "produce" in s or s == "deli":
        return "Produce & Deli"
    if "meat" in s or "seafood" in s:
        return "Meat & Seafood"
    if any(x in s for x in ("health", "beauty", "cleaning", "household", "non food", "personal care")):
        return "Home, Health & Cleaning"
    if any(x in s for x in ("grocery", "snacks", "beverages", "pantry", "bakery", "breakfast")):
        return "Pantry, Snacks & Drinks"
    return previous

def normalized_name(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def category_for(name, suggested, known):
    """Use existing matches and recognizable grocery terms before generic pantry."""
    key = normalized_name(name)
    if key in known:
        return known[key]
    words = key.split("-")
    if len(words) >= 3:
        prefix = "-".join(words[:3])
        matching = {cat for old, cat in known.items() if old.startswith(prefix)}
        if len(matching) == 1:
            return next(iter(matching))
    text = name.lower()
    def has(*terms):
        return any(re.search(r"\b" + re.escape(t) + r"\b", text) for t in terms)
    if has("wine", "beer", "ale", "lager", "prosecco", "sauvignon", "chardonnay",
           "cabernet", "merlot", "pinot", "vodka", "gin", "cocktail", "hard seltzer"):
        return "Beer, Wine & Alternatives"
    if has("laundry", "detergent", "dish soap", "tissue", "paper towel", "toilet paper",
           "cleaner", "deodorant", "shampoo", "conditioner", "body wash", "razor",
           "mouthwash", "toothpaste", "diaper", "fabric softener", "dog food", "cat food"):
        return "Home, Health & Cleaning"
    if has("frozen", "ice cream", "pizza rolls", "freezer", "french fries", "phyllo",
           "pot pie", "skillet meals", "gelato", "sorbetto", "puff pastry",
           "frozen dessert", "meatless meatballs", "appetizers", "tater tots",
           "totino", "ore-ida", "birds eye", "breyers", "haagen-dazs", "talenti",
           "cool whip", "good humor", "edwards", "marie callender"):
        return "Frozen Foods"
    if has("milk", "yogurt", "cheese", "butter", "cream cheese", "sour cream",
           "creamer", "cottage cheese", "refrigerated", "eggs", "kefir"):
        return "Dairy & Refrigerated"
    if has("shrimp", "salmon", "tilapia", "steak", "beef", "pork", "chicken breast",
           "bacon", "sausage", "kielbasa", "turkey breast", "ground turkey",
           "ribeye", "meatballs", "salami", "hot dogs"):
        return "Meat & Seafood"
    if has("salad", "lettuce", "arugula", "baby spinach", "fresh berries", "tomatoes",
           "grapes", "apples", "watermelon", "avocado", "hummus", "deli", "fresh fruit"):
        return "Produce & Deli"
    return suggested if suggested in CATEGORY_NAMES else "Pantry, Snacks & Drinks"

def previous_categories(*catalogs):
    return {
        normalized_name(d["name"]): d["category"]
        for catalog in catalogs if catalog
        for d in catalog.get("deals", [])
        if d.get("name") and d.get("category") in CATEGORY_NAMES
    }

def parse_offers(blocks, start, known=None):
    offers, seen = [], set()
    known = known or {}
    category = "Pantry, Snacks & Drinks"
    in_bogos = False
    for kind, raw in blocks:
        line = re.sub(r"\s+", " ", raw).strip()
        if line.upper() in ("BOGOS", "BOGO DEALS", "BUY ONE GET ONE FREE"):
            in_bogos = True
            continue
        if in_bogos and kind in ("h1", "h2", "h3") and line.upper() in ("MEAT", "SEAFOOD", "GROCERY", "PRODUCE", "DAIRY"):
            break
        if not in_bogos:
            continue
        if kind in ("h1", "h2", "h3", "h4") or (len(line) < 45 and not BOGO.search(line)):
            category = category_heading(line, category)
        if not (12 <= len(line) <= 450 and BOGO.search(line)):
            continue
        line = re.sub(r"\bAdd to Shopping List\b", "", line, flags=re.I).strip()
        if re.search(r"subscribe|privacy policy|leave a comment|printable coupon|advertisement", line, re.I):
            # Coupon blocks often mention BOGO; never treat them as deal lines.
            continue
        bogo = BOGO.search(line)
        prefix = line[:bogo.start()].strip(" \t,;:–—-*✓✔")
        if len(prefix) < 5 or len(prefix) > 240:
            continue
        if re.search(r"^(?:save|off|coupon|limit|buy|view|click|see|regular price)\b", prefix, re.I):
            continue
        rest = line[bogo.end():]
        match = PRICE.search(rest[:65]) if not NO_PRICE.search(rest[:65]) else None
        if not match and not NO_PRICE.search(rest[:65]):
            continue
        low = float(match.group(1)) if match else None
        high = float(match.group(2) or match.group(1)) if match else None
        if low is not None and not (0.49 <= low <= high <= 150):
            continue
        unit = "/lb" if re.search(r"/\s*lb\b|per\s+(?:pound|lb)\b", rest, re.I) else ""
        # Remove bullet/checkmark prefixes but leave all product/variant text intact.
        name = re.sub(r"^[\W_]+", "", prefix, flags=re.UNICODE).strip()
        if not 5 <= len(name) <= 220:
            continue
        key = normalized_name(name)
        if not key or key in seen:
            continue
        seen.add(key)
        label = (f"{low:.2f}" + (f"–{high:.2f}" if high != low else "") + unit) if match else ""
        offers.append({
            "id": "publix-" + key[:60] + "-" + hashlib.sha1(key.encode()).hexdigest()[:10],
            "category": category_for(name, category, known),
            "name": name,
            "details": "",
            "price": low if low == high else None,
            "priceMin": low, "priceMax": high, "priceLabel": label,
            "coupon": "", "notes": "", "searchQuery": name,
        })
    return offers

def validate(offers, minimum):
    if len(offers) < minimum:
        raise ValueError(f"Only {len(offers)} BOGO lines (minimum {minimum})")
    paid = sum(d["priceMin"] is not None for d in offers)
    if paid / len(offers) < 0.75:
        raise ValueError(f"Only {paid} of {len(offers)} offers have prices")
    # A partial section should not replace a complete 150-item catalog.
    if len({x["category"] for x in offers}) < 3:
        raise ValueError("Fewer than three grocery categories found")

def carry_image_fields(offers, *catalogs):
    old = {
        normalized_name(d["name"]): d
        for catalog in catalogs if catalog
        for d in catalog.get("deals", [])
        if d.get("name")
    }
    for deal in offers:
        previous = old.get(normalized_name(deal["name"]))
        if previous:
            for key in ("image", "imageSource", "imageVariant", "imageStatus", "imageProductCode"):
                if previous.get(key):
                    deal[key] = previous[key]

def stage(path, candidate):
    existing = read_catalog(path)
    if existing and existing.get("saleStart", "") >= candidate["saleStart"]:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Staged", path, candidate["saleStart"], len(candidate["deals"]), "offers")
    return True

def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--url", default="", help="Optional public article URL for troubleshooting")
    arg.add_argument("--min-offers", type=int, default=50)
    arg.add_argument("--today", default="", help="YYYY-MM-DD, for local tests")
    args = arg.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
    main = read_catalog(MAIN)
    upcoming = read_catalog(NEXT)
    if not main:
        raise SystemExit("No valid baseline catalog; refusing to replace user data")

    # Promote a verified preview when its Thursday sale date has arrived.
    if upcoming and dt.date.fromisoformat(upcoming["saleStart"]) <= today:
        if upcoming["saleStart"] > main["saleStart"]:
            stage(PREVIOUS, main)
            stage(MAIN, upcoming)
            main = upcoming

    urls = [args.url] if args.url else discover()
    for url in urls:
        try:
            start, end = sale_dates(url)
            if not today - dt.timedelta(days=10) <= start <= today + dt.timedelta(days=14):
                continue
            if start.isoformat() <= main["saleStart"]:
                continue
            if start > today and upcoming and start.isoformat() <= upcoming["saleStart"]:
                continue
            article = HTMLLines()
            try:
                body = get(url)
            except (OSError, ValueError, urllib.error.URLError):
                body = ARTICLE_CACHE.get(url, "")
                if not body:
                    raise
                print("Using public feed/API article content for", url)
            article.feed(body)
            article.flush()
            offers = parse_offers(article.blocks, start, previous_categories(main, upcoming))
            validate(offers, args.min_offers)
            carry_image_fields(offers, main, upcoming)
            snapshot = {
                "updated": today.isoformat(), "saleStart": start.isoformat(),
                "saleEnd": end.isoformat(), "sourceUrl": url,
                "source": "iHeartPublix weekly ad; automatically extracted; local prices may vary",
                "deals": offers,
            }
            if start > today and today <= dt.date.fromisoformat(main["saleEnd"]):
                stage(NEXT, snapshot)
            else:
                if snapshot["saleStart"] > main["saleStart"]:
                    stage(PREVIOUS, main)
                stage(MAIN, snapshot)
                main = snapshot
            return
        except Exception as exc:
            print("Rejected ad", url, type(exc).__name__, str(exc)[:150])
    print("No validated newer ad. Existing catalogs retained.")

if __name__ == "__main__":
    main()
