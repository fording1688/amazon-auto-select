from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.amazon_listing_export import build_saw_blade_upload_workbook
from app.database import get_db
from app.listing_generator import (
    add_competitor_reference,
    copy_listing_project,
    create_listing_project,
    delete_listing_project,
    generate_aplus_version,
    generate_image_prompts,
    generate_listing_versions,
    get_listing_project,
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
from app.models import AplusVersion, CompetitorReference, ImagePromptVersion, ListingImageAsset, ListingProjectInput, ListingVersion, User
from app.r2_storage import R2StorageError, build_listing_image_key, delete_object, signed_url_for_key, upload_listing_image
from sqlalchemy import desc, select


router = APIRouter(prefix="/api/listing-projects", tags=["listing-projects"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 12 * 1024 * 1024


def serialize_listing_image(item: ListingImageAsset) -> dict[str, Any]:
    data = {column.name: getattr(item, column.name) for column in ListingImageAsset.__table__.columns}
    try:
        data["url"] = item.public_url or signed_url_for_key(item.r2_key, item.r2_bucket)
    except Exception:
        data["url"] = item.public_url or ""
    return data


@router.post("")
def create_project(payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        project = create_listing_project(db, payload, user_id=user.id)
        competitor_reference = payload.get("competitor_reference")
        if isinstance(competitor_reference, dict):
            add_competitor_reference(db, project.id, competitor_reference, user_id=user.id)
        return serialize_project(project)
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


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return delete_listing_project(db, project_id, user_id=user.id)
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


@router.get("/{project_id}/images")
def listing_images(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project_detail(db, project_id, user_id=user.id)
    rows = db.execute(
        select(ListingImageAsset).where(ListingImageAsset.project_id == project_id).order_by(desc(ListingImageAsset.created_at))
    ).scalars().all()
    return {"items": [serialize_listing_image(item) for item in rows]}


@router.post("/{project_id}/images")
async def upload_listing_asset(
    project_id: int,
    image_type: str = Form(default="other"),
    title: str = Form(default=""),
    notes: str = Form(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project_detail(db, project_id, user_id=user.id)
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、WEBP、GIF 图片。")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="图片文件为空。")
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片不能超过 12MB。")
    from io import BytesIO

    key = build_listing_image_key(user.id, project_id, file.filename or "listing-image.jpg")
    try:
        uploaded = upload_listing_image(BytesIO(data), key=key, content_type=content_type)
    except R2StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"上传到 R2 失败：{exc}") from exc

    row = ListingImageAsset(
        project_id=project_id,
        user_id=user.id,
        image_type=(image_type or "other")[:80],
        title=title or None,
        notes=notes or None,
        file_name=file.filename or "listing-image",
        content_type=content_type,
        file_size=len(data),
        r2_bucket=uploaded["bucket"],
        r2_key=uploaded["key"],
        public_url=uploaded["public_url"] or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_listing_image(row)


@router.delete("/{project_id}/images/{image_id}")
def delete_listing_asset(project_id: int, image_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project_detail(db, project_id, user_id=user.id)
    row = db.get(ListingImageAsset, image_id)
    if not row or row.project_id != project_id or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="图片不存在")
    try:
        delete_object(row.r2_key, row.r2_bucket)
    except Exception:
        pass
    db.delete(row)
    db.commit()
    return {"ok": True, "deleted_id": image_id}


@router.post("/{project_id}/amazon-upload-file")
def amazon_upload_file(project_id: int, payload: dict[str, Any] | None = Body(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = payload or {}
    try:
        detail = project_detail(db, project_id, user_id=user.id)
        project = get_listing_project(db, project_id, user_id=user.id)
        listing_id = payload.get("listing_version_id")
        listing = None
        if listing_id:
            listing = db.get(ListingVersion, int(listing_id))
        if not listing or listing.project_id != project_id:
            listing = db.execute(
                select(ListingVersion).where(ListingVersion.project_id == project_id).order_by(desc(ListingVersion.created_at))
            ).scalars().first()
        if not listing:
            raise ValueError("请先生成至少 1 个 Listing 文案版本。")
        inputs = db.execute(select(ListingProjectInput).where(ListingProjectInput.project_id == project_id)).scalar_one_or_none()
        export = build_saw_blade_upload_workbook(
            project=project,
            inputs=inputs,
            listing=listing,
            brand=(payload.get("brand") or project.brand or "").strip(),
            category=(payload.get("category") or project.category or "").strip(),
            images=payload.get("images") or detail.get("listing_images") or [],
            variation=payload.get("variation") or None,
        )
        headers = {"Content-Disposition": f'attachment; filename="{export.file_name}"'}
        return Response(
            content=export.content,
            headers=headers,
            media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
                    version_count=payload.get("version_count") or 1,
                    product_reference_image={},
                    similar_product_references=payload.get("similar_product_references") or [],
                    reference_insights=payload.get("reference_insights") or {},
                    confirmed_product_facts=payload.get("confirmed_product_facts") or {},
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
                    version_count=payload.get("version_count") or 1,
                    product_reference_image=payload.get("product_reference_image") or {},
                    similar_product_references=payload.get("similar_product_references") or [],
                    reference_insights=payload.get("reference_insights") or {},
                    confirmed_product_facts=payload.get("confirmed_product_facts") or {},
                )
            ]
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/generate-aplus")
def generate_aplus(project_id: int, payload: dict[str, Any] | None = Body(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        payload = payload or {}
        count = max(1, min(5, int(payload.get("version_count") or 1)))
        return {
            "items": [
                serialize_aplus(
                    generate_aplus_version(
                        db,
                        project_id,
                        user_id=user.id,
                        model=payload.get("model"),
                        version_count=1,
                        product_reference_image=payload.get("product_reference_image") or {},
                        similar_product_references=payload.get("similar_product_references") or [],
                        reference_insights=payload.get("reference_insights") or {},
                        confirmed_product_facts=payload.get("confirmed_product_facts") or {},
                    )
                )
                for _ in range(count)
            ]
        }
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
