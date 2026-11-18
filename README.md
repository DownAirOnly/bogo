# bogo.

Mobile-first Publix BOGO deal browser. Hosted on GitHub Pages.

**Current version:** v0.6.1 (November 17, 2026). See [CHANGELOG.md](CHANGELOG.md) for the reconstructed milestone history.

## Implemented
- Gold branding and Everyday-inspired app layout.
- Deals, Lists and Favorites navigation.
- Search, category filters, local shopping list and favorites.
- November 19–25, 2026 catalog with 150 offers.
- Seven locally cached product images; missing images remain explicitly unverified.
- Conservative image matching and image caching workflows.
- Paste-text deal import on this device.

## Not yet implemented
- Reliable automatic weekly deal ingestion.
- Direct import of an external URL.
- Broad image coverage across all products.
- Named lists and cross-device sync.

## Catalog
The app reads `data/deals.json`. Source attribution and offer dates are in the catalog metadata. Price ranges represent the original deal listing; verify local shelf prices and sale dates.

## Photo pipeline
`scripts/enrich_images.py` proposes Open Food Facts matches and `scripts/cache_images.py` validates and caches image files. Image-file validity **does not prove a correct product/variant match**. Review mismatches before treating them as verified packaging.
