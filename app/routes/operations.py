from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.operations_ai import generate_operations_ai_report, latest_operations_ai_report, report_to_view
from app.pagination import build_pagination, paginate_list
from app.report_importer import (
    REPORT_TYPES,
    build_ad_action_groups,
    build_ad_actions,
    build_business_overview,
    build_listing_audits,
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
    db: Session = Depends(get_db),
):
    content = await file.read()
    batch = import_report(db, report_type, file.filename or "uploaded_file", content)
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
            },
        ),
    )


@router.post("/imports/scan-inbox")
def scan_report_inbox(request: Request, db: Session = Depends(get_db)):
    before_files = _pending_inbox_files()
    results = scan_inbox(db)
    success_count = sum(1 for item in results if item["status"] == "success")
    failed_count = sum(1 for item in results if item["status"] == "failed")
    summary = {
        "before_count": len(before_files),
        "processed_count": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
    }
    return templates.TemplateResponse(
        "imports.html",
        _imports_context(request, db, scan_results=results, scan_summary=summary),
    )


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
