"""Fast, offline smoke tests for the weekly Publix article extractor."""
import unittest
from scripts.update_weekly_deals import HTMLLines, parse_offers, sale_dates, validate

SAMPLE = """
<html><body>
<h2>BOGOS</h2>
<div><button>+</button><span>Add to Shopping List</span>
Fresh Attitude Salads, Spring Mix, 5 oz, BOGO $3.99</div>
<p>Athens Phyllo Bites, 8.4 oz box, BOGO $6.79</p>
<p>Boursin Gourmet Cheese, 5.3 oz, BOGO $5.99 – $7.29</p>
<p>Bero Non-Alcoholic Beer, 12 oz, BOGO (no price listed)</p>
<p>–$1/1 Boursin product (Publix Digital Coupon)</p>
<h2>MEAT</h2>
<p>Ordinary meat ad, BOGO $12.99</p>
</body></html>"""

class WeeklyDealsTest(unittest.TestCase):
    def test_parse_realistic_bogo_section(self):
        page = HTMLLines()
        page.feed(SAMPLE)
        page.flush()
        offers = parse_offers(page.blocks, sale_dates(
            "https://www.iheartpublix.com/2026/11/publix-ad-coupons-week-of-11-19-to-11-25-11-18-to-11-25-for-some/"
        )[0])
        self.assertEqual(4, len(offers))
        self.assertEqual("3.99", offers[0]["priceLabel"])
        self.assertEqual("5.99–7.29", offers[2]["priceLabel"])
        self.assertIsNone(offers[3]["priceMin"])
        self.assertNotIn("Ordinary meat ad", [x["name"] for x in offers])
        self.assertEqual(len({x["id"] for x in offers}), len(offers))
        validate(offers, 4)

    def test_date_window(self):
        start, end = sale_dates(
            "https://www.iheartpublix.com/2026/11/publix-ad-coupons-week-of-11-19-to-11-25-11-18-to-11-25-for-some/"
        )
        self.assertEqual("2026-11-19", start.isoformat())
        self.assertEqual("2026-11-25", end.isoformat())

if __name__ == "__main__":
    unittest.main()
