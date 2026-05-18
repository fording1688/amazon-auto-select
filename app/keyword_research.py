from __future__ import annotations

import json
import re
from collections import Counter

from sqlalchemy.orm import Session

from app.amazon_api_client import get_amazon_client
from app.models import KeywordResearchRun
from app.opportunity import expand_keyword


BUYER_MODIFIERS = [
    "replacement",
    "compatible",
    "fits",
    "for",
    "kit",
    "set",
    "pack",
    "bulk",
    "assorted",
    "professional",
    "heavy duty",
    "diamond",
    "cbn",
    "carbide",
    "stained glass",
    "lapidary",
    "tile",
    "ceramic",
    "stone",
    "glass",
    "grout",
    "rotary tool",
    "dremel",
]

NEGATIVE_WORDS = [
    "free",
    "used",
    "manual",
    "pdf",
    "plans",
    "toy",
    "kids",
    "cheap",
    "rental",
    "job",
    "repair service",
]

STOPWORDS = {
    "with",
    "and",
    "for",
    "the",
    "inch",
    "inches",
    "pcs",
    "piece",
    "pieces",
    "pack",
    "set",
    "tool",
    "tools",
    "use",
    "using",
    "from",
    "most",
    "all",
    "fit",
    "fits",
    "compatible",
}


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _ngrams(tokens: list[str], size: int) -> list[str]:
    return [" ".join(tokens[index : index + size]) for index in range(0, max(0, len(tokens) - size + 1))]


def generate_seed_expansions(seed_keyword: str, limit: int = 30) -> list[str]:
    seed = _clean(seed_keyword)
    variants = set(expand_keyword(seed))
    product_patterns = [
        "{seed} replacement",
        "{seed} compatible",
        "{seed} parts",
        "{seed} kit",
        "{seed} set",
        "{seed} 3 pack",
        "{seed} 5 pack",
        "{seed} 10 pack",
        "{seed} bulk",
        "{seed} assorted",
        "replacement {seed}",
        "compatible {seed}",
        "{seed} for glass",
        "{seed} for stone",
        "{seed} for ceramic",
        "{seed} for tile",
        "{seed} for lapidary",
        "{seed} for stained glass",
        "{seed} for dremel",
    ]
    for pattern in product_patterns:
        variants.add(pattern.format(seed=seed))
    return sorted(variants)[:limit]


def extract_terms_from_titles(seed_keyword: str, titles: list[str]) -> dict:
    seed_tokens = set(_clean(seed_keyword).split())
    product_counter: Counter[str] = Counter()
    modifier_counter: Counter[str] = Counter()

    for title in titles:
        cleaned = re.sub(r"[^a-z0-9/ -]+", " ", _clean(title))
        tokens = [token for token in cleaned.split() if len(token) > 2 and token not in STOPWORDS]
        for size in (2, 3, 4):
            for phrase in _ngrams(tokens, size):
                phrase_tokens = set(phrase.split())
                if phrase_tokens & seed_tokens or any(term in phrase for term in BUYER_MODIFIERS):
                    product_counter[phrase] += 1
        for modifier in BUYER_MODIFIERS:
            if modifier in cleaned:
                modifier_counter[modifier] += 1

    product_terms = [term for term, _ in product_counter.most_common(40)]
    modifier_terms = [term for term, _ in modifier_counter.most_common(25)]
    ad_keywords = []
    for term in product_terms:
        if any(signal in term for signal in ["replacement", "compatible", "diamond", "carbide", "glass", "stone", "kit", "set"]):
            ad_keywords.append(term)
    ad_keywords = list(dict.fromkeys(ad_keywords))[:30]

    return {
        "product_terms": product_terms,
        "modifier_terms": modifier_terms,
        "ad_keywords": ad_keywords,
        "negative_keywords": NEGATIVE_WORDS,
    }


def run_keyword_research(db: Session, seed_keyword: str, fetch_limit: int = 8) -> KeywordResearchRun:
    run = KeywordResearchRun(seed_keyword=seed_keyword, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        expansions = generate_seed_expansions(seed_keyword)
        client = get_amazon_client()
        titles: list[str] = []
        for keyword in expansions[: min(12, len(expansions))]:
            products = client.search_products(keyword, limit=fetch_limit)
            titles.extend([product["title"] for product in products if product.get("title")])

        extracted = extract_terms_from_titles(seed_keyword, titles)
        run.status = "success"
        run.expanded_keywords_json = _json(expansions)
        run.product_terms_json = _json(extracted["product_terms"])
        run.modifier_terms_json = _json(extracted["modifier_terms"])
        run.ad_keywords_json = _json(extracted["ad_keywords"])
        run.negative_keywords_json = _json(extracted["negative_keywords"])
        run.raw_titles_json = _json(titles[:100])
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
    db.commit()
    db.refresh(run)
    return run


def loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
