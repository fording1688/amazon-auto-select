from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AdRecommendation, CampaignMetric, SearchTermMetric, TargetingMetric
from app.report_importer import _raw_text


RECOMMENDATION_LABELS = {
    "add_exact": "加入 exact",
    "add_exact_boost": "加入 exact 并适度提高预算/出价",
    "add_product_targeting_asin": "加入 ASIN 商品投放",
    "add_phrase_test": "phrase/exact 小预算测试",
    "negative_exact": "否定精准",
    "negative_or_lower_bid": "否定词或降低出价",
    "lower_bid": "降低出价",
    "increase_budget": "适度增加预算",
}

STATUS_LABELS = {
    "pending": "待确认",
    "approved": "已确认待执行",
    "executed": "已处理",
    "rejected": "已拒绝",
    "failed": "执行失败",
}


def _pct(value: float | None) -> str:
    return f"{(value or 0) * 100:.1f}%"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_asin_search_term(value: str | None) -> bool:
    search_term = (value or "").strip().upper()
    return bool(re.fullmatch(r"B0[A-Z0-9]{8,10}", search_term))


def _avg_bid_for(db: Session, campaign_name: str, ad_group_name: str, targeting: str) -> float | None:
    target = (
        db.execute(
            select(TargetingMetric)
            .where(TargetingMetric.campaign_name == campaign_name)
            .where(TargetingMetric.ad_group_name == ad_group_name)
            .where(TargetingMetric.targeting == targeting)
            .order_by(desc(TargetingMetric.created_at))
            .limit(1)
        )
        .scalar_one_or_none()
    )
    return target.bid if target else None


def _campaign_budget(db: Session, campaign_name: str) -> float | None:
    campaign = (
        db.execute(
            select(CampaignMetric)
            .where(CampaignMetric.campaign_name == campaign_name)
            .order_by(desc(CampaignMetric.created_at))
            .limit(1)
        )
        .scalar_one_or_none()
    )
    return campaign.budget if campaign else None


def _budget_limited(db: Session, campaign_name: str) -> bool:
    campaign = (
        db.execute(
            select(CampaignMetric)
            .where(CampaignMetric.campaign_name == campaign_name)
            .order_by(desc(CampaignMetric.created_at))
            .limit(1)
        )
        .scalar_one_or_none()
    )
    if not campaign:
        return False
    raw_status = _raw_text(campaign, "Budget Status", "预算状态", "Campaign Budget Status").lower()
    if any(term in raw_status for term in ["out of budget", "budget limited", "用完", "受限"]):
        return True
    budget = campaign.budget or 0
    spend = campaign.spend or 0
    return bool(budget and spend >= budget * 0.9)


def _reference_maps(db: Session) -> tuple[dict[tuple[str, str, str], float], dict[str, dict[str, Any]]]:
    target_rows = db.execute(select(TargetingMetric).order_by(desc(TargetingMetric.created_at))).scalars().all()
    bid_by_key = {}
    for row in target_rows:
        key = (row.campaign_name or "", row.ad_group_name or "", row.targeting or "")
        if key not in bid_by_key and row.bid is not None:
            bid_by_key[key] = row.bid

    campaign_rows = db.execute(select(CampaignMetric).order_by(desc(CampaignMetric.created_at))).scalars().all()
    campaign_by_name = {}
    for row in campaign_rows:
        name = row.campaign_name or ""
        if not name or name in campaign_by_name:
            continue
        raw_status = _raw_text(row, "Budget Status", "预算状态", "Campaign Budget Status").lower()
        budget = row.budget or 0
        spend = row.spend or 0
        campaign_by_name[name] = {
            "budget": row.budget,
            "budget_limited": any(term in raw_status for term in ["out of budget", "budget limited", "用完", "受限"])
            or bool(budget and spend >= budget * 0.9),
        }
    return bid_by_key, campaign_by_name


def _suggested_bid(current_bid: float | None, recommendation_type: str) -> float | None:
    if not current_bid:
        if recommendation_type in {"add_exact", "add_exact_boost", "add_phrase_test", "add_product_targeting_asin"}:
            return 0.75
        return None
    if recommendation_type == "add_product_targeting_asin":
        return round(current_bid * 1.1, 2)
    if recommendation_type == "add_exact_boost":
        return round(current_bid * 1.15, 2)
    if recommendation_type == "lower_bid":
        return round(current_bid * 0.85, 2)
    if recommendation_type == "add_phrase_test":
        return round(min(current_bid, current_bid * 0.9), 2)
    return round(current_bid, 2)


def _suggested_budget(current_budget: float | None, recommendation_type: str, clicks: float) -> float | None:
    if recommendation_type == "add_product_targeting_asin":
        return 10.0
    if recommendation_type not in {"increase_budget", "add_exact_boost"}:
        return None
    if not current_budget:
        return 10.0
    increase = 1.1 if clicks < 5 else 1.2
    return round(current_budget * increase, 2)


def _execution_action(recommendation_type: str) -> str:
    return {
        "add_exact": "add_keyword_to_exact_campaign",
        "add_exact_boost": "add_keyword_to_exact_campaign",
        "add_product_targeting_asin": "add_asin_to_product_targeting_campaign",
        "add_phrase_test": "add_keyword_small_budget_test",
        "negative_exact": "add_negative_exact_keyword",
        "negative_or_lower_bid": "add_negative_or_lower_bid",
        "lower_bid": "update_keyword_bid",
        "increase_budget": "update_campaign_budget",
    }.get(recommendation_type, "review_manually")


def _target_campaign(campaign_name: str, recommendation_type: str) -> str:
    if recommendation_type in {"add_exact", "add_exact_boost"}:
        return f"{campaign_name} - Exact"
    if recommendation_type == "add_product_targeting_asin":
        return f"{campaign_name} - Product Targeting"
    if recommendation_type == "add_phrase_test":
        return f"{campaign_name} - Phrase Test"
    return campaign_name


def build_execution_plan(recommendation: AdRecommendation) -> dict[str, Any]:
    target_ad_group = recommendation.ad_group_name or "Exact - Core Terms"
    if recommendation.recommendation_type == "add_product_targeting_asin":
        target_ad_group = "Product Targeting - ASIN Test"
    return {
        "action": _execution_action(recommendation.recommendation_type),
        "search_term": recommendation.search_term,
        "target_campaign": _target_campaign(recommendation.campaign_name or "", recommendation.recommendation_type),
        "target_ad_group": target_ad_group,
        "match_type": (
            "asin_product_targeting"
            if recommendation.recommendation_type == "add_product_targeting_asin"
            else ("phrase" if recommendation.recommendation_type == "add_phrase_test" else "exact")
        ),
        "target_asin": recommendation.search_term if recommendation.recommendation_type == "add_product_targeting_asin" else None,
        "suggested_bid": recommendation.suggested_bid,
        "suggested_daily_budget": recommendation.suggested_budget,
        "note": recommendation.reason,
        "safety_limits": {
            "manual_confirmation_required": True,
            "max_bulk_execute": 20,
            "max_bid_increase": "20%",
            "max_budget_increase": "20%",
            "low_sample_clicks_under_5": "only_small_budget_test",
            "api_enabled": get_settings().amazon_ads_api_enabled,
        },
    }


def _candidate_recommendations(db: Session) -> list[dict[str, Any]]:
    settings = get_settings()
    rows = db.execute(select(SearchTermMetric)).scalars().all()
    bid_by_key, campaign_by_name = _reference_maps(db)
    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        campaign = row.campaign_name or ""
        ad_group = row.ad_group_name or ""
        targeting = row.targeting or ""
        search_term = row.search_term or targeting
        match_type = _raw_text(row, "Match Type", "匹配类型")
        key = (campaign, ad_group, targeting, search_term or "", match_type)
        item = grouped[key]
        item["campaign_name"] = campaign
        item["ad_group_name"] = ad_group
        item["targeting"] = targeting
        item["search_term"] = search_term or ""
        item["match_type"] = match_type
        item["clicks"] += row.clicks or 0
        item["spend"] += row.spend or 0
        item["sales"] += row.sales or 0
        item["orders"] += row.orders or 0

    candidates = []
    for item in grouped.values():
        clicks = item["clicks"]
        spend = item["spend"]
        sales = item["sales"]
        orders = item["orders"]
        campaign = item["campaign_name"]
        ad_group = item["ad_group_name"]
        targeting = item["targeting"]
        acos = spend / sales if sales else None
        cpc = spend / clicks if clicks else None
        conversion_rate = orders / clicks if clicks else None
        current_bid = bid_by_key.get((campaign, ad_group, targeting))
        campaign_ref = campaign_by_name.get(campaign, {})
        current_budget = campaign_ref.get("budget")
        budget_limited = bool(campaign_ref.get("budget_limited"))

        def add(kind: str, text: str, reason: str, risk: str) -> None:
            candidates.append(
                {
                    **item,
                    "recommendation_type": kind,
                    "recommendation_text": text,
                    "reason": reason,
                    "risk_level": risk,
                    "acos": acos,
                    "cpc": cpc,
                    "conversion_rate": conversion_rate,
                    "suggested_bid": _suggested_bid(current_bid, kind),
                    "suggested_budget": _suggested_budget(current_budget, kind, clicks),
                    "budget_limited": budget_limited,
                }
            )

        is_asin_term = is_asin_search_term(item["search_term"])
        if is_asin_term:
            if orders >= 1 and acos is not None and acos <= 0.20:
                add(
                    "add_product_targeting_asin",
                    "该 ASIN 来自 substitutes 商品投放，已有订单且 ACOS 较低，建议将该 ASIN 单独加入手动 Product Targeting 活动进行测试。初始预算 $5-$10/天，竞价参考建议竞价或略高 10%，先观察 3-5 天。不建议立即在原自动广告中否定该 ASIN。",
                    f"该搜索词识别为 ASIN Product Target，订单 {orders:.0f}，ACOS {_pct(acos)}；不能作为 keyword exact 添加。",
                    "medium",
                )
            elif acos is not None and acos > 0.50 and orders > 0:
                add(
                    "lower_bid",
                    "降低商品投放出价 10%-20%，继续观察",
                    f"该搜索词识别为 ASIN Product Target，已有订单但 ACOS {_pct(acos)} 偏高；先降商品投放 bid，不直接关闭。",
                    "medium",
                )
            elif orders == 0 and (clicks >= 15 or spend >= settings.default_ad_test_cost):
                add(
                    "negative_or_lower_bid",
                    "降低商品投放出价，确认无关后再考虑否定 ASIN",
                    f"该搜索词识别为 ASIN Product Target，点击 {clicks:.0f}、花费 ${spend:.2f} 但无订单；先谨慎降 bid，不建议误加 keyword 否定。",
                    "medium",
                )
            continue

        if orders >= 2 and acos is not None and acos <= 0.10:
            add(
                "add_exact_boost",
                "加入 exact 活动并适度提高出价/预算",
                f"订单 {orders:.0f}，ACOS {_pct(acos)}，表现非常稳；预算/出价提高不得超过 20%。",
                "medium",
            )
        elif orders >= 1 and acos is not None and acos <= 0.20 and clicks >= 2:
            add(
                "add_exact",
                "将该搜索词加入 exact 精准广告活动",
                f"点击 {clicks:.0f}，订单 {orders:.0f}，ACOS {_pct(acos)}，适合单独精准承接。",
                "low",
            )
        if orders >= 1 and clicks < 5:
            add(
                "add_phrase_test",
                "加入 phrase 或 exact 小预算测试",
                f"已有订单但样本少，点击 {clicks:.0f}，只建议小预算测试，不允许大幅加价。",
                "low",
            )
        if clicks >= 15 and orders == 0:
            add(
                "negative_exact",
                "加入否定精准",
                f"点击 {clicks:.0f} 但无订单，优先否定精准，避免继续浪费。",
                "low",
            )
        elif spend >= settings.default_ad_test_cost and orders == 0:
            add(
                "negative_or_lower_bid",
                "加入否定词或降低出价",
                f"花费 ${spend:.2f} 已达到目标单次广告测试成本 ${settings.default_ad_test_cost:.2f}，仍无订单。",
                "medium",
            )
        if acos is not None and acos > 0.50 and orders > 0:
            add(
                "lower_bid",
                "降低出价 10%-20%，继续观察",
                f"已有订单但 ACOS {_pct(acos)} 偏高，先降 bid，不直接关闭。",
                "medium",
            )
        if acos is not None and acos <= 0.20 and orders >= 2 and budget_limited:
            add(
                "increase_budget",
                "适度增加预算",
                f"订单 {orders:.0f}，ACOS {_pct(acos)}，且 campaign 预算可能用完；预算提高不得超过 20%。",
                "medium",
            )
    return candidates


def generate_ad_recommendations(db: Session) -> int:
    created_or_updated = 0
    candidates = _candidate_recommendations(db)
    wrong_keyword_rows = (
        db.execute(
            select(AdRecommendation)
            .where(AdRecommendation.status.in_(["pending", "approved"]))
            .where(AdRecommendation.recommendation_type.in_(["add_exact", "add_exact_boost", "add_phrase_test"]))
        )
        .scalars()
        .all()
    )
    for row in wrong_keyword_rows:
        if is_asin_search_term(row.search_term):
            row.status = "rejected"
            row.execution_plan_json = None
            row.reason = f"{row.reason or ''} 系统已纠正：该搜索词是 ASIN Product Target，不能作为 keyword exact/phrase 添加。".strip()
            row.updated_at = datetime.utcnow()
    existing_rows = (
        db.execute(select(AdRecommendation).where(AdRecommendation.status.in_(["pending", "approved"])))
        .scalars()
        .all()
    )
    existing_by_key = {
        (
            row.campaign_name or "",
            row.ad_group_name or "",
            row.search_term or "",
            row.targeting or "",
            row.recommendation_type,
        ): row
        for row in existing_rows
    }
    for item in candidates:
        key = (
            item["campaign_name"] or "",
            item["ad_group_name"] or "",
            item["search_term"] or "",
            item["targeting"] or "",
            item["recommendation_type"],
        )
        existing = existing_by_key.get(key)
        target = existing or AdRecommendation(
            campaign_name=item["campaign_name"],
            ad_group_name=item["ad_group_name"],
            search_term=item["search_term"],
            targeting=item["targeting"],
            match_type=item["match_type"],
            recommendation_type=item["recommendation_type"],
            status="pending",
        )
        target.recommendation_text = item["recommendation_text"]
        target.reason = item["reason"]
        target.clicks = item["clicks"]
        target.spend = item["spend"]
        target.sales = item["sales"]
        target.orders = item["orders"]
        target.acos = item["acos"]
        target.suggested_bid = item["suggested_bid"]
        target.suggested_budget = item["suggested_budget"]
        target.risk_level = item["risk_level"]
        target.updated_at = datetime.utcnow()
        if not existing:
            db.add(target)
        created_or_updated += 1
    db.commit()
    return created_or_updated


def approve_recommendation(db: Session, recommendation_id: int) -> AdRecommendation:
    recommendation = db.get(AdRecommendation, recommendation_id)
    if not recommendation:
        raise ValueError("广告建议不存在。")
    if recommendation.status in {"executed", "failed"}:
        raise ValueError("已执行或失败的建议不能重复确认。")
    recommendation.status = "approved"
    recommendation.execution_plan_json = json.dumps(build_execution_plan(recommendation), ensure_ascii=False)
    recommendation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recommendation)
    return recommendation


def reject_recommendation(db: Session, recommendation_id: int) -> AdRecommendation:
    recommendation = db.get(AdRecommendation, recommendation_id)
    if not recommendation:
        raise ValueError("广告建议不存在。")
    if recommendation.status == "executed":
        raise ValueError("已处理的建议不能拒绝。")
    recommendation.status = "rejected"
    recommendation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recommendation)
    return recommendation


def mark_manual_recommendation(db: Session, recommendation_id: int) -> AdRecommendation:
    recommendation = db.get(AdRecommendation, recommendation_id)
    if not recommendation:
        raise ValueError("广告建议不存在。")
    recommendation.status = "executed"
    recommendation.api_response_json = json.dumps({"manual": True, "handled_at": datetime.utcnow().isoformat()}, ensure_ascii=False)
    recommendation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recommendation)
    return recommendation


def count_recommendations(
    db: Session,
    status: str | None = None,
    recommendation_type: str | None = None,
    acos_max: float | None = None,
    orders_positive: bool = False,
    spend_positive: bool = False,
) -> int:
    query = select(func.count(AdRecommendation.id))
    query = _apply_filters(query, status, recommendation_type, acos_max, orders_positive, spend_positive)
    return db.execute(query).scalar_one()


def list_recommendations(
    db: Session,
    limit: int,
    offset: int,
    status: str | None = None,
    recommendation_type: str | None = None,
    acos_max: float | None = None,
    orders_positive: bool = False,
    spend_positive: bool = False,
) -> list[AdRecommendation]:
    query = select(AdRecommendation).order_by(desc(AdRecommendation.created_at), desc(AdRecommendation.spend))
    query = _apply_filters(query, status, recommendation_type, acos_max, orders_positive, spend_positive)
    return db.execute(query.offset(offset).limit(limit)).scalars().all()


def _apply_filters(query, status, recommendation_type, acos_max, orders_positive, spend_positive):
    if status:
        query = query.where(AdRecommendation.status == status)
    if recommendation_type:
        query = query.where(AdRecommendation.recommendation_type == recommendation_type)
    if acos_max is not None:
        query = query.where(AdRecommendation.acos <= acos_max)
    if orders_positive:
        query = query.where(AdRecommendation.orders > 0)
    if spend_positive:
        query = query.where(AdRecommendation.spend > 0)
    return query
