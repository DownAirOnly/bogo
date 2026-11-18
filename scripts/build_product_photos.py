#!/usr/bin/env python3
"""Build only barcode-identified or brand-and-item-matched packaging photos.

Inaccurate search thumbnails must never be presented as product images.
Outputs to a new cache directory, avoiding all unverified historical photos.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import shutil
from urllib.parse import urlencode, urlparse
from html.parser import HTMLParser
import html
from urllib.request import Request, urlopen
from PIL import Image, ImageOps
import json
import re

CATALOGS = [Path("data/current-deals.json"), Path("data/deals.json"), Path("data/next-deals.json")]
OUTPUT = Path("images/verified-products")
INDEX_PATH = OUTPUT / "photo-index.json"
PHOTO_INDEX = {}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; bogo-product-photo/1.0; personal grocery guide)",
    "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
}
STOP = {"the", "and", "for", "with", "size", "pack", "products",
        "organic", "assorted", "variety", "flavor", "flavored", "select"}
REJECT = {"recipe", "recipes", "casserole", "casseroles", "game", "gaming",
          "showdown", "wallpaper", "screenshot", "logo", "poster",
          "artwork", "drawing", "template", "illustration", "sticker",
          "ribbon", "sports", "football", "baseball", "sponsored"}
def tokens(s):
    words = re.findall(r"[a-z0-9]+", (s or "").lower())
    words = [w for w in words if len(w) > 2 and w not in STOP]
    result = []
    for word in words:
        # Plural normalization handles "tomatoes" and "vegetables" without
        # permissive substring matches ("Hunt" matching "hunting").
        if word.endswith("ies") and len(word) > 5:
            word = word[:-3] + "y"
        elif word.endswith("oes") and len(word) > 5:
            word = word[:-2]
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 4:
            word = word[:-1]
        if word not in result:
            result.append(word)
    return result

def query_for(d):
    s = (d.get("searchQuery") or d.get("name") or "").split(" — ")[0]
    s = re.split(r"\s+(?:or|and/or)\s+", s, maxsplit=1, flags=re.I)[0]
    s = re.split(r"[,;/]", s, maxsplit=1)[0]
    return re.sub(r"\([^)]*\)", "", s).strip()

def photo_key(deal):
    return " ".join(tokens(deal.get("name") or deal.get("searchQuery") or ""))

def valid_cached(path):
    try:
        path = Path(path)
        return path.is_file() and path.suffix == ".webp" and path.stat().st_size > 500
    except OSError:
        return False

def plausible_product_match(query, brand, product_name):
    wanted = tokens(query)
    have_brand = set(tokens(brand))
    have_name = set(tokens(product_name))
    have = have_brand | have_name
    # Only trust matches with a real brand and specific item nouns.
    # A "Hunt" game screenshot, "Del" logo, or tomato recipe fails.
    if len(wanted) < 2 or len(have) < 2:
        return False
    if any(word in REJECT for word in tokens(product_name)):
        return False
    if wanted[0] not in have:
        return False
    # The packaging/product listing must contain the brand and product type.
    return all(word in have for word in wanted[:min(len(wanted), 4)])

def allowed_image(url):
    if not url or not isinstance(url, str): return False
    p = urlparse(url)
    if p.scheme != "https": return False
    host = (p.hostname or "").lower()
    return (host == "images.openfoodfacts.org" or host == "th.bing.com" or
            bool(re.fullmatch(r"encrypted-tbn\d*\.gstatic\.com", host)) or
            bool(re.fullmatch(r"(?:tse|ts)\d*\.mm\.bing\.net", host)))

def get(url, limit=4_000_000, timeout=7):
    with urlopen(Request(url, headers=HEADERS), timeout=timeout) as response:
        if response.status != 200: raise ValueError("HTTP error")
        content = response.read(limit + 1)
        if len(content) > limit: raise ValueError("Large response")
        return content

def barcode_images(d):
    """Use a known exact barcode when available."""
    code = str(d.get("imageProductCode") or "").strip()
    if not re.fullmatch(r"\d{8,14}", code):
        return []
    try:
        url = "https://world.openfoodfacts.org/api/v2/product/" + code + ".json?" + urlencode({
            "fields": "product_name,brands,image_front_url,image_url"
        })
        product = json.loads(get(url, timeout=4)).get("product", {})
        image = product.get("image_front_url") or product.get("image_url")
        return [image] if allowed_image(image) else []
    except Exception:
        return []

def food_facts_images(q):
    # We deliberately do not publish anonymous Google or Bing image
    # thumbnails. A readable thumbnail alone proves nothing about the product.
    params = urlencode({
        "search_terms": q, "page_size": 30,
        "fields": "product_name,product_name_en,brands,image_front_url,image_url"
    })
    try:
        j = json.loads(get("https://world.openfoodfacts.org/api/v2/search?" + params, timeout=4))
    except Exception: return []
    found = []
    for product in j.get("products", []):
        label = (product.get("product_name_en") or product.get("product_name") or "")
        brand = product.get("brands") or ""
        if not plausible_product_match(q, brand, label): continue
        url = product.get("image_front_url") or product.get("image_url") or ""
        if allowed_image(url): found.append(url)
    return list(dict.fromkeys(found))[:4]


def metadata_plausible(q, title):
    label = html.unescape(str(title or "")).strip()
    if len(label) < 10 or len(label) > 260:
        return False
    if re.search(r"^(?:image result for|search results for|google images|bing images)\b", label, re.I):
        return False
    return plausible_product_match(q, "", label)

def google_labeled_images(q):
    """Only thumbnails with independently supplied relevant result titles."""
    url = "https://www.google.com/search?" + urlencode({
        "tbm": "isch", "q": q + " grocery can package product front", "num": 20, "safe": "active"
    })
    try:
        body = get(url, limit=1_500_000, timeout=4).decode("utf-8", "ignore")
    except Exception:
        return []
    class Results(HTMLParser):
        def __init__(self): super().__init__(); self.images=[]
        def handle_starttag(self, tag, attrs):
            if tag != "img": return
            a = dict(attrs)
            label = a.get("alt") or a.get("aria-label") or a.get("title") or ""
            if not metadata_plausible(q, label): return
            for field in ("data-src", "src"):
                image_url = html.unescape(a.get(field) or "")
                if allowed_image(image_url):
                    self.images.append(image_url)
                    return
    parser = Results()
    try: parser.feed(body)
    except Exception: return []
    return list(dict.fromkeys(parser.images))[:5]

def bing_labeled_images(q):
    """Require the actual Bing result title, never an unlabeled thumbnail."""
    url = "https://www.bing.com/images/search?" + urlencode({
        "q": q + " grocery can package front", "first": 1, "adlt": "strict"
    })
    try:
        body = get(url, limit=1_500_000, timeout=4).decode("utf-8", "ignore")
    except Exception:
        return []
    class Results(HTMLParser):
        def __init__(self): super().__init__(); self.images=[]
        def handle_starttag(self, tag, attrs):
            if tag != "a": return
            a = dict(attrs)
            if not a.get("m"): return
            try:
                meta = json.loads(html.unescape(a["m"]))
            except (TypeError, ValueError):
                return
            title = meta.get("t") or meta.get("desc") or a.get("title") or ""
            url = meta.get("turl") or ""
            if metadata_plausible(q, title) and allowed_image(url):
                self.images.append(url)
    parser = Results()
    try: parser.feed(body)
    except Exception: return []
    return list(dict.fromkeys(parser.images))[:5]

def save_photo(url, dest):
    if not allowed_image(url): return False
    try:
        raw = get(url, timeout=5)
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
    # Known barcode, structured product metadata, then public image-search
    # thumbnails ONLY when the result's title names the brand and product.
    for finder in (barcode_images, food_facts_images, google_labeled_images, bing_labeled_images):
        candidates = finder(d) if finder is barcode_images else finder(q)
        for url in candidates:
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
    with ThreadPoolExecutor(max_workers=10) as pool:
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
