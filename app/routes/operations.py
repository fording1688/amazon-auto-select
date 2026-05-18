from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.report_importer import (
    REPORT_TYPES,
    build_ad_actions,
    build_listing_audits,
    build_sku_dashboard,
    import_report,
    latest_batches,
)


router = APIRouter(tags=["operations"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/imports")
def imports_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "imports.html",
        {"request": request, "report_types": REPORT_TYPES, "batches": latest_batches(db)},
    )


@router.post("/imports")
async def upload_report(
    report_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    import_report(db, report_type, file.filename or "uploaded_file", content)
    return RedirectResponse("/imports", status_code=303)


@router.get("/operations/dashboard")
def sku_dashboard(request: Request, db: Session = Depends(get_db)):
    rows = build_sku_dashboard(db)
    totals = {
        "sales": sum(row.sales for row in rows),
        "ad_spend": sum(row.ad_spend for row in rows),
        "profit": sum(row.estimated_profit for row in rows),
        "sku_count": len(rows),
    }
    totals["tacos"] = totals["ad_spend"] / totals["sales"] if totals["sales"] else None
    totals["margin"] = totals["profit"] / totals["sales"] if totals["sales"] else None
    return templates.TemplateResponse("sku_dashboard.html", {"request": request, "rows": rows, "totals": totals})


@router.get("/operations/ad-actions")
def ad_actions(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("ad_actions.html", {"request": request, "actions": build_ad_actions(db)})


@router.get("/operations/listing-audit")
def listing_audit(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("listing_audit.html", {"request": request, "audits": build_listing_audits(db)})
