# bogo. — Changelog

Version numbers are retrospective development milestones reconstructed from the repository's November 17, 2026 commit history. They are not claims that separate versioned releases were published at those points.

## v0.11.4 — November 18, 2026
- Diagnosed why previous strict image filtering reduced photo coverage to 26/322.
- Added DuckDuckGo's titled grocery image results as a fallback, with brand and product-word checks, retailer source ranking, and explicit exclusions for stock photos, games and recipes.
- First successful expanded image build: 303/322 available photos (298 newly saved, 5 restored, 19 missing); four photo matching tests passed.
- Corrected the image cache to use a unique key per deployment, preserving new matches instead of reusing an immutable stale catalog-hash cache.
- Replaced dominant repeated category placeholders with quieter missing-image states. Cached bad images remain excluded.

## v0.11.2 — November 18, 2026
- Successfully imported the actual November 12–18 Publix ad into a separate current-week catalog (172 BOGO offers, 168 with prices).
- Preserved the 150-item November 19–25 preview catalog without overwriting it.
- Added current-week catalog discovery to app startup and automatic This Week / Next Week tabs, selected from local sale dates.
- Kept per-week shopping lists separated, including after the active week changes.
- Extended automatic photo generation and cache restoration to cover the new current-week catalog.
- Verified GitHub Actions import and publish run 44243819823.

## v0.11.1 — November 17, 2026
- Added a separate read-only live test for the current November 12–18 Publix ad. It does not publish or modify catalog data.
- Successful GitHub Actions run 44239657634 extracted 172 BOGO candidates, with prices on 168, across 7 categories.
- Identified that normal imports skipped the active week because the stored catalog was already dated November 19–25.
- Added the product keyword filter to Publix coupon-name links; Ibotta and printable offers retain their provider links.
- Full live publication and individual-offer deep links remain unverified.

## v0.11.0 — November 17, 2026
- Replaced the large Favorite and Add to List buttons with black corner controls overlaying product images: red active heart, blue active list button.
- Made images and a smaller More button open a product details sheet with list selection, quantity stepper, favorite status and coupon notes.
- Removed the redundant top-right List shortcut; the bottom Lists tab remains primary.
- Automatically create separate shopping lists by sale week, preserve older lists, and support multiple custom named lists for each week.
- Added list picker, New, Rename, Clear and Delete actions, with confirmation before destructive actions.
- Migrated v0.10.x list items, quantities and purchased states to weekly list storage without deleting the old records.
- Replaced generic numeric coupon dropdown labels with the actual named offer; offer names link to Publix, Ibotta or a printable coupon provider, and a separate chevron reveals terms.
- Products with several offers show the first title and a More offers indicator instead of a count. Provider links may require searching for the exact current offer.

## v0.10.1 — November 17, 2026
- Turn long coupon strings into expandable options on deal cards and in shopping-list rows.
- Label source types such as Publix digital, printable coupon and Ibotta rebate, preserving purchase requirements and restrictions from the ad.
- Link to the official Publix digital coupon and Ibotta sites when relevant.
- Keep potential coupon savings separate from the estimated checkout total; do not pretend a coupon is clipped or eligible.
- Add a shopping-list progress bar and a persistent Hide checked toggle.

## v0.10.0 — November 17, 2026
- Added compact, single-column shopping list organized by the user's preferred grocery category order.
- Default to two units per BOGO selection, with per-item increase/decrease controls (1–99).
- Check off items as they are purchased without rebuilding the photo grid; saved checkmarks survive app restarts.
- Calculate estimated BOGO spend and savings using two-for-one pairs; odd quantities are billed as additional full-price items.
- Show transparent totals and exclude per-pound, missing-price, expired or unavailable deals rather than guessing weights or prices.
- Save product snapshots across catalog changes and migrate existing saved selections.
- Provide a copyable, quantity-aware shopping list.

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
