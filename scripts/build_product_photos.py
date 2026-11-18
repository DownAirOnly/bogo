#!/usr/bin/env python3
"""Automatically cache small real product photos during the Pages build.

Runs without keys or user actions. Uses public search thumbnails and Open Food
Facts; never treats a search match as a verified exact product variant.
Unavailable sources are skipped without interrupting site deployment.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import shutil
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from PIL import Image, ImageOps
import html
import json
import re

CATALOGS = [Path("data/current-deals.json"), Path("data/deals.json"), Path("data/next-deals.json")]
OUTPUT = Path("images/products")
INDEX_PATH = OUTPUT / "photo-index.json"
PHOTO_INDEX = {}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; bogo-product-photo/1.0; personal grocery guide)",
    "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
}
STOP = {"the", "and", "for", "with", "size", "pack", "products", "organic", "assorted", "variety"}
def photo_key(deal):
    # Preserve the complete product name; never merge different flavors
    # just because the first few words match.
    return " ".join(tokens(deal.get("name") or deal.get("searchQuery") or ""))

def valid_cached(path):
    try:
        path = Path(path)
        return path.is_file() and path.suffix == ".webp" and path.stat().st_size > 500
    except OSError:
        return False

def tokens(s):
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w)>2 and w not in STOP]
def query_for(d):
    s = (d.get("searchQuery") or d.get("name") or "").split(" — ")[0]
    s = re.split(r"\s+(?:or|and/or)\s+", s, maxsplit=1, flags=re.I)[0]
    s = re.split(r"[,;/]", s, maxsplit=1)[0]
    return re.sub(r"\([^)]*\)", "", s).strip()
def allowed_image(url):
    if not url or not isinstance(url, str): return False
    p = urlparse(url)
    if p.scheme != "https": return False
    host = (p.hostname or "").lower()
    return (host == "images.openfoodfacts.org" or
            bool(re.fullmatch(r"encrypted-tbn\d*\.gstatic\.com", host)) or
            bool(re.fullmatch(r"(?:tse|ts)\d*\.mm\.bing\.net", host)))
def get(url, limit=4_000_000, timeout=7):
    with urlopen(Request(url, headers=HEADERS), timeout=timeout) as response:
        if response.status != 200: raise ValueError("HTTP error")
        content = response.read(limit + 1)
        if len(content) > limit: raise ValueError("Large response")
        return content
def google_images(q):
    url = "https://www.google.com/search?" + urlencode({
        "tbm": "isch", "q": q + " product packaging", "num": 12, "safe": "active"
    })
    try: body = get(url, limit=1_500_000, timeout=6).decode("utf-8", errors="ignore")
    except Exception: return []
    body = html.unescape(body).replace(r"\u003d", "=").replace(r"\u0026", "&")
    class Pics(HTMLParser):
        def __init__(self): super().__init__(); self.items=[]
        def handle_starttag(self, tag, attrs):
            if tag != "img": return
            a = dict(attrs)
            for v in (a.get("src"), a.get("data-src")):
                if v and "gstatic.com/images?q=tbn:" in v and allowed_image(v):
                    self.items.append(v)
    parsed = Pics()
    try: parsed.feed(body)
    except Exception: pass
    urls = parsed.items + re.findall(
        r"https://encrypted-tbn\d*\.gstatic\.com/images\?q=tbn:[A-Za-z0-9_-]+",
        body
    )
    return list(dict.fromkeys(u for u in urls if allowed_image(u)))[:6]
class BingPics(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]
    def handle_starttag(self, tag, attrs):
        if tag != "a": return
        a = dict(attrs)
        m = a.get("m")
        if not m: return
        try:
            data = json.loads(html.unescape(m))
            u = data.get("turl", "")
            if allowed_image(u): self.items.append(u)
        except (ValueError, TypeError): pass
def bing_images(q):
    try:
        body = get("https://www.bing.com/images/search?" + urlencode({
            "q": q + " product packaging", "first": 1, "adlt": "strict"
        }), limit=1_500_000, timeout=6).decode("utf-8", errors="ignore")
        parser = BingPics(); parser.feed(body)
        return list(dict.fromkeys(parser.items))[:6]
    except Exception: return []
def barcode_images(d):
    """A known product barcode is more precise than a broad image search."""
    code = str(d.get("imageProductCode") or "").strip()
    if not re.fullmatch(r"\d{8,14}", code):
        return []
    try:
        url = "https://world.openfoodfacts.org/api/v2/product/" + code + ".json?" + urlencode({
            "fields": "image_front_url,image_url"
        })
        product = json.loads(get(url, timeout=6)).get("product", {})
        image = product.get("image_front_url") or product.get("image_url")
        return [image] if allowed_image(image) else []
    except Exception:
        return []

def food_facts_images(q):
    params = urlencode({
        "search_terms": q, "page_size": 20,
        "fields": "product_name,brands,image_front_url,image_url"
    })
    try:
        j = json.loads(get("https://world.openfoodfacts.org/api/v2/search?" + params, timeout=7))
    except Exception: return []
    wanted = tokens(q)
    found = []
    for product in j.get("products", []):
        url = product.get("image_front_url") or product.get("image_url") or ""
        if not allowed_image(url): continue
        have = tokens((product.get("brands") or "") + " " + (product.get("product_name") or ""))
        score = sum(w in have for w in wanted) / max(1, len(wanted))
        if score >= .45: found.append((score,url))
    found.sort(reverse=True)
    return list(dict.fromkeys(url for _,url in found))[:5]
def save_photo(url, dest):
    if not allowed_image(url): return False
    try:
        raw = get(url, timeout=8)
        with Image.open(BytesIO(raw)) as source:
            if min(source.size) < 72 or max(source.size) / min(source.size) > 3.5:
                return False  # Tiny badges and extreme banners are not useful product photos.
            photo = ImageOps.exif_transpose(source).convert("RGBA")
            photo.thumbnail((420, 420), Image.Resampling.LANCZOS)
            background = Image.new("RGB", photo.size, "white")
            background.paste(photo, mask=photo.getchannel("A"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = dest.with_suffix(".tmp.webp")
            background.save(temp, "WEBP", quality=82, method=4)
            temp.replace(dest)
        return True
    except Exception:
        return False
def build(d):
    ident = re.sub(r"[^A-Za-z0-9_-]", "-", str(d.get("id", "")))[:85]
    if not ident: return "skipped"
    target = OUTPUT / (ident + ".webp")
    if valid_cached(target): return "existing"
    key = photo_key(d)
    cached_name = PHOTO_INDEX.get(key, "")
    # Restore a previously found photo when the weekly deal ID changes.
    if cached_name and re.fullmatch(r"[A-Za-z0-9_-]+\.webp", cached_name):
        cached = OUTPUT / cached_name
        if cached != target and valid_cached(cached):
            try:
                shutil.copyfile(cached, target)
                return "reused"
            except OSError:
                pass
    q = query_for(d)
    if not q: return "missing"
    # First use the top Google image result, as requested; search public
    # packaged-food data and Bing thumbnails when Google cannot serve it.
    for url in barcode_images(d):
        if save_photo(url, target): return "saved"
    for finder in (google_images, food_facts_images, bing_images):
        for url in finder(q):
            if save_photo(url, target): return "saved"
    return "missing"
def main():
    deals_by_id = {}
    for path in CATALOGS:
        if path.exists():
            for deal in json.loads(path.read_text(encoding="utf-8")).get("deals", []):
                deals_by_id[str(deal.get("id", ""))] = deal
    deals = list(deals_by_id.values())
    if not deals: return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    global PHOTO_INDEX
    try:
        previous = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        PHOTO_INDEX = previous if isinstance(previous, dict) else {}
    except (OSError, ValueError):
        PHOTO_INDEX = {}
    # Seed index from legacy/local image files in the current catalog.
    for deal in deals:
        key = photo_key(deal)
        filename = re.sub(r"[^A-Za-z0-9_-]", "-", str(deal.get("id", "")))[:85] + ".webp"
        if key and valid_cached(OUTPUT / filename):
            PHOTO_INDEX[key] = filename
    counts = {"saved":0, "existing":0, "reused":0, "missing":0, "skipped":0}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(build, deal) for deal in deals]
        for f in as_completed(futures):
            try: counts[f.result()] += 1
            except Exception as exc:
                print("Photo lookup error:", str(exc)[:120])
                counts["missing"] += 1
    # Save only validated paths, not failed search URLs, for future deployments.
    for deal in deals:
        key = photo_key(deal)
        filename = re.sub(r"[^A-Za-z0-9_-]", "-", str(deal.get("id", "")))[:85] + ".webp"
        if key and valid_cached(OUTPUT / filename):
            PHOTO_INDEX[key] = filename
    PHOTO_INDEX = {
        key: filename for key, filename in PHOTO_INDEX.items()
        if re.fullmatch(r"[A-Za-z0-9_-]+\.webp", filename) and valid_cached(OUTPUT / filename)
    }
    INDEX_PATH.write_text(json.dumps(PHOTO_INDEX, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Automatic product photos:", counts)
if __name__ == "__main__":
    main()
