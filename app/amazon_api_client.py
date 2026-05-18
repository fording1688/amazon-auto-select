from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import quote_plus

import requests

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
            search_url = f"https://www.amazon.com/s?k={quote_plus(base_term)}"
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
                    "product_url": search_url,
                    "availability": rng.choice(["In Stock", "Only 8 left in stock", "In Stock"]),
                    "coupon": rng.choice(["", "5% coupon", "$2 coupon", "10% coupon"]),
                    "variation_count": rng.randint(0, 8),
                    "package_quantity": qty,
                    "bsr": rng.randint(1200, 120000),
                }
            )
        return products


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    cleaned = str(value).replace(",", "").strip()
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    return int(digits) if digits else None


def _package_quantity_from_title(title: str) -> int:
    lower = title.lower()
    for qty in (10, 5, 4, 3, 2):
        if f"{qty}-pack" in lower or f"{qty} pack" in lower or f"pack of {qty}" in lower:
            return qty
    return 1


def _read_env_value(path: Path, names: tuple[str, ...]) -> str:
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in names:
            return value.strip().strip('"').strip("'")
    return ""


def _resolve_serpapi_key() -> str:
    settings = get_settings()
    names = ("SERPAPI_KEY", "SERPAPI_API_KEY")
    candidates = [
        settings.serpapi_key or "",
        os.getenv("SERPAPI_KEY", ""),
        os.getenv("SERPAPI_API_KEY", ""),
        _read_env_value(Path(".env"), names),
        _read_env_value(Path("../.env"), names),
    ]
    return next((value for value in candidates if value), "")


@dataclass
class SerpApiAmazonClient:
    amazon_domain: str = "amazon.com"
    language: str = "en_US"
    device: str = "desktop"

    def search_products(self, keyword: str, limit: int = 20) -> list[dict]:
        api_key = _resolve_serpapi_key()
        if not api_key:
            raise RuntimeError("Missing SerpApi key. Set SERPAPI_KEY or SERPAPI_API_KEY in .env.")

        products: list[dict] = []
        seen_asins: set[str] = set()
        page = 1
        while len(products) < limit and page <= 3:
            payload = self._request(keyword, page, api_key)
            for raw in self._iter_result_products(payload):
                mapped = self._map_product(raw, keyword)
                asin = mapped.get("asin")
                if not asin or not mapped.get("title") or asin in seen_asins:
                    continue
                seen_asins.add(asin)
                products.append(mapped)
                if len(products) >= limit:
                    break
            if not (payload.get("serpapi_pagination") or {}).get("next"):
                break
            page += 1
        return products

    def _request(self, keyword: str, page: int, api_key: str) -> dict:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "amazon",
                "amazon_domain": self.amazon_domain,
                "k": keyword,
                "page": page,
                "language": self.language,
                "device": self.device,
                "api_key": api_key,
                "output": "json",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(f"SerpApi error: {payload['error']}")
        return payload

    def _iter_result_products(self, payload: dict):
        for product in payload.get("organic_results", []) or []:
            yield product
        for section in payload.get("featured_products", []) or []:
            for product in section.get("products", []) or []:
                yield product
        product_ads = payload.get("product_ads")
        if isinstance(product_ads, dict):
            for product in product_ads.get("products", []) or []:
                yield product
        elif isinstance(product_ads, list):
            for product in product_ads:
                yield product

    def _map_product(self, product: dict, keyword: str) -> dict:
        title = str(product.get("title") or "").strip()
        price = _to_float(product.get("extracted_price") or product.get("price"))
        asin = str(product.get("asin") or "").strip()
        link = str(product.get("link_clean") or product.get("link") or "").strip()
        return {
            "asin": asin,
            "keyword": keyword,
            "title": title,
            "price": price,
            "rating": _to_float(product.get("rating")),
            "review_count": _to_int(product.get("reviews")),
            "brand": str(product.get("brand") or "").strip() or None,
            "seller": str(product.get("seller") or "").strip() or None,
            "image_url": str(product.get("thumbnail") or "").strip() or None,
            "product_url": link or (f"https://www.amazon.com/dp/{asin}" if asin else ""),
            "availability": str(product.get("availability") or "").strip() or None,
            "coupon": str(product.get("coupon") or "").strip() or None,
            "variation_count": None,
            "package_quantity": _package_quantity_from_title(title),
            "bsr": None,
        }


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
    if provider == "serpapi":
        return SerpApiAmazonClient()
    if provider in {"rainforest", "keepa", "dataforseo", "oxylabs"}:
        return PlaceholderAmazonApiClient(provider)
    return MockAmazonApiClient()
