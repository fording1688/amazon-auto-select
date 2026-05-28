from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.copilot_services import (
    ads_diagnosis_center,
    daily_operations_report,
    import_copilot_report,
    profit_calculator,
    sku_health_center,
)
from app.database import get_db


router = APIRouter(prefix="/api/copilot", tags=["seller-growth-copilot"])


class ProfitInput(BaseModel):
    price: float
    purchase_cost: float = 0
    logistics_cost: float = 0
    fba_fee: float = 0
    referral_fee_rate: float = 0.15
    ad_spend: float = 0


@router.post("/uploads/{report_type}")
async def upload_report(
    report_type: str,
    file: UploadFile = File(...),
    duplicate_strategy: str = Form("prompt"),
    uploaded_by: str = Form(""),
    marketplace: str = Form("US"),
    db: Session = Depends(get_db),
):
    content = await file.read()
    return import_copilot_report(
        db,
        report_type,
        file.filename or "uploaded_report",
        content,
        duplicate_strategy=duplicate_strategy,
        uploaded_by=uploaded_by or None,
        marketplace=marketplace or "US",
    )


@router.get("/sku-health")
def sku_health(db: Session = Depends(get_db)):
    return {"items": sku_health_center(db)}


@router.get("/ads-diagnosis")
def ads_diagnosis(target_acos: Optional[float] = Query(0.25), db: Session = Depends(get_db)):
    return ads_diagnosis_center(db, target_acos=target_acos or 0.25)


@router.post("/profit-calculator")
def calculate_profit(payload: ProfitInput):
    return profit_calculator(payload.model_dump())


@router.get("/daily-report")
def daily_report(db: Session = Depends(get_db)):
    return daily_operations_report(db)
