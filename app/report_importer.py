from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    AdvertisedProductMetric,
    BusinessMetric,
    CostItem,
    ImportBatch,
    ListingItem,
    SearchTermMetric,
)


REPORT_TYPES = {
    "business": "Business Report",
    "search_terms": "Advertising Search Term Report",
    "advertised_products": "Advertised Product Report",
    "costs": "成本表",
    "listings": "Listing 基础信息表",
}


ALIASES = {
    "sku": ["sku", "childsku", "seller sku", "advertisedsku", "advertised sku", "merchant sku"],
    "asin": ["asin", "childasin", "child asin", "advertisedasin", "advertised asin"],
    "title": ["title", "product name", "productname", "item name"],
    "sessions": ["sessions", "sessions total", "total sessions"],
    "page_views": ["page views", "pageviews", "page views total"],
    "units_ordered": ["units ordered", "unitsordered", "ordered units", "units"],
    "ordered_sales": ["ordered product sales", "orderedproductsales", "sales", "ordered revenue"],
    "conversion_rate": ["unit session percentage", "unit session %", "conversion rate", "cvr"],
    "buy_box_percentage": ["buy box percentage", "buy box %"],
    "campaign_name": ["campaign name", "campaign"],
    "ad_group_name": ["ad group name", "ad group"],
    "targeting": ["targeting", "target", "keyword", "keyword or product targeting"],
    "search_term": ["customer search term", "search term", "customersearchterm"],
    "impressions": ["impressions"],
    "clicks": ["clicks"],
    "spend": ["spend", "cost", "ad spend"],
    "ad_sales": ["7 day total sales", "14 day total sales", "sales", "total sales"],
    "orders": ["7 day total orders", "14 day total orders", "orders", "total orders"],
    "acos": ["acos", "total advertising cost of sales acos", "advertising cost of sales"],
    "purchase_cost": ["purchase cost", "product cost", "unit cost", "采购成本"],
    "first_leg_shipping": ["first leg shipping", "shipping cost", "头程", "头程运费"],
    "packaging_cost": ["packaging cost", "package cost", "包装成本"],
    "fba_fee": ["fba fee", "fulfillment fee", "配送费"],
    "referral_fee_rate": ["referral fee rate", "commission rate", "佣金比例"],
    "other_cost": ["other cost", "misc cost", "其他成本"],
    "target_margin": ["target margin", "目标利润率"],
    "product_name": ["product name", "product", "产品名称"],
    "bullet_1": ["bullet 1", "bullet_1", "bullet point 1"],
    "bullet_2": ["bullet 2", "bullet_2", "bullet point 2"],
    "bullet_3": ["bullet 3", "bullet_3", "bullet point 3"],
    "bullet_4": ["bullet 4", "bullet_4", "bullet point 4"],
    "bullet_5": ["bullet 5", "bullet_5", "bullet point 5"],
    "price": ["price", "售价", "sale price"],
    "coupon": ["coupon", "优惠券"],
    "main_image_url": ["main image url", "image url", "main_image_url"],
}


@dataclass
class SkuSummary:
    sku: str
    asin: str
    title: str
    sales: float
    units: float
    sessions: float
    conversion_rate: float | None
    ad_spend: float
    ad_sales: float
    ad_orders: float
    acos: float | None
    tacos: float | None
    unit_cost: float
    estimated_profit: float
    margin: float | None
    tags: list[str]
    recommendations: list[str]


def normalize_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(value or "").strip().lower())


def _alias_map(headers: list[str]) -> dict[str, str]:
    normalized = {normalize_header(header): header for header in headers}
    result = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            hit = normalized.get(normalize_header(alias))
            if hit:
                result[canonical] = hit
                break
    return result


def _get(row: dict, alias: dict[str, str], key: str, default: str = ""):
    source = alias.get(key)
    return row.get(source, default) if source else default


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "").replace("USD", "")
    is_percent = "%" in text
    text = text.replace("%", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if is_percent and number > 1:
        return number / 100
    return number


def _json(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, default=str)


def parse_tabular_file(file_name: str, content: bytes) -> list[dict]:
    lower = file_name.lower()
    if lower.endswith(".csv") or lower.endswith(".tsv"):
        text = content.decode("utf-8-sig", errors="ignore")
        dialect = csv.excel_tab if lower.endswith(".tsv") else csv.excel
        return [dict(row) for row in csv.DictReader(io.StringIO(text), dialect=dialect)]
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(value or "").strip() for value in rows[0]]
        parsed = []
        for values in rows[1:]:
            if not any(value not in (None, "") for value in values):
                continue
            parsed.append({headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))})
        return parsed
    raise ValueError("只支持 CSV、TSV、XLSX、XLSM 文件。")


def import_report(db: Session, report_type: str, file_name: str, content: bytes) -> ImportBatch:
    if report_type not in REPORT_TYPES:
        raise ValueError("未知报表类型")
    batch = ImportBatch(report_type=report_type, file_name=file_name, status="running")
    db.add(batch)
    db.commit()
    db.refresh(batch)
    try:
        rows = parse_tabular_file(file_name, content)
        if not rows:
            raise ValueError("文件没有可读取的数据行。")
        alias = _alias_map(list(rows[0].keys()))
        for row in rows:
            _insert_row(db, batch.id, report_type, row, alias)
        batch.status = "success"
        batch.row_count = len(rows)
    except Exception as exc:
        batch.status = "failed"
        batch.error_message = str(exc)
    db.commit()
    db.refresh(batch)
    return batch


def _insert_row(db: Session, batch_id: int, report_type: str, row: dict, alias: dict[str, str]) -> None:
    common = {"batch_id": batch_id, "raw_json": _json(row)}
    if report_type == "business":
        db.add(
            BusinessMetric(
                **common,
                sku=str(_get(row, alias, "sku")).strip() or None,
                asin=str(_get(row, alias, "asin")).strip() or None,
                title=str(_get(row, alias, "title")).strip() or None,
                sessions=to_float(_get(row, alias, "sessions")),
                page_views=to_float(_get(row, alias, "page_views")),
                units_ordered=to_float(_get(row, alias, "units_ordered")),
                ordered_sales=to_float(_get(row, alias, "ordered_sales")),
                conversion_rate=to_float(_get(row, alias, "conversion_rate")),
                buy_box_percentage=to_float(_get(row, alias, "buy_box_percentage")),
            )
        )
    elif report_type == "search_terms":
        db.add(
            SearchTermMetric(
                **common,
                campaign_name=str(_get(row, alias, "campaign_name")).strip() or None,
                ad_group_name=str(_get(row, alias, "ad_group_name")).strip() or None,
                targeting=str(_get(row, alias, "targeting")).strip() or None,
                search_term=str(_get(row, alias, "search_term")).strip() or None,
                impressions=to_float(_get(row, alias, "impressions")),
                clicks=to_float(_get(row, alias, "clicks")),
                spend=to_float(_get(row, alias, "spend")),
                sales=to_float(_get(row, alias, "ad_sales")),
                orders=to_float(_get(row, alias, "orders")),
                acos=to_float(_get(row, alias, "acos")),
            )
        )
    elif report_type == "advertised_products":
        db.add(
            AdvertisedProductMetric(
                **common,
                sku=str(_get(row, alias, "sku")).strip() or None,
                asin=str(_get(row, alias, "asin")).strip() or None,
                campaign_name=str(_get(row, alias, "campaign_name")).strip() or None,
                impressions=to_float(_get(row, alias, "impressions")),
                clicks=to_float(_get(row, alias, "clicks")),
                spend=to_float(_get(row, alias, "spend")),
                sales=to_float(_get(row, alias, "ad_sales")),
                orders=to_float(_get(row, alias, "orders")),
                acos=to_float(_get(row, alias, "acos")),
            )
        )
    elif report_type == "costs":
        db.add(
            CostItem(
                **common,
                sku=str(_get(row, alias, "sku")).strip() or None,
                asin=str(_get(row, alias, "asin")).strip() or None,
                product_name=str(_get(row, alias, "product_name")).strip() or None,
                purchase_cost=to_float(_get(row, alias, "purchase_cost")),
                first_leg_shipping=to_float(_get(row, alias, "first_leg_shipping")),
                packaging_cost=to_float(_get(row, alias, "packaging_cost")),
                fba_fee=to_float(_get(row, alias, "fba_fee")),
                referral_fee_rate=to_float(_get(row, alias, "referral_fee_rate")),
                other_cost=to_float(_get(row, alias, "other_cost")),
                target_margin=to_float(_get(row, alias, "target_margin")),
            )
        )
    elif report_type == "listings":
        db.add(
            ListingItem(
                **common,
                sku=str(_get(row, alias, "sku")).strip() or None,
                asin=str(_get(row, alias, "asin")).strip() or None,
                title=str(_get(row, alias, "title")).strip() or None,
                bullet_1=str(_get(row, alias, "bullet_1")).strip() or None,
                bullet_2=str(_get(row, alias, "bullet_2")).strip() or None,
                bullet_3=str(_get(row, alias, "bullet_3")).strip() or None,
                bullet_4=str(_get(row, alias, "bullet_4")).strip() or None,
                bullet_5=str(_get(row, alias, "bullet_5")).strip() or None,
                price=to_float(_get(row, alias, "price")),
                coupon=str(_get(row, alias, "coupon")).strip() or None,
                main_image_url=str(_get(row, alias, "main_image_url")).strip() or None,
            )
        )


def latest_batches(db: Session) -> list[ImportBatch]:
    return db.execute(select(ImportBatch).order_by(desc(ImportBatch.created_at)).limit(30)).scalars().all()


def build_sku_dashboard(db: Session) -> list[SkuSummary]:
    business_rows = db.execute(select(BusinessMetric)).scalars().all()
    ad_rows = db.execute(select(AdvertisedProductMetric)).scalars().all()
    costs = db.execute(select(CostItem).order_by(desc(CostItem.created_at))).scalars().all()
    listings = db.execute(select(ListingItem).order_by(desc(ListingItem.created_at))).scalars().all()

    by_sku: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    meta: dict[str, dict] = defaultdict(dict)

    for row in business_rows:
        key = row.sku or row.asin or "unknown"
        by_sku[key]["sales"] += row.ordered_sales or 0
        by_sku[key]["units"] += row.units_ordered or 0
        by_sku[key]["sessions"] += row.sessions or 0
        meta[key].update({"sku": row.sku or key, "asin": row.asin or "", "title": row.title or meta[key].get("title", "")})

    for row in ad_rows:
        key = row.sku or row.asin or "unknown"
        by_sku[key]["ad_spend"] += row.spend or 0
        by_sku[key]["ad_sales"] += row.sales or 0
        by_sku[key]["ad_orders"] += row.orders or 0
        meta[key].update({"sku": row.sku or key, "asin": row.asin or meta[key].get("asin", "")})

    cost_by_key = {}
    for cost in costs:
        key = cost.sku or cost.asin
        if key and key not in cost_by_key:
            cost_by_key[key] = cost
    for listing in listings:
        key = listing.sku or listing.asin
        if key:
            meta[key].update({"sku": listing.sku or key, "asin": listing.asin or meta[key].get("asin", ""), "title": listing.title or meta[key].get("title", "")})

    summaries = []
    for key, values in by_sku.items():
        sales = values["sales"]
        units = values["units"]
        sessions = values["sessions"]
        ad_spend = values["ad_spend"]
        ad_sales = values["ad_sales"]
        ad_orders = values["ad_orders"]
        cost = cost_by_key.get(key) or cost_by_key.get(meta[key].get("asin", ""))
        unit_cost = 0.0
        referral_rate = 0.15
        target_margin = 0.25
        if cost:
            unit_cost = sum(
                value or 0
                for value in [cost.purchase_cost, cost.first_leg_shipping, cost.packaging_cost, cost.fba_fee, cost.other_cost]
            )
            referral_rate = cost.referral_fee_rate if cost.referral_fee_rate is not None else referral_rate
            if referral_rate > 1:
                referral_rate = referral_rate / 100
            target_margin = cost.target_margin if cost.target_margin is not None else target_margin
            if target_margin > 1:
                target_margin = target_margin / 100
        estimated_profit = sales - ad_spend - sales * referral_rate - units * unit_cost
        margin = estimated_profit / sales if sales else None
        conversion_rate = units / sessions if sessions else None
        acos = ad_spend / ad_sales if ad_sales else None
        tacos = ad_spend / sales if sales else None
        tags, recommendations = _sku_tags_and_recommendations(
            sales, units, sessions, ad_spend, ad_sales, conversion_rate, acos, tacos, margin, target_margin
        )
        summaries.append(
            SkuSummary(
                sku=meta[key].get("sku") or key,
                asin=meta[key].get("asin") or "",
                title=meta[key].get("title") or "",
                sales=sales,
                units=units,
                sessions=sessions,
                conversion_rate=conversion_rate,
                ad_spend=ad_spend,
                ad_sales=ad_sales,
                ad_orders=ad_orders,
                acos=acos,
                tacos=tacos,
                unit_cost=unit_cost,
                estimated_profit=estimated_profit,
                margin=margin,
                tags=tags,
                recommendations=recommendations,
            )
        )
    return sorted(summaries, key=lambda item: item.estimated_profit, reverse=True)


def _sku_tags_and_recommendations(
    sales: float,
    units: float,
    sessions: float,
    ad_spend: float,
    ad_sales: float,
    conversion_rate: float | None,
    acos: float | None,
    tacos: float | None,
    margin: float | None,
    target_margin: float,
) -> tuple[list[str], list[str]]:
    tags = []
    recs = []
    if margin is not None and margin >= target_margin:
        tags.append("利润健康")
    if margin is not None and margin < target_margin:
        tags.append("利润偏低")
        recs.append("检查售价、广告花费和成本；优先保留高转化词，压缩低效广告。")
    if conversion_rate is not None and conversion_rate < 0.05 and sessions >= 100:
        tags.append("转化偏低")
        recs.append("优化主图、尺寸图、适配说明和价格锚点。")
    if conversion_rate is not None and conversion_rate >= 0.12 and sessions < 300:
        tags.append("高转化低流量")
        recs.append("增加精准词广告预算，扩展相关长尾词。")
    if acos is not None and acos > 0.45 and ad_spend >= 20:
        tags.append("广告亏损风险")
        recs.append("降低 broad/auto 出价，检查浪费搜索词。")
    if acos is not None and acos < 0.25 and ad_sales >= 50:
        tags.append("广告可放大")
        recs.append("把高转化词拆 exact 活动，适度加预算。")
    if sales > 0 and ad_spend == 0:
        tags.append("自然销售")
        recs.append("可小预算测试精准词，确认是否能放量。")
    if units >= 10 and margin is not None and margin > target_margin:
        tags.append("可测试多件装")
        recs.append("评估 3-pack/5-pack，提高客单价和广告承受能力。")
    return tags or ["待观察"], recs or ["继续积累数据，等待更多销量和广告表现。"]


def build_ad_actions(db: Session) -> list[dict]:
    rows = db.execute(select(SearchTermMetric).order_by(desc(SearchTermMetric.spend))).scalars().all()
    actions = []
    for row in rows:
        clicks = row.clicks or 0
        spend = row.spend or 0
        sales = row.sales or 0
        orders = row.orders or 0
        impressions = row.impressions or 0
        ctr = clicks / impressions if impressions else None
        acos = row.acos if row.acos is not None else (spend / sales if sales else None)
        priority = None
        action = None
        reason = None
        if clicks >= 12 and orders == 0 and spend >= 10:
            priority = "P0"
            action = "否定 exact 或大幅降价"
            reason = "点击和花费已经足够，但没有订单。"
        elif orders >= 2 and acos is not None and acos <= 0.25:
            priority = "P1"
            action = "加入 exact 活动并适度加预算"
            reason = "搜索词有订单且 ACOS 较低。"
        elif orders >= 1 and sales > 0 and spend / sales <= 0.35:
            priority = "P1"
            action = "保留并观察，可测试 phrase/exact"
            reason = "已有转化，广告效率可接受。"
        elif ctr is not None and ctr < 0.002 and impressions >= 2000:
            priority = "P2"
            action = "检查主图/标题相关性或降低出价"
            reason = "曝光高但点击率低。"
        if priority:
            actions.append(
                {
                    "priority": priority,
                    "action": action,
                    "reason": reason,
                    "search_term": row.search_term or row.targeting or "",
                    "campaign": row.campaign_name or "",
                    "clicks": clicks,
                    "spend": spend,
                    "sales": sales,
                    "orders": orders,
                    "acos": acos,
                }
            )
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(actions, key=lambda item: (priority_order[item["priority"]], -item["spend"]))[:100]


def build_listing_audits(db: Session) -> list[dict]:
    listings = db.execute(select(ListingItem).order_by(desc(ListingItem.created_at))).scalars().all()
    audits = []
    seen = set()
    for item in listings:
        key = item.sku or item.asin
        if not key or key in seen:
            continue
        seen.add(key)
        issues = []
        title = item.title or ""
        bullets = [item.bullet_1, item.bullet_2, item.bullet_3, item.bullet_4, item.bullet_5]
        bullet_text = " ".join(value or "" for value in bullets)
        if len(title) < 90:
            issues.append("标题偏短，可能没有覆盖核心规格、用途和兼容词。")
        if not any(term in title.lower() for term in ["replacement", "compatible", "pack", "kit", "set"]):
            issues.append("标题缺少 replacement / compatible / pack / kit 等高意图词。")
        if sum(1 for value in bullets if value) < 4:
            issues.append("五点不完整，建议补齐规格、适配、材料、使用场景、售后说明。")
        if not any(term in bullet_text.lower() for term in ["size", "dimension", "compatible", "fit", "fits"]):
            issues.append("五点缺少尺寸/适配说明，容易影响转化和售后。")
        if not item.main_image_url:
            issues.append("缺少主图链接，建议检查图片资料是否完整。")
        audits.append({"listing": item, "issues": issues or ["基础信息完整，后续结合转化率和广告词做精细优化。"]})
    return audits
