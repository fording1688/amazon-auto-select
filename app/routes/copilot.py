from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.copilot_services import (
    ads_diagnosis_center,
    batch_context_options,
    create_store,
    daily_operations_report,
    import_copilot_report,
    profit_calculator,
    sku_health_center,
    store_options,
)
from app.database import get_db
from app.models import User


router = APIRouter(prefix="/api/copilot", tags=["seller-growth-copilot"])


class ProfitInput(BaseModel):
    price: float
    purchase_cost: float = 0
    logistics_cost: float = 0
    fba_fee: float = 0
    referral_fee_rate: float = 0.15
    ad_spend: float = 0


class StoreInput(BaseModel):
    name: str
    marketplace: str = "US"


def _parse_business_date(value: str | None) -> datetime | None:
    if not value:
        return None
    clean = value.strip()
    if not clean:
        return None
    try:
        return datetime.fromisoformat(clean)
    except ValueError:
        return datetime.strptime(clean, "%Y-%m-%d")


@router.post("/uploads/{report_type}")
async def upload_report(
    report_type: str,
    file: UploadFile = File(...),
    duplicate_strategy: str = Form("prompt"),
    uploaded_by: str = Form(""),
    marketplace: str = Form("US"),
    store_name: str = Form(""),
    business_date: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        return import_copilot_report(
            db,
            report_type,
            file.filename or "uploaded_report",
            content,
            duplicate_strategy=duplicate_strategy,
            uploaded_by=uploaded_by or None,
            marketplace=marketplace or "US",
            store_name=store_name,
            business_date=_parse_business_date(business_date),
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sku-health")
def sku_health(
    store_id: Optional[int] = Query(None),
    business_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {"items": sku_health_center(db, store_id=store_id, business_date=_parse_business_date(business_date), user_id=user.id)}


@router.get("/ads-diagnosis")
def ads_diagnosis(
    target_acos: Optional[float] = Query(0.25),
    store_id: Optional[int] = Query(None),
    business_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ads_diagnosis_center(
        db,
        target_acos=target_acos or 0.25,
        store_id=store_id,
        business_date=_parse_business_date(business_date),
        user_id=user.id,
    )


@router.post("/profit-calculator")
def calculate_profit(payload: ProfitInput):
    return profit_calculator(payload.model_dump())


@router.get("/daily-report")
def daily_report(
    store_id: Optional[int] = Query(None),
    business_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return daily_operations_report(db, store_id=store_id, business_date=_parse_business_date(business_date), user_id=user.id)


@router.get("/stores")
def stores(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"items": store_options(db, user_id=user.id)}


@router.post("/stores")
def add_store(payload: StoreInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return create_store(db, payload.name, payload.marketplace, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/context")
def context(store_id: Optional[int] = Query(None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return batch_context_options(db, store_id=store_id, user_id=user.id)
