from __future__ import annotations

import re
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    AplusVersion,
    CompetitorReference,
    ImagePromptVersion,
    ListingProject,
    ListingProjectInput,
    ListingVersion,
)


RISKY_WORDS = [
    "best",
    "guaranteed",
    "lifetime",
    "official",
    "original",
    "authorized",
    "amazon's choice",
]

INPUT_FIELDS = [
    "size",
    "material",
    "color",
    "quantity",
    "compatibility",
    "package_includes",
    "not_included",
    "warning_limitation",
    "use_cases",
    "target_customer",
    "buyer_type",
    "advantages",
    "difference_from_competitors",
    "main_keywords",
    "secondary_keywords",
    "long_tail_keywords",
    "compatibility_keywords",
    "keywords_to_avoid",
    "forbidden_words",
    "compliance_notes",
]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _split_terms(value: str | None) -> list[str]:
    terms = re.split(r"[,;\n]+", _text(value))
    return [term.strip() for term in terms if term.strip()]


def create_listing_project(db: Session, payload: dict[str, Any], user_id: int | None = None) -> ListingProject:
    project = ListingProject(
        user_id=user_id,
        project_name=_text(payload.get("project_name")) or _text(payload.get("product_name")) or "Untitled Listing Project",
        marketplace=_text(payload.get("marketplace")) or "US",
        brand=_text(payload.get("brand")) or None,
        category=_text(payload.get("category")) or None,
        product_name=_text(payload.get("product_name")) or None,
        target_price=float(payload["target_price"]) if _text(payload.get("target_price")) else None,
        fulfillment_method=_text(payload.get("fulfillment_method")) or None,
        status=_text(payload.get("status")) or "draft",
        notes=_text(payload.get("notes")) or None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    if payload.get("inputs"):
        upsert_project_inputs(db, project.id, payload["inputs"], user_id=user_id)
    return project


def list_listing_projects(db: Session, user_id: int | None = None) -> list[ListingProject]:
    query = select(ListingProject).order_by(desc(ListingProject.updated_at))
    if user_id:
        query = query.where(ListingProject.user_id == user_id)
    return db.execute(query).scalars().all()


def get_listing_project(db: Session, project_id: int, user_id: int | None = None) -> ListingProject:
    project = db.get(ListingProject, project_id)
    if not project or (user_id and project.user_id != user_id):
        raise ValueError("Listing 项目不存在")
    return project


def _ensure_draft(project: ListingProject) -> None:
    if project.status != "draft":
        raise ValueError("项目已生成内容，基础信息已锁定；请复制基本信息新建草稿后修改。")


def update_listing_project(db: Session, project_id: int, payload: dict[str, Any], user_id: int | None = None) -> ListingProject:
    project = get_listing_project(db, project_id, user_id=user_id)
    _ensure_draft(project)
    for field in ["project_name", "marketplace", "brand", "category", "product_name", "fulfillment_method", "notes"]:
        if field in payload:
            value = _text(payload.get(field))
            setattr(project, field, value or (None if field not in ["project_name", "marketplace"] else getattr(project, field)))
    if "target_price" in payload:
        project.target_price = float(payload["target_price"]) if _text(payload.get("target_price")) else None
    if payload.get("inputs") is not None:
        upsert_project_inputs(db, project.id, payload["inputs"], user_id=user_id)
    else:
        db.commit()
    db.refresh(project)
    return project


def copy_listing_project(db: Session, project_id: int, user_id: int | None = None) -> ListingProject:
    project = get_listing_project(db, project_id, user_id=user_id)
    inputs = db.execute(select(ListingProjectInput).where(ListingProjectInput.project_id == project_id)).scalar_one_or_none()
    copy_project = ListingProject(
        user_id=user_id or project.user_id,
        project_name=f"{project.project_name} - 副本",
        marketplace=project.marketplace,
        brand=project.brand,
        category=project.category,
        product_name=project.product_name,
        target_price=project.target_price,
        fulfillment_method=project.fulfillment_method,
        status="draft",
        notes=project.notes,
    )
    db.add(copy_project)
    db.commit()
    db.refresh(copy_project)
    if inputs:
        copied_inputs = ListingProjectInput(project_id=copy_project.id)
        for field in INPUT_FIELDS:
            setattr(copied_inputs, field, getattr(inputs, field))
        db.add(copied_inputs)
        db.commit()
    db.refresh(copy_project)
    return copy_project


def upsert_project_inputs(db: Session, project_id: int, payload: dict[str, Any], user_id: int | None = None) -> ListingProjectInput:
    project = get_listing_project(db, project_id, user_id=user_id)
    _ensure_draft(project)
    inputs = db.execute(select(ListingProjectInput).where(ListingProjectInput.project_id == project_id)).scalar_one_or_none()
    if not inputs:
        inputs = ListingProjectInput(project_id=project_id)
        db.add(inputs)
    for field in INPUT_FIELDS:
        if field in payload:
            setattr(inputs, field, _text(payload.get(field)) or None)
    db.commit()
    db.refresh(inputs)
    return inputs


def add_competitor_reference(db: Session, project_id: int, payload: dict[str, Any], user_id: int | None = None) -> CompetitorReference:
    get_listing_project(db, project_id, user_id=user_id)
    ref = CompetitorReference(
        project_id=project_id,
        competitor_url=_text(payload.get("competitor_url")) or None,
        competitor_title=_text(payload.get("competitor_title")) or None,
        competitor_bullets=_text(payload.get("competitor_bullets")) or None,
        competitor_description=_text(payload.get("competitor_description")) or None,
        competitor_price=float(payload["competitor_price"]) if _text(payload.get("competitor_price")) else None,
        competitor_rating=float(payload["competitor_rating"]) if _text(payload.get("competitor_rating")) else None,
        competitor_review_count=int(float(payload["competitor_review_count"])) if _text(payload.get("competitor_review_count")) else None,
        competitor_image_notes=_text(payload.get("competitor_image_notes")) or None,
        competitor_aplus_notes=_text(payload.get("competitor_aplus_notes")) or None,
        what_to_reference=_text(payload.get("what_to_reference")) or None,
        what_to_avoid=_text(payload.get("what_to_avoid")) or None,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def project_detail(db: Session, project_id: int, user_id: int | None = None) -> dict[str, Any]:
    project = get_listing_project(db, project_id, user_id=user_id)
    inputs = db.execute(select(ListingProjectInput).where(ListingProjectInput.project_id == project_id)).scalar_one_or_none()
    competitors = db.execute(select(CompetitorReference).where(CompetitorReference.project_id == project_id).order_by(desc(CompetitorReference.created_at))).scalars().all()
    listings = db.execute(select(ListingVersion).where(ListingVersion.project_id == project_id).order_by(desc(ListingVersion.created_at))).scalars().all()
    images = db.execute(select(ImagePromptVersion).where(ImagePromptVersion.project_id == project_id).order_by(desc(ImagePromptVersion.created_at))).scalars().all()
    aplus = db.execute(select(AplusVersion).where(AplusVersion.project_id == project_id).order_by(desc(AplusVersion.created_at))).scalars().all()
    return {
        "project": serialize_project(project),
        "inputs": serialize_inputs(inputs),
        "competitors": [serialize_competitor(item) for item in competitors],
        "listing_versions": [serialize_listing(item) for item in listings],
        "image_prompt_versions": [serialize_image_prompt(item) for item in images],
        "aplus_versions": [serialize_aplus(item) for item in aplus],
    }


def _context(db: Session, project_id: int, user_id: int | None = None) -> tuple[ListingProject, ListingProjectInput | None, list[CompetitorReference]]:
    project = get_listing_project(db, project_id, user_id=user_id)
    inputs = db.execute(select(ListingProjectInput).where(ListingProjectInput.project_id == project_id)).scalar_one_or_none()
    competitors = db.execute(select(CompetitorReference).where(CompetitorReference.project_id == project_id)).scalars().all()
    return project, inputs, competitors


def _competitor_terms(competitors: list[CompetitorReference], limit: int = 16) -> list[str]:
    words: dict[str, int] = {}
    stop_words = {"with", "from", "this", "that", "product", "amazon", "inch", "pack", "tool", "tools"}
    for ref in competitors:
        url_text = re.sub(r"https?://|www\.|amazon\.com|dp|gp|product|ref|qid|keywords|[A-Z0-9]{10}", " ", _text(ref.competitor_url), flags=re.I)
        url_text = re.sub(r"[/_?=&.%+-]+", " ", url_text)
        text = " ".join([
            url_text,
            _text(ref.competitor_title),
            _text(ref.competitor_bullets),
            _text(ref.competitor_description),
            _text(ref.competitor_image_notes),
            _text(ref.competitor_aplus_notes),
        ])
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text.lower()):
            if word in stop_words:
                continue
            words[word] = words.get(word, 0) + 1
    return [word for word, _ in sorted(words.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _base_keywords(inputs: ListingProjectInput | None, competitors: list[CompetitorReference] | None = None) -> list[str]:
    if not inputs:
        return _competitor_terms(competitors or [])
    terms = []
    for field in [inputs.main_keywords, inputs.secondary_keywords, inputs.long_tail_keywords, inputs.compatibility_keywords]:
        terms.extend(_split_terms(field))
    terms.extend(_competitor_terms(competitors or []))
    seen = set()
    clean = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            clean.append(term)
    return clean


def _competitor_insights(competitors: list[CompetitorReference]) -> str:
    words: dict[str, int] = {}
    for term in _competitor_terms(competitors, limit=12):
        words[term] = 1
    top = sorted(words.items(), key=lambda item: item[1], reverse=True)[:12]
    if not top:
        return "同行资料较少，主要依据你的产品资料生成。"
    return "同行常见词/结构参考：" + ", ".join(word for word, _ in top) + "。仅作为关键词和结构参考，不复制同行文案。"


def _risk_notes(inputs: ListingProjectInput | None) -> str:
    forbidden = _split_terms(inputs.forbidden_words if inputs else "")
    risky = sorted(set(RISKY_WORDS + [term.lower() for term in forbidden]))
    return "避免使用高风险表达：" + ", ".join(risky) + "。兼容性产品避免 official/original/authorized，优先使用 Compatible with / Replacement for。"


def generate_listing_versions(db: Session, project_id: int, user_id: int | None = None) -> list[ListingVersion]:
    project, inputs, competitors = _context(db, project_id, user_id=user_id)
    keywords = _base_keywords(inputs, competitors)
    primary = keywords[0] if keywords else (project.product_name or project.project_name)
    size = _text(inputs.size if inputs else "")
    qty = _text(inputs.quantity if inputs else "")
    material = _text(inputs.material if inputs else "")
    compatibility = _text(inputs.compatibility if inputs else "")
    use_cases = _text(inputs.use_cases if inputs else "")
    advantages = _text(inputs.advantages if inputs else "")
    diff = _text(inputs.difference_from_competitors if inputs else "")
    product = project.product_name or project.project_name
    title_parts = [primary, product]
    if size:
        title_parts.append(size)
    if qty:
        title_parts.append(qty)
    if compatibility:
        title_parts.append(f"Compatible with {compatibility}")
    if use_cases:
        title_parts.append(f"for {use_cases}")
    base_title = ", ".join([part for part in title_parts if part])
    backend_terms = " ".join([term for term in keywords[1:] if term.lower() not in base_title.lower()])[:240]
    variants = [
        ("Listing Version 1 - 原始版", base_title),
        ("Listing Version 2 - SEO 优化版", f"{primary} {size} {qty} - {product} for {use_cases}".strip(" -")),
        ("Listing Version 3 - 转化优化版", f"{product}, {primary}, {qty}, Easy Replacement for {use_cases}".strip(" ,")),
        ("Listing Version 4 - 多件装强调版", f"{qty or 'Multi-Pack'} {primary} for {use_cases}, {size}".strip(" ,")),
        ("Listing Version 5 - 专业客户版", f"{primary} for Professional Workshop Use, {material} {size}".strip(" ,")),
    ]
    created = []
    for index, (name, title) in enumerate(variants, start=1):
        bullets = [
            f"Accurate Fit and Specs: Designed for {compatibility or 'selected compatible applications'} with clear size/specification reference: {size or 'see product details'}.",
            f"Built for Real Use: {material or 'Durable construction'} supports {use_cases or 'daily workshop, repair, and replacement tasks'}.",
            f"Package Details: Includes {qty or 'the listed quantity'}; {('does not include ' + inputs.not_included) if inputs and inputs.not_included else 'check compatibility before ordering'}.",
            f"Practical Advantage: {advantages or diff or 'Made for stable replacement, repeat purchase, and small business use cases'}.",
            "Safe Compatibility Wording: Compatible-with wording is used for fitment guidance only; verify dimensions and model before purchase.",
        ]
        version = ListingVersion(
            project_id=project_id,
            version_name=name,
            title=title[:190],
            bullet_1=bullets[0],
            bullet_2=bullets[1],
            bullet_3=bullets[2],
            bullet_4=bullets[3],
            bullet_5=bullets[4],
            description=(
                f"This {product} is designed for {use_cases or 'targeted repair and replacement needs'}. "
                f"It focuses on accurate specifications, practical compatibility, and clear package information. "
                f"{_text(inputs.warning_limitation if inputs else '')} "
                "Review the size, included items, and compatibility notes before purchase."
            ).strip(),
            backend_search_terms=backend_terms,
            seo_score=min(95, 72 + len(keywords) * 2 + index),
            conversion_score=min(95, 70 + (5 if advantages else 0) + (5 if compatibility else 0) + index),
            compliance_risk_notes=_risk_notes(inputs),
            generation_notes=_competitor_insights(competitors),
        )
        db.add(version)
        created.append(version)
    project.status = "ready"
    db.commit()
    for item in created:
        db.refresh(item)
    return created


IMAGE_TYPES = [
    ("Main Image", "Show exact product clearly on pure white background"),
    ("Size Image", "Explain dimensions and key specifications"),
    ("Feature Image", "Show material, durability, and main benefit"),
    ("Compatibility Image", "Show compatible models or fitment notes without third-party logos"),
    ("Application Image", "Show realistic use case or workshop context"),
    ("Package Includes Image", "Show included quantity and what is not included"),
    ("A+ Banner", "Brand-style wide hero image"),
    ("A+ Feature Module", "Explain top features in a clean module"),
    ("A+ Comparison Chart", "Compare variants/specs without misleading claims"),
]


def generate_image_prompts(db: Session, project_id: int, user_id: int | None = None) -> list[ImagePromptVersion]:
    project, inputs, competitors = _context(db, project_id, user_id=user_id)
    product = project.product_name or project.project_name
    competitor_note = "Use competitor reference only as layout inspiration. Do not copy exact design, text, logo, brand, product appearance, or copyrighted elements."
    created = []
    for image_type, goal in IMAGE_TYPES:
        main_rules = (
            "Use the uploaded product photo as the exact product reference. Keep product shape, size, material, color, and quantity consistent. "
            "Do not add misleading accessories."
        )
        if image_type == "Main Image":
            image_text = "No text on image"
            prompt_en = (
                f"{main_rules} Create a clean Amazon main image for {product} on a pure white background. "
                "Show the product clearly and accurately, no extra props, no text, no logo, no watermark, no hands, no background scene. "
                "Professional, sharp, high-resolution, suitable for Amazon listing."
            )
        else:
            image_text = {
                "Size Image": f"Size: {_text(inputs.size if inputs else '') or 'Add exact size'}",
                "Feature Image": _text(inputs.advantages if inputs else "") or "Key Features",
                "Compatibility Image": f"Compatible with: {_text(inputs.compatibility if inputs else '') or 'selected models'}",
                "Application Image": _text(inputs.use_cases if inputs else "") or "Application Scenarios",
                "Package Includes Image": f"Package Includes: {_text(inputs.package_includes if inputs else '') or _text(inputs.quantity if inputs else '')}",
            }.get(image_type, project.brand or product)
            prompt_en = (
                f"{main_rules} Create a professional Amazon infographic image for {product}. "
                f"Image goal: {goal}. Add clean readable callouts: {image_text}. "
                "Use modern spacing, clear hierarchy, realistic lighting, and high readability. "
                "Do not include third-party logos or official authorization claims. "
                f"{competitor_note}"
            )
        prompt = ImagePromptVersion(
            project_id=project_id,
            version_name=f"{image_type} Prompt V1",
            image_type=image_type,
            image_goal=goal,
            required_reference_images="真实产品图；如有包装图/使用图/同行图，仅作为辅助参考",
            reference_usage_notes=f"真实产品图用于外观准确性。{competitor_note}",
            image_text=image_text,
            prompt_en=prompt_en,
            prompt_cn=f"为 {product} 生成 {image_type}。保持真实产品外观、尺寸、材质、颜色和数量一致。{goal}。不要复制同行图片或品牌元素。",
            negative_prompt="Do not change product shape. Do not add brand logos. Do not add misleading accessories. Do not copy competitor images. Do not create a different product. No cluttered background.",
            size_recommendation="Amazon square 2000x2000 for listing images; A+ banner 1464x600 or platform-specific module size.",
            notes=_text(inputs.warning_limitation if inputs else "") or None,
        )
        db.add(prompt)
        created.append(prompt)
    project.status = "ready"
    db.commit()
    for item in created:
        db.refresh(item)
    return created


def generate_aplus_version(db: Session, project_id: int, user_id: int | None = None) -> AplusVersion:
    project, inputs, competitors = _context(db, project_id, user_id=user_id)
    product = project.product_name or project.project_name
    features = [
        {"module": "Core Feature", "copy_en": _text(inputs.advantages if inputs else "") or "Clear specifications and dependable replacement performance.", "image_prompt": "Create a clean feature module showing product close-up with 3 benefit callouts."},
        {"module": "Application", "copy_en": _text(inputs.use_cases if inputs else "") or "Designed for workshop, repair, and replacement use cases.", "image_prompt": "Create a realistic application image using the product in the correct context without changing product appearance."},
        {"module": "Compatibility", "copy_en": _text(inputs.compatibility if inputs else "") or "Check dimensions and compatibility before purchase.", "image_prompt": "Create a compatibility module with model list callouts, no third-party logos, no official claim."},
    ]
    version = AplusVersion(
        project_id=project_id,
        version_name="A+ Version 1 - 标准结构",
        banner_copy=f"{product} | Clear Specs, Practical Fit, Reliable Replacement",
        brand_story_copy=f"{project.brand or 'Our brand'} focuses on practical tools and replacement parts for buyers who care about accurate specifications, repeat use, and dependable value.",
        feature_modules=str(features),
        specification_module=f"Specifications: size={_text(inputs.size if inputs else '')}; material={_text(inputs.material if inputs else '')}; color={_text(inputs.color if inputs else '')}; quantity={_text(inputs.quantity if inputs else '')}.",
        application_module=_text(inputs.use_cases if inputs else "") or "Workshop, repair, replacement, and small business use cases.",
        comparison_chart="Compare by size, quantity, compatibility, material, package includes, and target use case. Do not claim superiority without proof.",
        image_prompt_notes=_competitor_insights(competitors) + " A+ 图片可偏品牌化和场景化，但不得复制同行排版、Logo、文字和版权元素。",
    )
    db.add(version)
    project.status = "ready"
    db.commit()
    db.refresh(version)
    return version


def serialize_project(item: ListingProject) -> dict[str, Any]:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "project_name": item.project_name,
        "marketplace": item.marketplace,
        "brand": item.brand,
        "category": item.category,
        "product_name": item.product_name,
        "target_price": item.target_price,
        "fulfillment_method": item.fulfillment_method,
        "status": item.status,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def serialize_inputs(item: ListingProjectInput | None) -> dict[str, Any] | None:
    if not item:
        return None
    fields = [column.name for column in ListingProjectInput.__table__.columns]
    return {field: getattr(item, field) for field in fields}


def serialize_competitor(item: CompetitorReference) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in CompetitorReference.__table__.columns}


def serialize_listing(item: ListingVersion) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in ListingVersion.__table__.columns}


def serialize_image_prompt(item: ImagePromptVersion) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in ImagePromptVersion.__table__.columns}


def serialize_aplus(item: AplusVersion) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in AplusVersion.__table__.columns}
