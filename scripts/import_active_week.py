#!/usr/bin/env python3
"""Import a verified, older-or-current weekly BOGO ad into its own catalog.

This is intentionally separate from the rolling future-week updater. It
never modifies data/deals.json or data/next-deals.json.
"""
import argparse
import datetime as dt
import json
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit

import update_weekly_deals as weekly

DEST = Path("data/current-deals.json")
DEFAULT_URL = ("https://www.iheartpublix.com/2026/11/"
               "publix-ad-coupons-week-of-11-12-to-11-18-11-11-to-11-17-for-some/")


def import_week(url, minimum=50):
    start, end = weekly.sale_dates(url)
    if not (dt.date(2026, 11, 12) <= start <= dt.date(2026, 11, 18)):
        raise ValueError("This one-time import accepts only the November 12–18 sale week")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.iheartpublix.com":
        raise ValueError("Unrecognized public source")

    try:
        html = weekly.get(url, timeout=25)
        fetched = "public article"
    except (OSError, urllib.error.URLError, ValueError):
        weekly.discover()
        html = weekly.ARTICLE_CACHE.get(url.rstrip("/") + "/", "") or weekly.ARTICLE_CACHE.get(url, "")
        if not html:
            raise RuntimeError("Unable to retrieve complete article or feed text")
        fetched = "public feed/API fallback"

    page = weekly.HTMLLines()
    page.feed(html)
    page.flush()
    saved = [weekly.read_catalog(p) for p in (
        weekly.MAIN, weekly.NEXT, DEST)]
    offers = weekly.parse_offers(page.blocks, start, weekly.previous_categories(*saved))
    weekly.validate(offers, minimum)
    weekly.carry_image_fields(offers, *saved)

    data = {
        "updated": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "saleStart": start.isoformat(),
        "saleEnd": end.isoformat(),
        "sourceUrl": url,
        "source": "iHeartPublix weekly ad; automatically extracted; local prices may vary",
        "deals": offers,
    }
    old = weekly.read_catalog(DEST)
    if old and old["saleStart"] >= data["saleStart"]:
        print("Existing same/newer current-week snapshot retained")
        return
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("CURRENT_WEEK_READY " + json.dumps({
        "saleStart": data["saleStart"], "saleEnd": data["saleEnd"],
        "count": len(offers),
        "priced": sum(x["priceMin"] is not None for x in offers),
        "source": fetched,
        "file": str(DEST)
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--min-offers", type=int, default=50)
    args = parser.parse_args()
    import_week(args.url, args.min_offers)
