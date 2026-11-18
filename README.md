# bogo.

Mobile-first Publix BOGO browser and installed iPhone PWA, published on GitHub Pages.

**Current app version: v0.9.8.**

## What works
- Browsing grocery deals, product photographs, search, category filters, favorites and shopping lists.
- User-preferred category order and compact BOGO/per-item prices.
- Automatic checks for newly deployed app versions on launch, return, and every 60 seconds while open.
- Visible sale-date status: current, upcoming or expired.
- Week selector when a separately validated upcoming catalog exists.
- Stable product-name keys for favorites and list selections across weekly IDs.

## Weekly automation
- `.github/workflows/weekly-deals.yml` runs daily, plus extra checks Wednesday–Friday.
- `scripts/update_weekly_deals.py` discovers weekly iHeartPublix ads from the homepage, weekly-ad page, RSS and optional public WordPress API. If an article cannot be fetched directly, it can use full article content supplied by RSS/API.
- It extracts BOGO listings, price ranges and no-price offers, classifies grocery categories and validates catalog size, prices, categories and sale dates.
- Valid previews are staged as `data/next-deals.json`; they become `data/deals.json` when their sale week begins. Failures retain the existing catalogs.
- `scripts/publish_weekly_catalog.py` publishes only newer dated catalogs and protects against GitHub write conflicts.
- The Pages deployment builds product images for both weeks automatically, restores previously cached photos across weekly catalog changes, and reuses a product-name-indexed image library. Known barcodes are checked before broader image searches.
- The importer has offline smoke tests in `tests/test_weekly_deals.py`.

**Important:** These changes establish the automated process, but successful live extraction from the publisher's site has not yet been independently verified. The source can change markup or block automated requests. If a week is missed, the app explicitly displays the dates of its last valid catalog rather than presenting old offers as current.

## Catalog
The default catalog is `data/deals.json`. The optional preview catalog is `data/next-deals.json`. Both use `saleStart`, `saleEnd`, `sourceUrl` and a `deals` array.

BOGO prices and coupon eligibility vary by location; the displayed amounts are previews and should be checked against local shelf tags.

## Future
- Increase the reliability and completeness of fresh weekly imports using real deployment logs.
- Verify photo coverage and match quality on a newly published weekly catalog.
- Add quantities, totals and in-store check-off to shopping lists.
- Improve coupon verification and optional alerts.
