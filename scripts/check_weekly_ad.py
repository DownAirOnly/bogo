#!/usr/bin/env python3
"""Read-only live weekly-ad diagnostic. NEVER writes to published deal files.

Used to distinguish an accessible, parseable ad from source-side blocking,
incomplete markup and missing offers. Use the same parser and validators
as the scheduled importer, but do not reject older/same-week dates.
"""
import argparse
import json
import urllib.error

from scripts import update_weekly_deals as weekly


def check(url, minimum):
    start, end = weekly.sale_dates(url)
    result = {
        "mode": "read-only", "url": url,
        "saleStart": start.isoformat(), "saleEnd": end.isoformat(),
        "minimum": minimum, "retrievedBy": None,
    }
    try:
        body = weekly.get(url, timeout=20)
        result["retrievedBy"] = "public article"
    except (OSError, ValueError, urllib.error.URLError) as error:
        result["directFetchError"] = f"{type(error).__name__}: {error}"
        # The normal importer can discover complete article content via
        # RSS or WordPress APIs even when the article page blocks requests.
        weekly.discover()
        body = weekly.ARTICLE_CACHE.get(url.rstrip("/") + "/", "") or weekly.ARTICLE_CACHE.get(url, "")
        if not body:
            result["status"] = "BLOCKED: direct page and feed/API fallback unavailable"
            print("WEEKLY_AD_CHECK " + json.dumps(result, ensure_ascii=False))
            return 2
        result["retrievedBy"] = "public feed/API fallback"
    page = weekly.HTMLLines()
    page.feed(body)
    page.flush()
    headings = [txt[:90] for tag, txt in page.blocks if tag in ("h1", "h2", "h3")]
    offers = weekly.parse_offers(page.blocks, start)
    result["offersParsed"] = len(offers)
    result["offersPriced"] = sum(d["priceMin"] is not None for d in offers)
    result["categories"] = sorted(set(d["category"] for d in offers))
    result["sampleNames"] = [d["name"] for d in offers[:5]]
    try:
        weekly.validate(offers, minimum)
    except ValueError as error:
        result["status"] = "INCOMPLETE: " + str(error)
        result["headingsSeen"] = headings[:20]
        print("WEEKLY_AD_CHECK " + json.dumps(result, ensure_ascii=False))
        return 1
    result["status"] = "PASS"
    print("WEEKLY_AD_CHECK " + json.dumps(result, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=(
        "https://www.iheartpublix.com/2026/11/"
        "publix-ad-coupons-week-of-11-12-to-11-18-11-11-to-11-17-for-some/"
    ))
    parser.add_argument("--min-offers", type=int, default=50)
    args = parser.parse_args()
    raise SystemExit(check(args.url, args.min_offers))


if __name__ == "__main__":
    main()
