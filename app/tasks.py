from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai_analyzer import analyze_product
from app.amazon_api_client import get_amazon_client
from app.feishu_notifier import send_top_products
from app.models import AnalysisReport, Keyword, Product, TaskRun
from app.scoring import calculate_opportunity_score


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _upsert_product(db: Session, keyword: Keyword, payload: dict) -> Product:
    product = db.execute(
        select(Product).where(Product.asin == payload["asin"], Product.keyword_id == keyword.id)
    ).scalar_one_or_none()
    if product is None:
        product = Product(asin=payload["asin"], keyword_id=keyword.id, title=payload["title"])
        db.add(product)
    for field in [
        "title",
        "price",
        "rating",
        "review_count",
        "brand",
        "seller",
        "image_url",
        "product_url",
        "availability",
        "coupon",
        "variation_count",
        "package_quantity",
        "bsr",
    ]:
        setattr(product, field, payload.get(field))
    product.updated_at = datetime.utcnow()
    db.flush()
    return product


def _save_report(db: Session, product: Product, analysis: dict) -> AnalysisReport:
    report = AnalysisReport(
        product_id=product.id,
        opportunity_score=int(analysis.get("opportunity_score") or 0),
        decision=analysis.get("decision") or "观察",
        summary=analysis.get("summary"),
        reasons_json=_json(analysis.get("reasons") or []),
        risks_json=_json(analysis.get("risks") or []),
        bundle_strategy_json=_json(analysis.get("bundle_strategy") or {}),
        pricing_suggestion_json=_json(analysis.get("pricing_suggestion") or {}),
        listing_suggestion_json=_json(analysis.get("listing_suggestion") or {}),
        image_selling_points_json=_json(analysis.get("image_selling_points") or []),
        ad_keywords_json=_json(analysis.get("ad_keywords") or []),
        negative_keywords_json=_json(analysis.get("negative_keywords") or []),
        fbm_test_plan_json=_json(analysis.get("fbm_test_plan_14_days") or analysis.get("fbm_test_plan") or {}),
        next_action=analysis.get("next_action"),
        raw_ai_response=analysis.get("raw_ai_response"),
    )
    db.add(report)
    db.flush()
    return report


def report_to_push_payload(report: AnalysisReport) -> dict:
    product = report.product
    keyword = product.keyword
    return {
        "title": product.title,
        "asin": product.asin,
        "keyword": keyword.keyword if keyword else "",
        "price": product.price,
        "review_count": product.review_count,
        "rating": product.rating,
        "opportunity_score": report.opportunity_score,
        "decision": report.decision,
        "reasons": json.loads(report.reasons_json or "[]"),
        "bundle_strategy": json.loads(report.bundle_strategy_json or "{}"),
        "pricing_suggestion": json.loads(report.pricing_suggestion_json or "{}"),
        "next_action": report.next_action,
    }


def run_analysis_task(db: Session) -> TaskRun:
    task_run = TaskRun(status="running", started_at=datetime.utcnow())
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    try:
        client = get_amazon_client()
        keywords = db.execute(select(Keyword).where(Keyword.status == "active")).scalars().all()
        task_run.total_keywords = len(keywords)
        total_products = 0
        total_analyzed = 0

        for keyword in keywords:
            products = client.search_products(keyword.keyword, limit=20)
            for payload in products:
                payload["keyword"] = keyword.keyword
                product = _upsert_product(db, keyword, payload)
                score_result = calculate_opportunity_score(payload)
                analysis = analyze_product(payload, score_result)
                _save_report(db, product, analysis)
                total_products += 1
                total_analyzed += 1

        task_run.status = "success"
        task_run.total_products = total_products
        task_run.total_analyzed = total_analyzed
        task_run.finished_at = datetime.utcnow()
        db.commit()

        top_reports = (
            db.execute(
                select(AnalysisReport)
                .order_by(desc(AnalysisReport.created_at), desc(AnalysisReport.opportunity_score))
                .limit(max(20, total_analyzed))
            )
            .scalars()
            .all()
        )
        recent_top = sorted(top_reports[:total_analyzed or 5], key=lambda r: r.opportunity_score, reverse=True)[:5]
        if recent_top:
            try:
                send_top_products([report_to_push_payload(report) for report in recent_top])
            except Exception as exc:
                task_run.error_message = f"飞书推送失败：{exc}"
                db.commit()

        db.refresh(task_run)
        return task_run
    except Exception as exc:
        task_run.status = "failed"
        task_run.error_message = str(exc)
        task_run.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(task_run)
        return task_run


def seed_keywords(db: Session) -> None:
    examples = [
        "diamond band saw blade",
        "cbn chainsaw grinding wheel",
        "diamond grinding disc",
        "glass grinder bit",
        "lapidary saw blade",
        "tormek replacement parts",
        "stained glass soldering tools",
        "glass cutter replacement wheel",
    ]
    existing = {row[0] for row in db.execute(select(Keyword.keyword)).all()}
    for keyword in examples:
        if keyword not in existing:
            db.add(Keyword(keyword=keyword, category="五金工具", priority="中", status="active"))
    db.commit()
