from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.listing_generator import (
    add_competitor_reference,
    copy_listing_project,
    create_listing_project,
    generate_aplus_version,
    generate_image_prompts,
    generate_listing_versions,
    list_listing_projects,
    project_detail,
    serialize_aplus,
    serialize_competitor,
    serialize_image_prompt,
    serialize_inputs,
    serialize_listing,
    serialize_project,
    update_listing_project,
    upsert_project_inputs,
)
from app.models import AplusVersion, CompetitorReference, ImagePromptVersion, ListingVersion, User
from sqlalchemy import desc, select


router = APIRouter(prefix="/api/listing-projects", tags=["listing-projects"])


@router.post("")
def create_project(payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return serialize_project(create_listing_project(db, payload, user_id=user.id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"items": [serialize_project(item) for item in list_listing_projects(db, user_id=user.id)]}


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return project_detail(db, project_id, user_id=user.id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{project_id}")
def update_project(project_id: int, payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        update_listing_project(db, project_id, payload, user_id=user.id)
        return project_detail(db, project_id, user_id=user.id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/copy")
def copy_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return serialize_project(copy_listing_project(db, project_id, user_id=user.id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{project_id}/inputs")
def update_inputs(project_id: int, payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return serialize_inputs(upsert_project_inputs(db, project_id, payload, user_id=user.id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/competitors")
def add_competitor(project_id: int, payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return serialize_competitor(add_competitor_reference(db, project_id, payload, user_id=user.id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{project_id}/competitors/{competitor_id}")
def delete_competitor(project_id: int, competitor_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        get_listing_project = project_detail(db, project_id, user_id=user.id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Listing 项目不存在") from exc
    row = db.get(CompetitorReference, competitor_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="同行参考不存在")
    db.delete(row)
    db.commit()
    return {"ok": True, "deleted_id": competitor_id}


@router.post("/{project_id}/generate-listing")
def generate_listing(project_id: int, payload: dict[str, Any] | None = Body(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        payload = payload or {}
        return {
            "items": [
                serialize_listing(item)
                for item in generate_listing_versions(
                    db,
                    project_id,
                    user_id=user.id,
                    model=payload.get("model"),
                    version_count=payload.get("version_count") or 5,
                    product_reference_image=payload.get("product_reference_image") or {},
                )
            ]
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/generate-image-prompts")
def generate_images(project_id: int, payload: dict[str, Any] | None = Body(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        payload = payload or {}
        return {
            "items": [
                serialize_image_prompt(item)
                for item in generate_image_prompts(
                    db,
                    project_id,
                    user_id=user.id,
                    model=payload.get("model"),
                    version_count=payload.get("version_count") or 9,
                    product_reference_image=payload.get("product_reference_image") or {},
                )
            ]
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/generate-aplus")
def generate_aplus(project_id: int, payload: dict[str, Any] | None = Body(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        payload = payload or {}
        return serialize_aplus(
            generate_aplus_version(
                db,
                project_id,
                user_id=user.id,
                model=payload.get("model"),
                version_count=payload.get("version_count") or 1,
                product_reference_image=payload.get("product_reference_image") or {},
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/listing-versions")
def listing_versions(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project_detail(db, project_id, user_id=user.id)
    rows = db.execute(
        select(ListingVersion).where(ListingVersion.project_id == project_id).order_by(desc(ListingVersion.created_at))
    ).scalars().all()
    return {"items": [serialize_listing(item) for item in rows]}


@router.get("/{project_id}/image-prompt-versions")
def image_versions(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project_detail(db, project_id, user_id=user.id)
    rows = db.execute(
        select(ImagePromptVersion).where(ImagePromptVersion.project_id == project_id).order_by(desc(ImagePromptVersion.created_at))
    ).scalars().all()
    return {"items": [serialize_image_prompt(item) for item in rows]}


@router.get("/{project_id}/aplus-versions")
def aplus_versions(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project_detail(db, project_id, user_id=user.id)
    rows = db.execute(
        select(AplusVersion).where(AplusVersion.project_id == project_id).order_by(desc(AplusVersion.created_at))
    ).scalars().all()
    return {"items": [serialize_aplus(item) for item in rows]}
