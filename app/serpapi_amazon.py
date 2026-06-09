from __future__ import annotations

import re
from typing import Any

from app.serpapi_client import SerpApiClient


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", _text(value))
    return float(match.group(0).replace(",", "")) if match else None


def _int(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _clean_amazon_link(link: str | None, asin: str | None, domain: str) -> str:
    if asin:
        return f"https://www.{domain}/dp/{asin}"
    return _text(link)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_specs(product: dict[str, Any]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for source_key in ("product_information", "product_details", "details", "item_specifications"):
        source = product.get(source_key)
        if isinstance(source, dict):
            for key, value in source.items():
                if key and value is not None:
                    specs[_text(key)] = _text(value)
        elif isinstance(source, list):
            for item in source:
                if isinstance(item, dict):
                    key = _text(item.get("name") or item.get("label") or item.get("title"))
                    value = _text(item.get("value") or item.get("text"))
                    if key and value:
                        specs[key] = value
    return specs


def _fact_by_keywords(specs: dict[str, str], keywords: list[str]) -> str:
    for key, value in specs.items():
        lower = key.lower()
        if any(word in lower for word in keywords):
            return value
    return ""


def _normalize_facts(product: dict[str, Any], specs: dict[str, str]) -> dict[str, str]:
    title = _text(product.get("title"))
    all_text = " ".join([title, " ".join(specs.values())])
    diameter = _fact_by_keywords(specs, ["diameter", "size"])
    thickness = _fact_by_keywords(specs, ["thickness", "width"])
    arbor = _fact_by_keywords(specs, ["arbor", "bore", "hole"])
    grit_match = re.search(r"\b(\d{2,4})\s*grit\b", all_text, re.I)
    quantity_match = re.search(r"\b(\d+)\s*(?:pack|pcs|pieces|piece|count)\b", all_text, re.I)
    return {
        "productName": title,
        "productCategory": " > ".join([_text(item.get("name") or item) for item in _list(product.get("categories")) if item]),
        "brand": _text(product.get("brand")),
        "material": _fact_by_keywords(specs, ["material"]),
        "color": _fact_by_keywords(specs, ["color"]),
        "diameter": diameter,
        "thickness": thickness,
        "arborHole": arbor,
        "grit": grit_match.group(1) if grit_match else _fact_by_keywords(specs, ["grit"]),
        "quantity": quantity_match.group(1) if quantity_match else _fact_by_keywords(specs, ["number of items", "unit count"]),
        "packageIncludes": _fact_by_keywords(specs, ["package", "included", "components"]),
        "compatibilityTarget": _fact_by_keywords(specs, ["compatible", "fit", "model"]),
    }


def normalize_search_item(item: dict[str, Any], amazon_domain: str) -> dict[str, Any]:
    asin = _text(item.get("asin"))
    price = item.get("price") or item.get("prices")
    if isinstance(price, dict):
        price_text = _text(price.get("raw") or price.get("value"))
    else:
        price_text = _text(price)
    return {
        "position": item.get("position"),
        "asin": asin or None,
        "title": _text(item.get("title")) or None,
        "link": _text(item.get("link")) or None,
        "linkClean": _clean_amazon_link(item.get("link"), asin or None, amazon_domain),
        "serpapiLink": _text(item.get("serpapi_link")) or None,
        "thumbnail": _text(item.get("thumbnail")) or None,
        "brand": _text(item.get("brand")) or None,
        "rating": _number(item.get("rating")),
        "reviews": _int(item.get("reviews") or item.get("ratings_total")),
        "price": price_text or None,
        "extractedPrice": _number(item.get("extracted_price") or price_text),
        "sponsored": bool(item.get("sponsored")),
        "badges": [str(value) for value in _list(item.get("badges"))],
        "tags": [str(value) for value in _list(item.get("tags"))],
    }


class SerpApiAmazonSearchAdapter:
    def __init__(self, client: SerpApiClient | None = None):
        self.client = client or SerpApiClient()

    def search(self, keyword: str, amazon_domain: str = "amazon.com", language: str = "en_US", page: int = 1, device: str = "desktop") -> dict[str, Any]:
        raw = self.client.search(
            {
                "engine": "amazon",
                "k": keyword,
                "amazon_domain": amazon_domain,
                "language": language,
                "page": page,
                "device": device,
            }
        )
        organic = _list(raw.get("organic_results") or raw.get("products"))
        ads = _list(raw.get("ads") or raw.get("product_ads"))
        related = []
        for item in _list(raw.get("related_searches")):
            related.append(_text(item.get("query") if isinstance(item, dict) else item))
        return {
            "source": "serpapi_amazon_search",
            "query": keyword,
            "amazonDomain": amazon_domain,
            "page": page,
            "totalResults": _int(_dict(raw.get("search_information")).get("total_results")),
            "organicResults": [normalize_search_item(item, amazon_domain) for item in organic],
            "productAds": [normalize_search_item(item, amazon_domain) for item in ads],
            "relatedSearches": [item for item in related if item],
            "raw": raw,
            "warnings": [],
        }


class SerpApiAmazonProductAdapter:
    def __init__(self, client: SerpApiClient | None = None):
        self.client = client or SerpApiClient()

    def product(self, asin: str, amazon_domain: str = "amazon.com", language: str = "en_US", device: str = "desktop") -> dict[str, Any]:
        raw = self.client.search(
            {
                "engine": "amazon_product",
                "asin": asin,
                "amazon_domain": amazon_domain,
                "language": language,
                "device": device,
            }
        )
        product = _dict(raw.get("product_results") or raw.get("product") or raw)
        specs = _extract_specs(product)
        categories = []
        for item in _list(product.get("categories")):
            categories.append(_text(item.get("name") if isinstance(item, dict) else item))
        images = []
        for key in ("images", "media"):
            for item in _list(product.get(key)):
                if isinstance(item, dict):
                    url = _text(item.get("link") or item.get("large") or item.get("thumbnail"))
                else:
                    url = _text(item)
                if url:
                    images.append(url)
        main_image = _text(product.get("main_image") or product.get("thumbnail") or (images[0] if images else ""))
        return {
            "source": "serpapi_amazon_product",
            "asin": _text(product.get("asin")) or asin,
            "amazonDomain": amazon_domain,
            "title": _text(product.get("title")) or None,
            "brand": _text(product.get("brand")) or None,
            "description": _text(product.get("description")) or None,
            "categories": [item for item in categories if item],
            "productLink": _clean_amazon_link(product.get("link"), asin, amazon_domain),
            "mainImage": main_image or None,
            "images": images,
            "rating": _number(product.get("rating")),
            "reviews": _int(product.get("reviews") or product.get("ratings_total")),
            "price": _text(product.get("price")) or None,
            "extractedPrice": _number(product.get("extracted_price") or product.get("price")),
            "availability": _text(product.get("availability")) or None,
            "aboutItem": [str(item) for item in _list(product.get("about_this_item") or product.get("feature_bullets"))],
            "itemSpecifications": specs,
            "productDetails": specs,
            "productFeatures": [str(item) for item in _list(product.get("features"))],
            "productDescription": _text(product.get("product_description") or product.get("description")) or None,
            "variants": _list(product.get("variants")),
            "compareWithSimilar": _list(product.get("compare_with_similar")),
            "relatedProducts": _list(product.get("related_products")),
            "boughtTogether": _list(product.get("bought_together")),
            "reviewsInformation": product.get("reviews_information"),
            "normalizedFacts": _normalize_facts(product, specs),
            "raw": raw,
            "warnings": [],
        }
