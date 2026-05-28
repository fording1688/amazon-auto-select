from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.ad_recommendations import (
    RECOMMENDATION_LABELS,
    STATUS_LABELS,
    approve_recommendation,
    count_recommendations,
    generate_ad_recommendations,
    list_recommendations,
    mark_manual_recommendation,
    recommendation_summary,
    reject_recommendation,
)
from app.database import get_db
from app.operations_ai import generate_operations_ai_report, latest_operations_ai_report, report_to_view
from app.pagination import build_pagination, paginate_list
from app.report_importer import (
    REPORT_TYPES,
    build_ad_action_groups,
    build_ad_actions,
    build_business_overview,
    build_listing_audits,
    build_operations_cockpit,
    build_sku_dashboard,
    count_batches,
    import_report,
    latest_batches,
    REPORT_INBOX,
    SUPPORTED_EXTENSIONS,
    scan_inbox,
)


router = APIRouter(tags=["operations"])
templates = Jinja2Templates(directory="app/templates")
AD_REPORT_TYPES = {"search_terms", "advertised_products", "campaigns", "targeting", "bulk_operations"}


def _pending_inbox_files() -> list[str]:
    REPORT_INBOX.mkdir(parents=True, exist_ok=True)
    return [
        path.name
        for path in sorted(REPORT_INBOX.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def _imports_context(request: Request, db: Session, page: int = 1, per_page: int = 10, **extra):
    total_batches = count_batches(db)
    pagination = build_pagination(total_batches, page, per_page, "/imports")
    context = {
        "request": request,
        "report_types": REPORT_TYPES,
        "batches": latest_batches(db, limit=per_page, offset=(pagination.page - 1) * pagination.per_page),
        "batch_pagination": pagination,
        "scan_results": None,
        "scan_summary": None,
        "upload_result": None,
        "pending_files": _pending_inbox_files(),
        "inbox_path": str(REPORT_INBOX.resolve()),
    }
    context.update(extra)
    return context


@router.get("/imports")
def imports_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    return templates.TemplateResponse("imports.html", _imports_context(request, db, page=page))


@router.post("/imports")
async def upload_report(
    request: Request,
    report_type: str = Form(...),
    file: UploadFile = File(...),
    duplicate_strategy: str = Form("prompt"),
    uploaded_by: str = Form(""),
    marketplace: str = Form("US"),
    db: Session = Depends(get_db),
):
    content = await file.read()
    batch = import_report(
        db,
        report_type,
        file.filename or "uploaded_file",
        content,
        duplicate_strategy=duplicate_strategy,
        uploaded_by=uploaded_by or None,
        marketplace=marketplace or "US",
    )
    generated_count = None
    if batch.status == "success" and report_type in AD_REPORT_TYPES:
        generated_count = generate_ad_recommendations(db)
    return templates.TemplateResponse(
        "imports.html",
        _imports_context(
            request,
            db,
            upload_result={
                "file_name": batch.file_name,
                "report_type": batch.report_type,
                "status": batch.status,
                "row_count": batch.row_count,
                "error_message": batch.error_message,
                "duplicate_count": batch.duplicate_count,
                "period_start": batch.period_start,
                "period_end": batch.period_end,
                "generated_ad_recommendations": generated_count,
            },
        ),
    )


@router.post("/imports/scan-inbox")
def scan_report_inbox(
    request: Request,
    duplicate_strategy: str = Form("prompt"),
    db: Session = Depends(get_db),
):
    before_files = _pending_inbox_files()
    results = scan_inbox(db, duplicate_strategy=duplicate_strategy)
    success_count = sum(1 for item in results if item["status"] == "success")
    failed_count = sum(1 for item in results if item["status"] == "failed")
    generated_count = None
    if any(item["status"] == "success" and item["report_type"] in AD_REPORT_TYPES for item in results):
        generated_count = generate_ad_recommendations(db)
    summary = {
        "before_count": len(before_files),
        "processed_count": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "generated_ad_recommendations": generated_count,
    }
    return templates.TemplateResponse(
        "imports.html",
        _imports_context(request, db, scan_results=results, scan_summary=summary),
    )


@router.get("/ad-recommendations")
def ad_recommendations_page(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query("pending"),
    recommendation_type: str = Query(""),
    traffic_type: str = Query(""),
    acos_max: Optional[float] = Query(None),
    orders_positive: bool = Query(False),
    spend_positive: bool = Query(False),
    db: Session = Depends(get_db),
):
    status_filter = status or None
    type_filter = recommendation_type or None
    traffic_filter = traffic_type or None
    total = count_recommendations(db, status_filter, type_filter, traffic_filter, acos_max, orders_positive, spend_positive)
    query_parts = []
    if status:
        query_parts.append(f"status={status}")
    if recommendation_type:
        query_parts.append(f"recommendation_type={recommendation_type}")
    if traffic_type:
        query_parts.append(f"traffic_type={traffic_type}")
    if acos_max is not None:
        query_parts.append(f"acos_max={acos_max}")
    if orders_positive:
        query_parts.append("orders_positive=true")
    if spend_positive:
        query_parts.append("spend_positive=true")
    base_url = "/ad-recommendations" + (f"?{'&'.join(query_parts)}" if query_parts else "")
    pagination = build_pagination(total, page, 20, base_url)
    rows = list_recommendations(
        db,
        limit=pagination.per_page,
        offset=(pagination.page - 1) * pagination.per_page,
        status=status_filter,
        recommendation_type=type_filter,
        traffic_type=traffic_filter,
        acos_max=acos_max,
        orders_positive=orders_positive,
        spend_positive=spend_positive,
    )
    return templates.TemplateResponse(
        "ad_recommendations.html",
        {
            "request": request,
            "rows": rows,
            "pagination": pagination,
            "status": status,
            "recommendation_type": recommendation_type,
            "traffic_type": traffic_type,
            "acos_max": acos_max,
            "summary": recommendation_summary(db),
            "orders_positive": orders_positive,
            "spend_positive": spend_positive,
            "recommendation_labels": RECOMMENDATION_LABELS,
            "status_labels": STATUS_LABELS,
            "generated_count": request.query_params.get("generated"),
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@router.post("/ad-recommendations/generate")
def generate_recommendations_now(db: Session = Depends(get_db)):
    count = generate_ad_recommendations(db)
    return RedirectResponse(f"/ad-recommendations?status=pending&generated={count}", status_code=303)


@router.post("/ad-recommendations/{recommendation_id}/approve")
def approve_ad_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    try:
        approve_recommendation(db, recommendation_id)
        return RedirectResponse("/ad-recommendations?status=approved&message=approved", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/ad-recommendations?error={quote(str(exc))}", status_code=303)


@router.post("/ad-recommendations/{recommendation_id}/reject")
def reject_ad_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    try:
        reject_recommendation(db, recommendation_id)
        return RedirectResponse("/ad-recommendations?status=rejected&message=rejected", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/ad-recommendations?error={quote(str(exc))}", status_code=303)


@router.post("/ad-recommendations/{recommendation_id}/manual")
def mark_ad_recommendation_manual(recommendation_id: int, db: Session = Depends(get_db)):
    try:
        mark_manual_recommendation(db, recommendation_id)
        return RedirectResponse("/ad-recommendations?status=executed&message=manual", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/ad-recommendations?error={quote(str(exc))}", status_code=303)


@router.get("/operations/dashboard")
def sku_dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    rows = build_sku_dashboard(db)
    totals = {
        "sales": sum(row.sales for row in rows),
        "ad_spend": sum(row.ad_spend for row in rows),
        "profit": sum(row.estimated_profit for row in rows),
        "sku_count": len(rows),
    }
    totals["tacos"] = totals["ad_spend"] / totals["sales"] if totals["sales"] else None
    totals["margin"] = totals["profit"] / totals["sales"] if totals["sales"] else None
    page_rows, pagination = paginate_list(rows, page, 10, "/operations/dashboard")
    return templates.TemplateResponse(
        "sku_dashboard.html",
        {"request": request, "rows": page_rows, "totals": totals, "pagination": pagination},
    )


@router.get("/operations/action-center")
def action_center(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "action_center.html",
        {"request": request, **build_operations_cockpit(db)},
    )


@router.get("/operations/business-overview")
def business_overview(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    data = build_business_overview(db)
    rows = data.get("rows") or []
    data["rows"], data["pagination"] = paginate_list(rows, page, 10, "/operations/business-overview")
    return templates.TemplateResponse("business_overview.html", {"request": request, **data})


@router.get("/operations/ad-actions")
def ad_actions(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    groups, pagination = paginate_list(build_ad_action_groups(db), page, 8, "/operations/ad-actions")
    return templates.TemplateResponse("ad_actions.html", {"request": request, "groups": groups, "pagination": pagination})


@router.get("/operations/ai-advisor")
def ai_advisor(request: Request, db: Session = Depends(get_db)):
    report = report_to_view(latest_operations_ai_report(db))
    return templates.TemplateResponse("ai_advisor.html", {"request": request, "report": report})


@router.post("/operations/ai-advisor/generate")
def generate_ai_advisor(request: Request, db: Session = Depends(get_db)):
    report = generate_operations_ai_report(db)
    return templates.TemplateResponse("ai_advisor.html", {"request": request, "report": report_to_view(report)})


@router.get("/operations/listing-audit")
def listing_audit(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    audits, pagination = paginate_list(build_listing_audits(db), page, 10, "/operations/listing-audit")
    return templates.TemplateResponse("listing_audit.html", {"request": request, "audits": audits, "pagination": pagination})
