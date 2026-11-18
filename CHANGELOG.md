# bogo. — Changelog

Version numbers are retrospective development milestones reconstructed from the repository's November 17, 2026 commit history. They are not claims that separate versioned releases were published at those points.

## v0.9.9 — November 17, 2026
- Added mobile-friendly sorting: preferred category order (default), BOGO price low/high, and name A–Z.
- Added a collapsed Filters panel with coupons-only, hide alcohol, and maximum BOGO price.
- Filters exclude products with missing prices when applying a price cap; price ranges must fit entirely within the selected cap.
- Save browse preferences locally and restore them on subsequent opens.
- Group Lists and Favorites by the preferred grocery category order.
- Kept legacy manual text import accessible under advanced Filters without displaying it on the main screen.

## v0.9.8 — November 17, 2026
- Prioritize static, locally cached images before external requests.
- Update shopping-list and Favorite buttons without rebuilding the deal grid, so loaded images stay visible.
- Cache remote image matches by complete product name and package size instead of a shortened query.
- Reuse successful downloaded product photos across weekly catalog releases.
- Restore previous build photo caches, and cap image searches so a slow provider does not indefinitely block website deployment.
- Prefer barcode-exact Open Food Facts photos when a product code is available.
- Reject very narrow banner images rather than displaying them as package photos.
- Full live importer verification is still pending because the publisher sometimes rejects direct automated requests.

## v0.9.7 — November 17, 2026
- Rebuilt the broken BOGO parser and added article discovery through multiple public sources.
- Added protected current/next-week publication, auto-promotion and small offline parser checks.
- Added explicit current/upcoming/expired date labels and a two-week selector.
- Saved item names now survive week-specific product-ID changes.
- Photo generation includes upcoming catalog products.
- The next live weekly extraction still requires verification.

## v0.9.6 — November 17, 2026
- Removed artificial vertical spacing in deal cards and hid empty size labels.

## v0.9.5 — November 17, 2026
- Added automatic installed-PWA version checks and a network-first service worker.

## v0.9.4 — November 17, 2026
- Corrected overly dark product images and adopted the user's category priority.

## v0.9.3 — November 17, 2026
- Grouped deals by category and replaced long effective-price descriptions with compact per-item amounts.
- Guarded price formatting against NaN.

## v0.8.0 — November 17, 2026
- Added scheduled Wednesday/Thursday weekly-ad discovery.
- Added manual iHeartPublix ad URL workflow dispatch.
- Added date, offer-count and price validation with fail-safe retention of the previous catalog.
- Added conflict-safe publishing and automatic photo-cache refresh when the catalog changes.
- The weekly extractor has not yet been validated against a newly published live ad.

## v0.7.1 — November 17, 2026
- Added Wikimedia Commons as an additional candidate-image source.
- Reattempts image searches that previously returned no candidates.
- Replaced repetitive missing-photo text with styled category placeholders.
- No new product photographs are claimed until reviewed and cached.

## v0.7.0 — November 17, 2026
- Added a persistent product-photo candidate database keyed by normalized product names.
- Added scheduled incremental image discovery, with suggestions held for review.
- Added approved-photo publishing and local image caching.
- Disabled the old workflow that published unreviewed search matches.
- No new image matches are claimed until approved and cached.

## v0.6.1 — November 17, 2026
- Added in-app version display and retrospective changelog.
- Refined contained image thumbnails and photo presentation.

## v0.6.0 — November 17, 2026
- Added locally cached product photos, image validation and resizing.
- Constrained product photographs to their card media areas.
- Added photo attribution and representative-variety labels.
- Current catalog: 150 offers; 7 cached images.

## v0.5.0 — November 17, 2026
- Replaced five sample deals with 150 Publix BOGO offers for November 19–25.
- Added BOGO price ranges and effective per-item prices.
- Introduced automated image matching through Open Food Facts.

## v0.4.0 — November 17, 2026
- Added Deals, Lists and Favorites bottom navigation.
- Added locally saved favorite products.
- Adjusted app shell to more closely follow Everyday.

## v0.3.0 — November 17, 2026
- Reworked dark surfaces, typography, header spacing and cards to align with Everyday.
- Corrected wordmark spacing and circular period.

## v0.2.0 — November 17, 2026
- Established the three-color b. icon family.
- Selected Gold: dark brown background, cream letter and gold period.
- Added app icon and iOS touch icon generation.

## v0.1.0 — November 17, 2026
- Initial public GitHub Pages app.
- Searchable BOGO sample catalog, category filters, shopping list and text import.
- GitHub Actions deployment workflow.

## Planned, not released
- Automatic weekly offer ingestion with validation and manual URL fallback.
- Broader verified product-photo coverage.
- Multiple named shopping lists and more robust saved-item handling.
