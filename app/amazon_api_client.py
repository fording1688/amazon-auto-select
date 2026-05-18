from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Protocol

from app.config import get_settings


class AmazonApiClient(Protocol):
    def search_products(self, keyword: str, limit: int = 20) -> list[dict]:
        ...


TOOL_TERMS = [
    "diamond band saw blade",
    "cbn chainsaw grinding wheel",
    "diamond grinding disc",
    "glass grinder bit",
    "lapidary saw blade",
    "tormek replacement parts",
    "stained glass soldering tools",
    "glass cutter replacement wheel",
]


@dataclass
class MockAmazonApiClient:
    marketplace: str = "amazon.com"

    def search_products(self, keyword: str, limit: int = 20) -> list[dict]:
        rng = random.Random(int(hashlib.sha1(keyword.encode("utf-8")).hexdigest(), 16))
        products = []
        modifiers = [
            "Replacement",
            "Compatible",
            "Industrial",
            "Premium",
            "Heavy Duty",
            "Precision",
            "Value Pack",
            "Kit",
        ]
        pack_options = [1, 1, 1, 2, 3, 5, 10]
        brands = ["ToolPro", "Gryphon", "Generic", "CBNPro", "DiamondEdge", "GlassMate", "ShopSupply"]

        base_term = keyword if keyword else rng.choice(TOOL_TERMS)
        for idx in range(limit):
            qty = rng.choice(pack_options)
            modifier = rng.choice(modifiers)
            asin = f"B0MOCK{hashlib.md5(f'{keyword}-{idx}'.encode()).hexdigest()[:4].upper()}"
            price = round(rng.uniform(8, 95), 2)
            if qty >= 3:
                price = round(price * (1 + qty * 0.16), 2)
            reviews = int(rng.triangular(8, 3500, 240))
            if idx in (0, 1):
                reviews += rng.randint(800, 5000)
            title_pack = f"{qty}-Pack " if qty > 1 else ""
            title = f"{modifier} {title_pack}{base_term.title()} Set for Repair and Workshop Use"
            products.append(
                {
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "rating": round(rng.uniform(3.6, 4.8), 1),
                    "review_count": reviews,
                    "brand": rng.choice(brands),
                    "seller": rng.choice(["Amazon", "Tool Outlet Direct", "US Workshop Supply", "Factory Store"]),
                    "image_url": f"https://dummyimage.com/240x240/e8edf3/263238.png&text={asin}",
                    "product_url": f"https://www.amazon.com/dp/{asin}",
                    "availability": rng.choice(["In Stock", "Only 8 left in stock", "In Stock"]),
                    "coupon": rng.choice(["", "5% coupon", "$2 coupon", "10% coupon"]),
                    "variation_count": rng.randint(0, 8),
                    "package_quantity": qty,
                    "bsr": rng.randint(1200, 120000),
                }
            )
        return products


class PlaceholderAmazonApiClient:
    def __init__(self, provider: str):
        self.provider = provider

    def search_products(self, keyword: str, limit: int = 20) -> list[dict]:
        raise NotImplementedError(
            f"{self.provider} provider is not implemented yet. Set AMAZON_API_PROVIDER=mock for local testing."
        )


def get_amazon_client() -> AmazonApiClient:
    provider = get_settings().amazon_api_provider.lower()
    if provider == "mock":
        return MockAmazonApiClient()
    if provider in {"serpapi", "rainforest", "keepa", "dataforseo", "oxylabs"}:
        return PlaceholderAmazonApiClient(provider)
    return MockAmazonApiClient()
