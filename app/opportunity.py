from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

from app.models import AnalysisReport, Product


CORE_MODIFIERS = [
    "replacement",
    "compatible",
    "parts",
    "repair kit",
    "5 pack",
    "10 pack",
    "multi pack",
    "assorted set",
]

CONSUMABLE_TERMS = [
    "blade",
    "wheel",
    "disc",
    "bit",
    "pad",
    "belt",
    "tip",
    "filter",
    "nozzle",
    "cutter",
    "grinder",
    "burr",
]

RISK_TERMS = [
    "battery",
    "charger",
    "helmet",
    "respirator",
    "medical",
    "food",
    "kids",
    "child",
    "gas",
]


@dataclass
class TestCandidate:
    product: Product
    report: AnalysisReport
    pack_signal: dict
    quick_reasons: list[str]
    sourcing_keywords: list[str]
    suggested_pack: str
    suggested_price: str
    action: str
    test_score: int


def expand_keyword(base_keyword: str) -> list[str]:
    base = " ".join(base_keyword.lower().strip().split())
    if not base:
        return []
    variants = {base}
    for modifier in CORE_MODIFIERS:
        variants.add(f"{base} {modifier}")
        if modifier in {"replacement", "compatible"}:
            variants.add(f"{modifier} {base}")
    if not any(term in base for term in ("pack", "kit", "set")):
        variants.add(f"{base} 3 pack")
        variants.add(f"{base} 5 pack")
        variants.add(f"{base} 10 pack")
    return sorted(variants)


def _loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _title(product: Product) -> str:
    return (product.title or "").lower()


def _is_consumable(product: Product) -> bool:
    title = _title(product)
    return any(term in title for term in CONSUMABLE_TERMS)


def _has_risk(product: Product) -> bool:
    title = _title(product)
    return any(term in title for term in RISK_TERMS)


def detect_pack_signal(product: Product, peer_products: Iterable[Product]) -> dict:
    title = _title(product)
    peers = list(peer_products)
    peer_count = len(peers) or 1
    multi_pack_peers = 0
    single_pack_peers = 0
    for peer in peers:
        qty = peer.package_quantity or 1
        peer_title = _title(peer)
        if qty >= 3 or re.search(r"\b(3|5|10)[ -]?pack\b", peer_title):
            multi_pack_peers += 1
        else:
            single_pack_peers += 1

    pack_terms = bool(re.search(r"\b(3|5|10)[ -]?pack\b", title) or "kit" in title or "set" in title)
    consumable = _is_consumable(product)
    peer_multi_ratio = multi_pack_peers / peer_count
    mostly_single_market = single_pack_peers >= multi_pack_peers

    if consumable and mostly_single_market and peer_multi_ratio < 0.45:
        recommended = "5-pack"
        if product.price and product.price < 18:
            recommended = "10-pack"
        elif product.price and product.price > 35:
            recommended = "3-pack"
        return {
            "score": 95,
            "recommended_pack": recommended,
            "label": "强组合装机会",
            "reason": "该关键词下竞品多为单件/低数量包装，但产品属于耗材或替换件，适合用多件装提高客单价。",
        }

    if consumable and pack_terms:
        return {
            "score": 78,
            "recommended_pack": f"{product.package_quantity or 3}-pack",
            "label": "已有组合装需求",
            "reason": "标题中已有 pack/set/kit 信号，说明买家接受多件装，需要看是否能做更清晰规格和更好价格。",
        }

    if consumable:
        return {
            "score": 68,
            "recommended_pack": "3-pack",
            "label": "可尝试小组合",
            "reason": "产品是轻小耗材/替换件，可先尝试 3-pack 或 5-pack。",
        }

    return {
        "score": 35,
        "recommended_pack": "1-pack",
        "label": "组合装不明显",
        "reason": "当前标题和品类信号不足，先按单件或套装观察。",
    }


def suggested_price_for_pack(product: Product, pack: str) -> str:
    price = float(product.price or 0)
    if not price:
        return "待核算"
    multiplier = {"3-pack": 2.65, "5-pack": 4.25, "10-pack": 7.8}.get(pack, 1)
    return f"${price * multiplier:.2f}"


def sourcing_keywords_for(product: Product) -> list[str]:
    base = product.keyword.keyword if product.keyword else product.title
    words = [base]
    title = _title(product)
    if "diamond" in title:
        words.append(f"{base} manufacturer")
    if "cbn" in title:
        words.append(f"{base} cbn wheel factory")
    if "glass" in title:
        words.append(f"{base} stained glass tool supplier")
    words.append(f"{base} bulk pack")
    return list(dict.fromkeys(words))[:4]


def build_test_candidate(product: Product, report: AnalysisReport, peers: Iterable[Product]) -> TestCandidate | None:
    price = float(product.price or 0)
    reviews = int(product.review_count or 0)
    if product.asin.startswith("B0MOCK"):
        return None
    if _has_risk(product):
        return None

    pack_signal = detect_pack_signal(product, peers)
    reasons: list[str] = []
    if 15 <= price <= 50:
        reasons.append("价格在 $15-$50，适合低成本 FBM 测款。")
    elif 12 <= price < 15 or 50 < price <= 80:
        reasons.append("价格仍可测，但需要更谨慎核算广告和履约成本。")
    else:
        return None

    if 50 <= reviews <= 1500:
        reasons.append("评论数处在适中区间，有需求但未必被头部完全垄断。")
    elif 15 <= reviews < 50:
        reasons.append("评论较少，可作为低成本观察型测试。")
    elif 1500 < reviews <= 3500:
        reasons.append("需求明确，但竞争偏强，需要靠组合装或图片规格差异化。")
    else:
        return None

    if _is_consumable(product):
        reasons.append("属于耗材/替换件方向，适合复购和多件装。")
    if pack_signal["score"] >= 75:
        reasons.append(pack_signal["reason"])

    test_score = min(
        100,
        round(report.opportunity_score * 0.65 + pack_signal["score"] * 0.25 + (10 if 15 <= price <= 50 else 4)),
    )
    suggested_pack = pack_signal["recommended_pack"]
    action = "FBM 采购 20-50 套小批量测试"
    if test_score >= 86:
        action = "优先进入本周测款，先做 FBM 小批量"
    elif test_score < 70:
        action = "先人工核查成本和侵权风险，再决定是否测"

    return TestCandidate(
        product=product,
        report=report,
        pack_signal=pack_signal,
        quick_reasons=reasons[:5],
        sourcing_keywords=sourcing_keywords_for(product),
        suggested_pack=suggested_pack,
        suggested_price=suggested_price_for_pack(product, suggested_pack),
        action=action,
        test_score=test_score,
    )
