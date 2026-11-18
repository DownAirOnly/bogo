# bogo.

Mobile-first Publix BOGO browser and installed iPhone PWA, published on GitHub Pages.

**Current app version: v0.12.0.**

## What works
- Browsing grocery deals, product photographs, search, category filters, favorites and shopping lists.
- User-preferred category order and compact BOGO/per-item prices.
- Optional sorting by category order, BOGO price or product name; collapsed filters for coupons, alcohol and a maximum BOGO price. Browse preferences are saved on this device.
- Automatic checks for newly deployed app versions on launch, return, and every 60 seconds while open.
- Visible sale-date status: current, upcoming or expired.
- Deal view switches between active-week and upcoming BOGO catalog when both are published, with clear dates and separate week-specific shopping lists.
- Stable product-name keys for favorites and list selections across weekly IDs.
- One-page shopping checklist with quantities, checked-off items, category groups and locally saved item snapshots that remain visible after a weekly ad changes.
- BOGO estimates calculate paid items as ceil(quantity / 2) and free items as floor(quantity / 2). Tax and coupons are not included; weight-priced, missing-price and unavailable/expired-ad items are visibly excluded from totals.
- Shopping-list completion progress and an optional Hide checked control, saved across sessions.
- Deal images open an in-app product details sheet to edit quantities, favorites and which same-week list receives the deal; a small More button opens the same sheet.
- Small black corner actions on each product photo: top-right heart turns red for favorites; bottom-right add-to-list becomes blue when selected. Both toggle directly without reloading the grid.
- Weekly shopping lists are created automatically for each sale-date range; separate named lists can be created, renamed, selected and deleted for a given week.
- Upcoming deals are compared conservatively against the preceding saved advertisement, with "New this week" labels and a filter when an adjacent historical ad is available.
- Unchecked items carried into another week are reconciled against returning product matches; successful matches use current-week deal details, and unmatched products remain on the list without a speculative discount.
- Favorites are kept in a local product library across sale weeks, including items no longer advertised; expired BOGO prices aren't displayed as active.
- Shopping list summaries distinguish total estimated spending and what remains to buy. Use Share on iPhone or Copy to send quantities, checkmarks, and provisional totals.
- On a newer week's list, **Bring over unchecked items** carries unpurchased products from the most recent earlier list. It preserves quantities and skips duplicates, without modifying the old list. Items not found in the new advertisement are excluded from BOGO cost and savings estimates.
- Older shopping-list quantities and purchased states migrate safely to weekly list storage the first time v0.11.0 opens; original legacy storage remains untouched.
- The search bar now fills the header; Lists live in the bottom navigation, without a duplicate top-right button.
- Coupon overview labels show the named discount/rebate, not a count. The offer title opens the relevant provider website, while a separate chevron reveals conditions and other offers. Provider links are not verified deep links to a specific clipped coupon.
- Publix coupon names now open the Publix coupon listing with the product keyword filter prefilled. Ibotta and printable coupons open their official provider pages; specific-offer deep links remain unavailable without verified IDs.
- Existing ad coupon/rebate notes are condensed into expandable product details on deal cards and list rows. The source and conditions remain visible, with direct links to Publix digital coupons and Ibotta. Offers are not automatically clipped or deducted from estimates; availability and eligibility must be verified with each provider.

## Current week import (November 18, 2026)
- The verified live article for November 12–18 was parsed and published by GitHub Actions run 44243819823.
- **172 offers** were extracted across seven grocery categories; **168 had listed prices**.
- The publication job created `data/current-deals.json` without replacing the separately dated November 19–25 catalog.
- `scripts/import_active_week.py` performs the one-time validated import; `.github/workflows/import-active-week.yml` runs it and calls the SHA-protected publisher.
- Product-image generation processes current and preview catalogs. All catalog snapshots remain clearly date-labeled; local prices can vary.

## Weekly automation
- `.github/workflows/weekly-deals.yml` runs daily, plus extra checks Wednesday–Friday.
- `scripts/update_weekly_deals.py` discovers weekly iHeartPublix ads from the homepage, weekly-ad page, RSS and optional public WordPress API.
- Before a newly valid catalog replaces the main week, the importer saves the outgoing catalog as `data/previous-deals.json`. The publisher uses SHA-protected writes and retains date order; the PWA keeps older catalogs available for comparisons but hides expired ads from active shopping. If an article cannot be fetched directly, it can use full article content supplied by RSS/API.
- It extracts BOGO listings, price ranges and no-price offers, classifies grocery categories and validates catalog size, prices, categories and sale dates.
- Valid previews are staged as `data/next-deals.json`; they become `data/deals.json` when their sale week begins. Failures retain the existing catalogs.
- `scripts/publish_weekly_catalog.py` publishes only newer dated catalogs and protects against GitHub write conflicts.
- The Pages deployment builds product images for both weeks automatically, restores previously cached photos across weekly catalog changes, and reuses a product-name-indexed image library. Known barcodes are checked before broader image searches.
- The importer has offline smoke tests in `tests/test_weekly_deals.py`.
- `scripts/check_weekly_ad.py` and `.github/workflows/test-weekly-ad.yml` provide a read-only, separately triggered live-ad test that ignores publication date ordering and never edits the catalog.

**Live diagnostic (November 17, 2026):** A separate GitHub Actions read-only test successfully fetched and parsed the November 12–18 iHeartPublix advertisement: 172 candidate BOGOs, 168 with prices and 7 categories. The parser's two offline smoke tests also passed. See GitHub Actions run 44239657634 (Read-only current Publix BOGO ad test). This does **not** verify that every offer was extracted perfectly, nor does it test the publisher action. The earlier scheduled updater ran successfully but printed "No validated newer ad" because its existing dated catalog was already newer. Full automatic publication remains unverified. The test does not overwrite app deals; failed imports retain previously published data.

## Catalog
`data/current-deals.json` holds the verified November 12–18 week (172 BOGOs; 168 priced); the existing `data/deals.json` holds the November 19–25 preview (150 BOGOs). `data/next-deals.json` remains reserved for subsequent upcoming ads. The app uses `saleStart`/`saleEnd` to select the active week. The optional older-week catalog is hidden when expired, but its shopping list data stays on-device. Each catalog also stores `sourceUrl` and a `deals` array.

BOGO prices and coupon eligibility vary by location; the displayed amounts are previews and should be checked against local shelf tags.

## Future
- Increase the reliability and completeness of fresh weekly imports using real deployment logs.
- Verify photo coverage and match quality on a newly published weekly catalog.
- Add receipt/tax-adjusted totals and eventual cross-device sync for named lists.
- Add new-deal highlights and eventually more targeted grocery subcategories when the data supports them.
- Verify coupon eligibility, stacking and redemption with supported retailer integrations before estimating coupon-adjusted totals; add optional alerts.

## Image relevance fix (November 18, 2026)
- The original image search accepted unrelated thumbnails; a temporary strict matcher reduced coverage to 26 of 322 products.
- A read-only search-source diagnostic found that DuckDuckGo's public image search returns explicit product titles and retailer page references, whereas Google's returned HTML did not expose usable labeled thumbnails and Bing sometimes returned unrelated results.
- The automatic builder now matches product words, rejects obvious games/recipes/stock artwork, and prioritizes retail source pages when selecting a thumbnail. The original unchecked photo cache remains excluded.
- The first successful expanded image build found 303 of 322 images (298 added, 5 reused; 19 missing); subsequent deployments use unique cache keys so improvements persist across builds.
- Remaining placeholders are deliberately understated. Search titles are evidence of likely relevance, not visual verification of every photo.

## Photo-quality spot check (November 18, 2026)
- Reviewed 100 product pictures from the last successful 309-photo deployment against the listed product names. Most showed the intended grocery brand or item; a few used variety packs, promotional collages or a different permissible variant, rather than a clean single-product photo.
- The 309/322 image-count measure is **coverage**, not a claim that every product image is an exact size or flavor match. The image cache remains preserved while other features are developed.
