"""Quick regression checks for false positive grocery product photos."""
import unittest
from scripts.build_product_photos import plausible_product_match, query_for, title_match_score


class PhotoMatchingTest(unittest.TestCase):
    def test_real_brand_and_product(self):
        self.assertTrue(plausible_product_match("Hunt's Tomatoes", "Hunt's", "Diced Tomatoes"))
        self.assertTrue(plausible_product_match("Del Monte Vegetables", "Del Monte", "Mixed Vegetables"))
        self.assertTrue(plausible_product_match("Muir Glen Tomatoes", "Muir Glen", "Organic Crushed Tomatoes"))
        self.assertTrue(plausible_product_match("Rotel Tomatoes", "Rotel", "Original Diced Tomatoes"))

    def test_screenshot_not_groceries(self):
        self.assertFalse(plausible_product_match("Hunt's Tomatoes", "", "Hunt Showdown game screenshot"))
        self.assertFalse(plausible_product_match("Del Monte Vegetables", "Del Monte", "Baseball sports graphic"))
        self.assertFalse(plausible_product_match("Muir Glen Tomatoes", "Muir Glen", "Decorative ribbons"))
        self.assertFalse(plausible_product_match("Rotel Tomatoes", "Rotel", "Tomato casserole recipe"))

    def test_named_retail_photos_preferred_over_random_images(self):
        cases = [
            ("Idahoan Mashed Potatoes", "Idahoan Buttery Homestyle Mashed Potatoes 4 oz - Walmart.com"),
            ("Del Monte Vegetables", "Del Monte Canned Mixed Vegetables 8.25 oz - Kroger"),
            ("Betty Crocker Brownie Mix", "Betty Crocker Fudge Brownie Mix - Walmart.com"),
            ("Campbell's Cream Soup", "Campbell's Cream of Chicken Soup - Walmart.com"),
            ("Hunt's Tomatoes", "Hunt's No Salt Added Diced Tomatoes 14.5 oz - Kroger"),
            ("Rotel Tomatoes", "RO*TEL Original Diced Tomatoes and Green Chiles 10 oz - Walmart.com")
        ]
        for query, title in cases:
            with self.subTest(query=query):
                self.assertGreaterEqual(title_match_score(query,title,"https://www.walmart.com/ip/example"),0)
        self.assertEqual(-1,title_match_score("Hunt's Tomatoes","Hunt Showdown game screenshot"))
        self.assertEqual(-1,title_match_score("Del Monte Vegetables","Del Monte Fruit Cocktail - Walmart"))
        self.assertEqual(-1,title_match_score("Betty Crocker Brownie Mix","Betty Crocker Logo"))

    def test_tiny_or_ambiguous_search_is_not_trusted(self):
        self.assertFalse(plausible_product_match("Pepsi", "Pepsi", "Brand Logo"))
        self.assertFalse(plausible_product_match("Hunt's Tomatoes", "Hunter", "Tomato Soup"))
        self.assertEqual("Hunt’s Tomatoes", query_for({"name": "Hunt’s Tomatoes or Sauce, 14.5 oz"}))


if __name__ == "__main__":
    unittest.main()
