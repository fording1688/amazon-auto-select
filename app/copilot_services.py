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
from app.models import AdsDaily, ImportBatch, InventoryDaily, InventoryItem, Recommendation, SalesDaily, SearchTerm, SearchTermMetric
from app.report_importer import (
    _alias_map,
    _get,
    _json,
    _row_marketplace,
    _row_period,
    _apply_batch_scope,
    _batch_filter_ids,
    build_sku_dashboard,
    ensure_store,
    import_report,
    list_stores,
    parse_tabular_file,
    row_data_hash,
    to_float,
)

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


def import_copilot_report(
    db: Session,
    report_type: str,
    file_name: str,
    content: bytes,
    duplicate_strategy: str = "prompt",
    uploaded_by: str | None = None,
    marketplace: str = "US",
    store_name: str | None = None,
    business_date: datetime | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    normalized = REPORT_TYPE_MAP.get(report_type, report_type)
    batch = import_report(
        db,
        normalized,
        file_name,
        content,
        duplicate_strategy,
        uploaded_by,
        marketplace,
        store_name=store_name,
        business_date=business_date,
        user_id=user_id,
    )
    synced_rows = 0
    if batch.status == "success":
        synced_rows = _sync_copilot_tables(db, batch.id, normalized, file_name, content, duplicate_strategy, marketplace, user_id=user_id)
    generated = 0
    if normalized in {"search_terms", "campaigns"} and batch.status == "success":
        generated = generate_ad_recommendations(db)
    return {
        "batch_id": batch.id,
        "report_type": normalized,
        "file_name": batch.file_name,
        "store_id": batch.store_id,
        "store_name": batch.store_name,
        "business_date": batch.business_date,
        "project_name": batch.project_name,
        "row_count": batch.row_count,
        "status": batch.status,
        "error_message": batch.error_message,
        "duplicate_count": batch.duplicate_count,
        "period_start": batch.period_start,
        "period_end": batch.period_end,
        "synced_rows": synced_rows,
        "generated_ad_recommendations": generated,
    }


def store_options(db: Session, user_id: int | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": store.id,
            "name": store.name,
            "marketplace": store.marketplace,
            "status": store.status,
        }
        for store in list_stores(db, user_id=user_id)
    ]


def create_store(db: Session, name: str, marketplace: str = "US", user_id: int | None = None) -> dict[str, Any]:
    store = ensure_store(db, name, marketplace, user_id=user_id)
    return {"id": store.id, "name": store.name, "marketplace": store.marketplace, "status": store.status}


def batch_context_options(db: Session, store_id: int | None = None, user_id: int | None = None) -> dict[str, Any]:
    query = select(ImportBatch).where(ImportBatch.status == "success").order_by(desc(ImportBatch.business_date), desc(ImportBatch.uploaded_at))
    if user_id:
        query = query.where(ImportBatch.user_id == user_id)
    if store_id:
        query = query.where(ImportBatch.store_id == store_id)
    batches = db.execute(query.limit(100)).scalars().all()
    return {
        "stores": store_options(db, user_id=user_id),
        "batches": [
            {
                "id": batch.id,
                "store_id": batch.store_id,
                "store_name": batch.store_name,
                "business_date": batch.business_date,
                "project_name": batch.project_name,
                "report_type": batch.report_type,
                "file_name": batch.file_name,
                "row_count": batch.row_count,
                "uploaded_at": batch.uploaded_at,
            }
            for batch in batches
        ],
    }


def _sync_copilot_tables(
    db: Session,
    batch_id: int,
    report_type: str,
    file_name: str,
    content: bytes,
    duplicate_strategy: str,
    marketplace: str,
    user_id: int | None = None,
) -> int:
    if report_type not in {"business", "search_terms", "campaigns", "inventory"}:
        return 0
    rows = parse_tabular_file(file_name, content)
    model_by_type = {
        "business": SalesDaily,
        "search_terms": SearchTerm,
        "campaigns": AdsDaily,
        "inventory": InventoryDaily,
    }
    model = model_by_type[report_type]
    prepared = []
    for row in rows:
        alias = _alias_map(list(row.keys()))
        row_marketplace = _row_marketplace(row, alias, marketplace)
        report_date, period_start, period_end = _row_period(row, alias)
        data_hash = row_data_hash(report_type, row, alias, row_marketplace)
        prepared.append((row, alias, row_marketplace, report_date, period_start, period_end, data_hash))
    hashes = [item[-1] for item in prepared]
    duplicate_hashes = set()
    if hashes:
        duplicate_query = select(model.data_hash).where(model.data_hash.in_(hashes)).where(model.is_active.is_(True))
        if user_id:
            duplicate_query = duplicate_query.where(model.user_id == user_id)
        duplicate_hashes = set(db.execute(duplicate_query).scalars().all())
    if duplicate_hashes and duplicate_strategy == "overwrite":
        update_query = db.query(model).filter(model.data_hash.in_(duplicate_hashes))
        if user_id:
            update_query = update_query.filter(model.user_id == user_id)
        update_query.update({"is_active": False}, synchronize_session=False)
    inserted = 0
    for row, alias, row_marketplace, report_date, period_start, period_end, data_hash in prepared:
        if data_hash in duplicate_hashes and duplicate_strategy == "skip":
            continue
        is_active = not (data_hash in duplicate_hashes and duplicate_strategy == "preserve_inactive")
        raw_json = _json(row)
        common = {
            "user_id": user_id,
            "import_batch_id": batch_id,
            "marketplace": row_marketplace,
            "date": report_date,
            "report_date": report_date,
            "period_start": period_start,
            "period_end": period_end,
            "is_active": is_active,
            "data_hash": data_hash,
            "raw_json": raw_json,
        }
        if report_type == "business":
            db.add(
                SalesDaily(
                    **common,
                    sku=str(_get(row, alias, "sku")).strip() or None,
                    asin=str(_get(row, alias, "asin")).strip() or None,
                    sales=to_float(_get(row, alias, "ordered_sales")),
                    orders=to_float(_get(row, alias, "orders")),
                    units=to_float(_get(row, alias, "units_ordered")),
                    sessions=to_float(_get(row, alias, "sessions")),
                    conversion_rate=to_float(_get(row, alias, "conversion_rate")),
                )
            )
        elif report_type == "search_terms":
            clicks = to_float(_get(row, alias, "clicks")) or 0
            orders = to_float(_get(row, alias, "orders")) or 0
            db.add(
                SearchTerm(
                    **common,
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
                )
            )
        elif report_type == "campaigns":
            clicks = to_float(_get(row, alias, "clicks")) or 0
            spend = to_float(_get(row, alias, "spend")) or 0
            db.add(
                AdsDaily(
                    **common,
                    campaign_name=str(_get(row, alias, "campaign_name")).strip() or None,
                    impressions=to_float(_get(row, alias, "impressions")),
                    clicks=clicks,
                    spend=spend,
                    sales=to_float(_get(row, alias, "ad_sales")),
                    orders=to_float(_get(row, alias, "orders")),
                    acos=to_float(_get(row, alias, "acos")),
                    cpc=spend / clicks if clicks else None,
                )
            )
        elif report_type == "inventory":
            db.add(
                InventoryDaily(
                    **common,
                    sku=str(_get(row, alias, "sku")).strip() or None,
                    asin=str(_get(row, alias, "asin")).strip() or None,
                    available=to_float(_get(row, alias, "available")),
                    inbound=to_float(_get(row, alias, "inbound")),
                    reserved=to_float(_get(row, alias, "reserved")),
                    days_of_supply=to_float(_get(row, alias, "days_of_supply")),
                )
            )
        inserted += 1
    db.commit()
    return inserted


def sku_health_center(
    db: Session,
    store_id: int | None = None,
    business_date: datetime | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    rows = build_sku_dashboard(db, store_id=store_id, business_date=business_date, user_id=user_id)
    latest_inventory = _latest_inventory_by_key(db, store_id=store_id, business_date=business_date, user_id=user_id)
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
                "image_url": row.image_url,
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


def ads_diagnosis_center(
    db: Session,
    target_acos: float = TARGET_ACOS,
    store_id: int | None = None,
    business_date: datetime | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    batch_ids = _batch_filter_ids(db, store_id, business_date, user_id=user_id)
    query = select(SearchTermMetric).where(SearchTermMetric.is_active.is_(True)).order_by(desc(SearchTermMetric.spend))
    query = _apply_batch_scope(query, SearchTermMetric, batch_ids)
    rows = db.execute(query).scalars().all()
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


def daily_operations_report(
    db: Session,
    store_id: int | None = None,
    business_date: datetime | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    health = sku_health_center(db, store_id=store_id, business_date=business_date, user_id=user_id)
    ads = ads_diagnosis_center(db, store_id=store_id, business_date=business_date, user_id=user_id)
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
    _save_report_recommendations(db, report, user_id=user_id)
    return report


def _latest_inventory_by_key(
    db: Session,
    store_id: int | None = None,
    business_date: datetime | None = None,
    user_id: int | None = None,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    batch_ids = _batch_filter_ids(db, store_id, business_date, user_id=user_id)
    query = select(InventoryItem).where(InventoryItem.is_active.is_(True)).order_by(desc(InventoryItem.created_at))
    query = _apply_batch_scope(query, InventoryItem, batch_ids)
    rows = db.execute(query).scalars().all()
    for row in rows:
        data = {"days_of_supply": row.days_of_supply, "available": row.available, "inbound": row.inbound}
        for key in [row.sku, row.asin]:
            if key and key not in result:
                result[key] = data
    return result


def _save_report_recommendations(db: Session, report: dict[str, Any], user_id: int | None = None) -> None:
    for index, action in enumerate(report.get("today_recommended_actions", [])[:10]):
        db.add(
            Recommendation(
                user_id=user_id,
                recommendation_type="daily_action",
                priority="P0" if index < 3 else "P1",
                title="每日运营动作",
                content=action,
                source_json=json.dumps(report, ensure_ascii=False),
            )
        )
    db.commit()
