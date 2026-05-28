from __future__ import annotations

import io
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ad_recommendations import generate_ad_recommendations, is_asin_search_term
from app.models import AdsDaily, InventoryDaily, InventoryItem, Recommendation, SalesDaily, SearchTerm, SearchTermMetric
from app.report_importer import _alias_map, _get, _json, build_sku_dashboard, import_report, parse_tabular_file, to_float

REPORT_TYPE_MAP = {
    "business_report": "business",
    "business": "business",
    "search_term_report": "search_terms",
    "search_terms": "search_terms",
    "campaign_report": "campaigns",
    "campaigns": "campaigns",
    "inventory_report": "inventory",
    "inventory": "inventory",
    "product_cost": "costs",
    "costs": "costs",
}

TARGET_ACOS = 0.25


def import_copilot_report(db: Session, report_type: str, file_name: str, content: bytes) -> dict[str, Any]:
    normalized = REPORT_TYPE_MAP.get(report_type, report_type)
    batch = import_report(db, normalized, file_name, content)
    synced_rows = 0
    if batch.status == "success":
        synced_rows = _sync_copilot_tables(db, normalized, file_name, content)
    generated = 0
    if normalized in {"search_terms", "campaigns"} and batch.status == "success":
        generated = generate_ad_recommendations(db)
    return {
        "batch_id": batch.id,
        "report_type": normalized,
        "file_name": batch.file_name,
        "row_count": batch.row_count,
        "status": batch.status,
        "error_message": batch.error_message,
        "synced_rows": synced_rows,
        "generated_ad_recommendations": generated,
    }


def _sync_copilot_tables(db: Session, report_type: str, file_name: str, content: bytes) -> int:
    if report_type not in {"business", "search_terms", "campaigns", "inventory"}:
        return 0
    rows = parse_tabular_file(file_name, content)
    for row in rows:
        alias = _alias_map(list(row.keys()))
        raw_json = _json(row)
        if report_type == "business":
            db.add(
                SalesDaily(
                    sku=str(_get(row, alias, "sku")).strip() or None,
                    asin=str(_get(row, alias, "asin")).strip() or None,
                    date=None,
                    sales=to_float(_get(row, alias, "ordered_sales")),
                    orders=to_float(_get(row, alias, "orders")),
                    units=to_float(_get(row, alias, "units_ordered")),
                    sessions=to_float(_get(row, alias, "sessions")),
                    conversion_rate=to_float(_get(row, alias, "conversion_rate")),
                    raw_json=raw_json,
                )
            )
        elif report_type == "search_terms":
            clicks = to_float(_get(row, alias, "clicks")) or 0
            orders = to_float(_get(row, alias, "orders")) or 0
            db.add(
                SearchTerm(
                    sku=str(_get(row, alias, "sku")).strip() or None,
                    asin=str(_get(row, alias, "asin")).strip() or None,
                    campaign_name=str(_get(row, alias, "campaign_name")).strip() or None,
                    ad_group_name=str(_get(row, alias, "ad_group_name")).strip() or None,
                    targeting=str(_get(row, alias, "targeting")).strip() or None,
                    match_type=str(_get(row, alias, "match_type")).strip() or None,
                    customer_search_term=str(_get(row, alias, "search_term")).strip() or None,
                    impressions=to_float(_get(row, alias, "impressions")),
                    clicks=clicks,
                    spend=to_float(_get(row, alias, "spend")),
                    sales=to_float(_get(row, alias, "ad_sales")),
                    orders=orders,
                    acos=to_float(_get(row, alias, "acos")),
                    cpc=(to_float(_get(row, alias, "spend")) or 0) / clicks if clicks else None,
                    conversion_rate=orders / clicks if clicks else None,
                    raw_json=raw_json,
                )
            )
        elif report_type == "campaigns":
            clicks = to_float(_get(row, alias, "clicks")) or 0
            spend = to_float(_get(row, alias, "spend")) or 0
            db.add(
                AdsDaily(
                    campaign_name=str(_get(row, alias, "campaign_name")).strip() or None,
                    impressions=to_float(_get(row, alias, "impressions")),
                    clicks=clicks,
                    spend=spend,
                    sales=to_float(_get(row, alias, "ad_sales")),
                    orders=to_float(_get(row, alias, "orders")),
                    acos=to_float(_get(row, alias, "acos")),
                    cpc=spend / clicks if clicks else None,
                    raw_json=raw_json,
                )
            )
        elif report_type == "inventory":
            db.add(
                InventoryDaily(
                    sku=str(_get(row, alias, "sku")).strip() or None,
                    asin=str(_get(row, alias, "asin")).strip() or None,
                    available=to_float(_get(row, alias, "available")),
                    inbound=to_float(_get(row, alias, "inbound")),
                    reserved=to_float(_get(row, alias, "reserved")),
                    days_of_supply=to_float(_get(row, alias, "days_of_supply")),
                    raw_json=raw_json,
                )
            )
    db.commit()
    return len(rows)


def sku_health_center(db: Session) -> list[dict[str, Any]]:
    rows = build_sku_dashboard(db)
    latest_inventory = _latest_inventory_by_key(db)
    health_rows = []
    for row in rows:
        inv = latest_inventory.get(row.sku) or latest_inventory.get(row.asin) or {}
        days = inv.get("days_of_supply")
        score = 100
        tags = list(row.tags)
        actions = list(row.recommendations)
        if row.margin is not None and row.margin < 0.15:
            score -= 22
            tags.append("利润风险")
        if row.acos is not None and row.acos > 0.5:
            score -= 18
            tags.append("广告 ACOS 高")
        if row.conversion_rate is not None and row.conversion_rate < 0.05 and row.sessions >= 100:
            score -= 16
            tags.append("转化低")
        if days is not None and days < 14:
            score -= 24
            tags.append("库存风险")
            actions.append("可售天数低于 14 天，优先补货或降低广告放量。")
        if row.sales >= 50 and (row.margin or 0) >= 0.25 and (row.tacos or 0) <= 0.18:
            score += 8
            tags.append("潜力 SKU")
            actions.append("利润和 TACOS 表现较好，可测试 exact 加预算或多件装。")
        health_rows.append(
            {
                "sku": row.sku,
                "asin": row.asin,
                "title": row.title,
                "sales": row.sales,
                "orders": row.units,
                "ad_spend": row.ad_spend,
                "acos": row.acos,
                "tacos": row.tacos,
                "conversion_rate": row.conversion_rate,
                "estimated_profit": row.estimated_profit,
                "margin": row.margin,
                "inventory_days": days,
                "health_score": max(0, min(100, round(score))),
                "problem_tags": sorted(set(tags)),
                "recommended_actions": actions[:5],
            }
        )
    return sorted(health_rows, key=lambda item: item["health_score"])


def ads_diagnosis_center(db: Session, target_acos: float = TARGET_ACOS) -> dict[str, Any]:
    rows = db.execute(select(SearchTermMetric).order_by(desc(SearchTermMetric.spend))).scalars().all()
    diagnosis = {
        "profitable_terms": [],
        "potential_terms": [],
        "waste_terms": [],
        "irrelevant_terms": [],
        "negative_keywords": [],
        "exact_keywords": [],
        "product_target_asins": [],
    }
    for row in rows:
        clicks = row.clicks or 0
        spend = row.spend or 0
        sales = row.sales or 0
        orders = row.orders or 0
        acos = row.acos if row.acos is not None else (spend / sales if sales else None)
        cvr = orders / clicks if clicks else 0
        ctr = (clicks / row.impressions) if row.impressions else None
        item = {
            "campaign_name": row.campaign_name,
            "ad_group_name": row.ad_group_name,
            "search_term": row.search_term,
            "traffic_type": "asin_product_target" if is_asin_search_term(row.search_term) else "keyword_search_term",
            "targeting": row.targeting,
            "clicks": clicks,
            "spend": spend,
            "sales": sales,
            "orders": orders,
            "acos": acos,
            "ctr": ctr,
            "cvr": cvr,
        }
        if item["traffic_type"] == "asin_product_target":
            if orders > 0 and acos is not None and acos <= target_acos:
                reason = "ASIN 商品流量已有订单且 ACOS 低于目标，适合单独 Product Targeting 小预算验证。"
                diagnosis["profitable_terms"].append({**item, "reason": reason})
                diagnosis["product_target_asins"].append(
                    {
                        **item,
                        "action": "建议加入手动 Product Targeting 商品投放活动，预算 $5-$10/天，竞价参考建议竞价或略高 10%，观察 3-5 天；暂不在原自动广告中否定该 ASIN。",
                    }
                )
            elif clicks >= 15 and orders == 0:
                diagnosis["waste_terms"].append({**item, "reason": "ASIN 商品流量点击 >= 15 且无订单，疑似商品投放浪费。"})
                diagnosis["negative_keywords"].append({**item, "action": "先降低商品投放 bid，确认明显无关后再考虑否定 ASIN。"})
            elif orders > 0:
                diagnosis["potential_terms"].append({**item, "reason": "ASIN 商品流量有订单但 ACOS 偏高或样本较少，先小预算观察。"})
        else:
            if clicks >= 15 and orders == 0:
                diagnosis["waste_terms"].append({**item, "reason": "点击 >= 15 且无订单，广告浪费明显。"})
                diagnosis["negative_keywords"].append({**item, "action": "建议否定精准或降 bid。"})
            elif orders > 0 and acos is not None and acos <= target_acos:
                diagnosis["profitable_terms"].append({**item, "reason": "关键词已有订单且 ACOS 低于目标 ACOS。"})
                diagnosis["exact_keywords"].append({**item, "action": "建议拆 exact 精准投放。"})
            elif orders > 0 and clicks < 5:
                diagnosis["potential_terms"].append({**item, "reason": "关键词已有订单但样本少，适合 phrase 或 exact 小预算测试。"})
            elif orders > 0 and acos is not None and acos > target_acos:
                diagnosis["potential_terms"].append({**item, "reason": "关键词有订单但 ACOS 高，建议降低竞价。"})
        if ctr is not None and ctr < 0.002 and (row.impressions or 0) >= 2000:
            diagnosis["irrelevant_terms"].append({**item, "reason": "CTR 低，可能主图/标题或流量相关性有问题。"})
        if clicks >= 20 and cvr < 0.03:
            diagnosis["irrelevant_terms"].append({**item, "reason": "CVR 低，优先检查 Listing、价格、评价和流量相关性。"})
    return {key: value[:50] for key, value in diagnosis.items()}


def profit_calculator(payload: dict[str, Any]) -> dict[str, float]:
    price = float(payload.get("price") or 0)
    purchase_cost = float(payload.get("purchase_cost") or 0)
    logistics_cost = float(payload.get("logistics_cost") or 0)
    fba_fee = float(payload.get("fba_fee") or 0)
    referral_fee_rate = float(payload.get("referral_fee_rate") or 0.15)
    ad_spend = float(payload.get("ad_spend") or 0)
    referral_fee = price * referral_fee_rate
    gross_profit = price - purchase_cost - logistics_cost - fba_fee - referral_fee
    net_profit = gross_profit - ad_spend
    gross_margin = gross_profit / price if price else 0
    post_ad_margin = net_profit / price if price else 0
    max_acceptable_acos = gross_margin
    return {
        "price": price,
        "referral_fee": round(referral_fee, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "gross_margin": round(gross_margin, 4),
        "post_ad_profit_margin": round(post_ad_margin, 4),
        "max_acceptable_acos": round(max_acceptable_acos, 4),
    }


def daily_operations_report(db: Session) -> dict[str, Any]:
    health = sku_health_center(db)
    ads = ads_diagnosis_center(db)
    urgent = []
    potential = []
    for sku in health:
        if sku["health_score"] < 60:
            urgent.append(f"{sku['sku']} 健康分 {sku['health_score']}，问题：{', '.join(sku['problem_tags'][:3])}")
        if "潜力 SKU" in sku["problem_tags"]:
            potential.append(f"{sku['sku']} 利润和广告承受力较好，可小幅放量。")
    actions = []
    for item in ads["waste_terms"][:5]:
        if item.get("traffic_type") == "asin_product_target":
            actions.append(f"商品投放止损：{item['search_term']} 点击 {item['clicks']:.0f} 无订单，先降低 bid，确认无关后再否定 ASIN。")
        else:
            actions.append(f"广告止损：{item['search_term']} 点击 {item['clicks']:.0f} 无订单，建议否定精准或降 bid。")
    for item in ads.get("product_target_asins", [])[:5]:
        actions.append(f"ASIN 放量测试：{item['search_term']} ACOS {((item['acos'] or 0) * 100):.1f}%，建议 Product Targeting 小预算承接。")
    for item in ads["profitable_terms"][:5]:
        if item.get("traffic_type") == "asin_product_target":
            continue
        actions.append(f"放量词：{item['search_term']} ACOS {((item['acos'] or 0) * 100):.1f}%，建议 exact 承接。")
    report = {
        "today_main_issues": urgent[:10],
        "today_potential_skus": potential[:10],
        "today_ad_waste_points": ads["waste_terms"][:10],
        "today_recommended_actions": actions[:15],
        "priority_order": ["先处理库存风险和亏损 SKU", "再处理烧钱搜索词", "最后放大低 ACOS 盈利词和潜力 SKU"],
    }
    _save_report_recommendations(db, report)
    return report


def _latest_inventory_by_key(db: Session) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    rows = db.execute(select(InventoryItem).order_by(desc(InventoryItem.created_at))).scalars().all()
    for row in rows:
        data = {"days_of_supply": row.days_of_supply, "available": row.available, "inbound": row.inbound}
        for key in [row.sku, row.asin]:
            if key and key not in result:
                result[key] = data
    return result


def _save_report_recommendations(db: Session, report: dict[str, Any]) -> None:
    for index, action in enumerate(report.get("today_recommended_actions", [])[:10]):
        db.add(
            Recommendation(
                recommendation_type="daily_action",
                priority="P0" if index < 3 else "P1",
                title="每日运营动作",
                content=action,
                source_json=json.dumps(report, ensure_ascii=False),
            )
        )
    db.commit()
