"""Quick regression checks for false positive grocery product photos."""
import unittest
from scripts.build_product_photos import plausible_product_match, query_for


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

    def test_tiny_or_ambiguous_search_is_not_trusted(self):
        self.assertFalse(plausible_product_match("Pepsi", "Pepsi", "Brand Logo"))
        self.assertFalse(plausible_product_match("Hunt's Tomatoes", "Hunter", "Tomato Soup"))
        self.assertEqual("Hunt’s Tomatoes", query_for({"name": "Hunt’s Tomatoes or Sauce, 14.5 oz"}))


if __name__ == "__main__":
    unittest.main()
