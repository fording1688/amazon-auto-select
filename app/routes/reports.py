from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisReport, Product


router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="app/templates")


def loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


@router.get("/product/{product_id}")
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    report = (
        db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.product_id == product_id)
            .order_by(desc(AnalysisReport.created_at))
            .limit(1)
        )
        .scalar_one_or_none()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    parsed = {
        "reasons": loads(report.reasons_json, []),
        "risks": loads(report.risks_json, []),
        "bundle": loads(report.bundle_strategy_json, {}),
        "pricing": loads(report.pricing_suggestion_json, {}),
        "listing": loads(report.listing_suggestion_json, {}),
        "images": loads(report.image_selling_points_json, []),
        "ads": loads(report.ad_keywords_json, []),
        "negative": loads(report.negative_keywords_json, []),
        "fbm": loads(report.fbm_test_plan_json, {}),
    }
    return templates.TemplateResponse(
        "product_detail.html",
        {"request": request, "product": product, "report": report, "parsed": parsed},
    )
