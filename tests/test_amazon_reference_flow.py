from __future__ import annotations

import unittest

from app.amazon_image_prompts import build_amazon_image_prompt
from app.amazon_url_parser import parse_amazon_url
from app.reference_analysis import analyze_references
from app.serpapi_amazon import normalize_search_item


class AmazonReferenceFlowTests(unittest.TestCase):
    def test_parse_amazon_url_dp(self):
        parsed = parse_amazon_url("https://www.amazon.com/Some-Product/dp/B0ABCDEF12/?th=1")
        self.assertTrue(parsed["isAmazonUrl"])
        self.assertEqual(parsed["asin"], "B0ABCDEF12")
        self.assertEqual(parsed["amazonDomain"], "amazon.com")
        self.assertEqual(parsed["normalizedUrl"], "https://www.amazon.com/dp/B0ABCDEF12")

    def test_parse_asin_from_text(self):
        parsed = parse_amazon_url("B00TEST123")
        self.assertEqual(parsed["asin"], "B00TEST123")
        self.assertFalse(parsed["isAmazonUrl"])

    def test_normalize_search_item(self):
        item = normalize_search_item(
            {
                "position": 1,
                "asin": "B0ABCDEF12",
                "title": "8 Inch CBN Grinding Wheel",
                "price": "$39.99",
                "rating": "4.5",
                "reviews": "1,234",
            },
            "amazon.com",
        )
        self.assertEqual(item["linkClean"], "https://www.amazon.com/dp/B0ABCDEF12")
        self.assertEqual(item["extractedPrice"], 39.99)
        self.assertEqual(item["reviews"], 1234)

    def test_reference_analysis_local(self):
        insights = analyze_references(
            [
                {
                    "productData": {
                        "title": "8 Inch CBN Grinding Wheel 5/8 Arbor",
                        "categories": ["Industrial & Scientific", "Abrasive Wheels"],
                        "aboutItem": ["60 grit aluminum body", "Compatible with bench grinders"],
                        "images": ["a", "b", "c", "d"],
                        "normalizedFacts": {"diameter": "8 inch", "arborHole": "5/8 inch"},
                    }
                }
            ],
            use_model=False,
        )
        self.assertIn("dimension", insights["commonImageTypes"])
        self.assertIn("diameter", insights["productFactsCandidates"])

    def test_prompt_builder_main_image_forces_no_text(self):
        bundle = build_amazon_image_prompt(
            {
                "imageType": "main_image_clean",
                "overlayTextMode": "recommended",
                "confirmedFacts": {"productName": "CBN grinding wheel", "diameter": "8 inch"},
            }
        )
        self.assertTrue(bundle["valid"])
        self.assertEqual(bundle["overlayTextMode"], "none")
        self.assertIn("pure white background", bundle["promptEn"])


if __name__ == "__main__":
    unittest.main()
