from __future__ import annotations

import re


PREFERRED_TERMS = [
    "diamond",
    "cbn",
    "grinding",
    "glass",
    "lapidary",
    "blade",
    "wheel",
    "bit",
    "replacement",
    "compatible",
    "soldering",
    "cutter",
]

BUNDLE_TERMS = ["pack", "set", "kit", "replacement", "compatible", "refill", "disc", "blade", "wheel", "bit"]
RISK_TERMS = ["battery", "electrical", "helmet", "respirator", "medical", "food", "child", "gas"]


def classify_decision(score: int) -> str:
    if score >= 80:
        return "重点测款"
    if score >= 65:
        return "小批量测试"
    if score >= 50:
        return "观察"
    return "放弃"


def _clamp(value: float, max_score: int) -> int:
    return max(0, min(max_score, round(value)))


def calculate_opportunity_score(product: dict) -> dict:
    title = (product.get("title") or "").lower()
    price = float(product.get("price") or 0)
    reviews = int(product.get("review_count") or 0)
    rating = float(product.get("rating") or 0)
    package_quantity = int(product.get("package_quantity") or 1)

    demand = 0
    if 50 <= reviews <= 1200:
        demand += 18
    elif 15 <= reviews < 50:
        demand += 10
    elif 1200 < reviews <= 3500:
        demand += 13
    elif reviews > 3500:
        demand += 7
    if rating >= 4.1:
        demand += 5
    if product.get("bsr") and int(product["bsr"]) < 50000:
        demand += 2
    demand = _clamp(demand, 25)

    competition = 20
    if reviews > 3000:
        competition -= 9
    elif reviews > 1200:
        competition -= 5
    if any(brand in (product.get("brand") or "").lower() for brand in ["tormek", "dewalt", "bosch", "makita"]):
        competition -= 5
    if "amazon" == (product.get("seller") or "").lower():
        competition -= 2
    competition = _clamp(competition, 20)

    profit = 0
    if 12 <= price <= 80:
        profit += 15
    elif 8 <= price < 12 or 80 < price <= 120:
        profit += 8
    if any(term in title for term in PREFERRED_TERMS):
        profit += 5
    profit = _clamp(profit, 20)

    bundle = 0
    if any(term in title for term in BUNDLE_TERMS):
        bundle += 7
    if package_quantity == 1 and any(term in title for term in ["replacement", "disc", "blade", "wheel", "bit"]):
        bundle += 7
    elif package_quantity in {3, 5, 10}:
        bundle += 5
    if re.search(r"\b(3|5|10)[ -]?pack\b", title):
        bundle += 2
    bundle = _clamp(bundle, 15)

    light_small = 8 if any(term in title for term in ["blade", "wheel", "disc", "bit", "cutter", "parts"]) else 4
    if any(term in title for term in ["machine", "table", "stand", "saw kit"]):
        light_small -= 4
    light_small = _clamp(light_small, 10)

    improvement = 0
    if 3.7 <= rating <= 4.2 and reviews >= 30:
        improvement += 8
    elif rating < 3.7 and reviews >= 30:
        improvement += 5
    else:
        improvement += 3
    if any(term in title for term in ["compatible", "replacement"]):
        improvement += 2
    improvement = _clamp(improvement, 10)

    penalty = 0
    if price < 8:
        penalty += 5
    if reviews > 6000:
        penalty += 7
    if any(term in title for term in RISK_TERMS):
        penalty += 10

    score = _clamp(demand + competition + profit + bundle + light_small + improvement - penalty, 100)
    return {
        "opportunity_score": score,
        "decision": classify_decision(score),
        "breakdown": {
            "市场需求": demand,
            "竞争难度": competition,
            "利润空间": profit,
            "组合装机会": bundle,
            "轻小件优势": light_small,
            "差评改进机会": improvement,
            "扣分": penalty,
        },
    }
