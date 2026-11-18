#!/usr/bin/env python3
"""Validate and cache sourced product images for static GitHub Pages hosting.

This verifies file format, dimensions, and successful retrieval, not that the
packaging is an exact match for every product variant.
"""
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps

catalog_path = Path("data/deals.json")
catalog = json.loads(catalog_path.read_text())
target_dir = Path("images/products")
target_dir.mkdir(parents=True, exist_ok=True)
allowed_hosts = {
    "images.openfoodfacts.org",
    "www.instacart.com",
    "s7d9.scene7.com",
    "www.kroger.com",
}
cached = 0
unavailable = 0
for deal in catalog["deals"]:
    url = deal.get("image")
    if not url or url.startswith("images/products/"):
        continue
    host = urllib.parse.urlparse(url).hostname
    if host not in allowed_hosts or not url.startswith("https://"):
        deal.pop("image", None)
        deal["imageStatus"] = "unverified-source"
        unavailable += 1
        continue
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", str(deal["id"]))[:85]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bogo/1.0 (personal grocery deals guide)", "Accept": "image/*"})
        with urllib.request.urlopen(req, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
            if not content_type.startswith("image/"):
                raise ValueError("Not an image response")
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Image exceeds size limit")
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            if im.width < 100 or im.height < 100:
                raise ValueError("Image too small")
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((640, 640))
            output = target_dir / (slug + ".webp")
            im.save(output, "WEBP", quality=84, method=5)
        deal["image"] = output.as_posix()
        deal["imageStatus"] = "cached"
        cached += 1
    except Exception as exc:
        # Do not ship a remote URL that may fail or expand over the card.
        deal.pop("image", None)
        deal["imageStatus"] = "unavailable"
        print(f"Unavailable {deal['name']}: {type(exc).__name__}: {str(exc)[:110]}")
        unavailable += 1
    time.sleep(0.15)
catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
print(f"Cached {cached} product photos; {unavailable} unavailable")
