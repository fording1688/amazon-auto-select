from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisReport, Keyword, Product
from app.opportunity import build_test_candidate


router = APIRouter(prefix="/products", tags=["products"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def list_products(
    request: Request,
    keyword_id: Optional[int] = None,
    decision: Optional[str] = None,
    db: Session = Depends(get_db),
):
    latest_report_id = (
        select(AnalysisReport.id)
        .where(AnalysisReport.product_id == Product.id)
        .order_by(desc(AnalysisReport.created_at))
        .limit(1)
        .correlate(Product)
        .scalar_subquery()
    )
    stmt = (
        select(Product, AnalysisReport)
        .join(AnalysisReport, AnalysisReport.id == latest_report_id)
        .order_by(desc(AnalysisReport.opportunity_score), desc(AnalysisReport.created_at))
    )
    if keyword_id:
        stmt = stmt.where(Product.keyword_id == keyword_id)
    if decision:
        stmt = stmt.where(AnalysisReport.decision == decision)
    rows = db.execute(stmt).all()
    keywords = db.execute(select(Keyword).order_by(Keyword.keyword)).scalars().all()
    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "rows": rows,
            "keywords": keywords,
            "keyword_id": keyword_id,
            "decision": decision or "",
            "decisions": ["重点测款", "小批量测试", "观察", "放弃"],
        },
    )


@router.get("/shortlist")
def shortlist(request: Request, db: Session = Depends(get_db)):
    latest_report_id = (
        select(AnalysisReport.id)
        .where(AnalysisReport.product_id == Product.id)
        .order_by(desc(AnalysisReport.created_at))
        .limit(1)
        .correlate(Product)
        .scalar_subquery()
    )
    rows = (
        db.execute(
            select(Product, AnalysisReport)
            .join(AnalysisReport, AnalysisReport.id == latest_report_id)
            .where(~Product.asin.like("B0MOCK%"))
            .order_by(desc(AnalysisReport.opportunity_score), desc(AnalysisReport.created_at))
            .limit(300)
        )
        .all()
    )
    keyword_ids = {product.keyword_id for product, _ in rows}
    peer_rows = db.execute(select(Product).where(Product.keyword_id.in_(keyword_ids))).scalars().all() if keyword_ids else []
    peers_by_keyword: dict[int, list[Product]] = {}
    for peer in peer_rows:
        peers_by_keyword.setdefault(peer.keyword_id, []).append(peer)

    candidates = []
    for product, report in rows:
        candidate = build_test_candidate(product, report, peers_by_keyword.get(product.keyword_id, []))
        if candidate:
            candidates.append(candidate)
    candidates = sorted(candidates, key=lambda item: item.test_score, reverse=True)[:20]
    return templates.TemplateResponse("shortlist.html", {"request": request, "candidates": candidates})
