from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm_client import get_openai_client
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


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _without_image_data(context: dict[str, Any]) -> dict[str, Any]:
    safe_context = dict(context)
    image = dict(safe_context.get("product_reference_image") or {})
    if image.get("data_url"):
        image["has_uploaded_image_data"] = True
        image["data_url"] = "[omitted from text context; attached as image input]"
    safe_context["product_reference_image"] = image
    return safe_context


def _image_data_url(context: dict[str, Any]) -> str:
    image = context.get("product_reference_image") or {}
    data_url = _text(image.get("data_url"))
    if data_url.startswith("data:image/"):
        return data_url
    return ""


def _model_source_from_note(note: str | None) -> str:
    match = re.search(r"Model:\s*([^\n]+)", _text(note))
    return match.group(1).strip().rstrip(".") if match else ""


def _safe_json_loads(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return json.loads(raw)


def _as_list(value: Any, limit: int | None = None) -> list[Any]:
    if isinstance(value, list):
        items = value
    elif value:
        items = [value]
    else:
        items = []
    return items[:limit] if limit else items


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def _safe_count(value: Any, default: int = 5, min_value: int = 1, max_value: int = 10) -> int:
    try:
        count = int(float(value))
    except (TypeError, ValueError):
        count = default
    return max(min_value, min(max_value, count))


def _url_reference_summary(url: str | None) -> dict[str, Any]:
    text = _text(url)
    if not text:
        return {"asin": "", "slug_terms": [], "inferred_title": ""}
    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", text, flags=re.I)
    cleaned = re.sub(r"https?://|www\.|amazon\.com|dp|gp|product|ref|qid|keywords|[A-Z0-9]{10}", " ", text, flags=re.I)
    cleaned = re.sub(r"[/_?=&.%+-]+", " ", cleaned)
    terms = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", cleaned)
        if word.lower() not in {"com", "www", "amazon", "the", "and", "for", "with"}
    ]
    return {
        "asin": asin_match.group(1).upper() if asin_match else "",
        "slug_terms": terms[:24],
        "inferred_title": " ".join(terms[:18]),
    }


def _build_ai_context(
    project: ListingProject,
    inputs: ListingProjectInput | None,
    competitors: list[CompetitorReference],
    selected_model: str | None = None,
    version_count: int = 1,
    product_reference_image: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_data = {}
    if inputs:
        input_data = {
            field: _text(getattr(inputs, field))
            for field in INPUT_FIELDS
            if _text(getattr(inputs, field))
        }
    competitor_data = []
    for index, ref in enumerate(competitors[:12], start=1):
        url_summary = _url_reference_summary(ref.competitor_url)
        competitor_data.append(
            {
                "ref_id": f"COMP-{index:02d}",
                "url": ref.competitor_url,
                "asin": url_summary["asin"],
                "slug_terms": url_summary["slug_terms"],
                "inferred_title_from_url": url_summary["inferred_title"],
                "what_to_reference": ref.what_to_reference,
                "what_to_avoid": ref.what_to_avoid,
            }
        )
    return {
        "marketplace": project.marketplace,
        "category": project.category,
        "product_name": project.product_name or project.project_name,
        "target_price": project.target_price,
        "fulfillment_method": project.fulfillment_method,
        "seller_notes": project.notes,
        "product_inputs": input_data,
        "competitor_references": competitor_data,
        "derived_competitor_terms": _competitor_terms(competitors, limit=20),
        "selected_model": _text(selected_model),
        "version_count": version_count,
        "product_reference_image": product_reference_image or {},
        "privacy_note": "Do not infer or expose seller identity, account, email, store name, supplier, cost, or private operational data.",
    }


def _call_listing_llm(task: str, context: dict[str, Any], schema_hint: str, model: str | None = None) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    selected_model = _text(model) or settings.openai_model
    client = get_openai_client()
    system_prompt = (
        "You are a senior Amazon US listing strategist for hardware tools, diamond tools, CBN grinding wheels, "
        "glass tools, industrial consumables, and replacement parts. Generate practical, conversion-oriented, "
        "Amazon-compliant content. Use competitor URLs only for keyword/category/structure inspiration. "
        "Do not copy competitor copy, images, logos, brand claims, or copyrighted expression. "
        "Avoid high-risk words such as best, guaranteed, official, original, authorized, lifetime unless the seller proves them. "
        "Output valid JSON only."
    )
    has_image = bool(_image_data_url(context))
    user_prompt = f"""Task: {task}

Seller goal:
- Build a practical Amazon US listing draft for a niche tool/consumable/replacement product.
- Prefer clear specs, compatibility wording, package quantity, use cases, and buyer risk reduction.
- If compatibility is involved, use "Compatible with" / "Replacement for" style wording and avoid official affiliation claims.
- Deeply use competitor links as reference: infer keywords, product positioning, image module ideas, packaging angle, compatibility wording, and selling point structure from URL slugs, ASIN references, and seller notes.
- For image prompts, the seller's own main product reference image controls product identity and appearance. Competitor links are only for module/storyboard inspiration.
- If an image is attached, inspect the visible product shape, color, material, package quantity, proportions, holes/edges/surface details, and carry those constraints into every image prompt.
- Every image prompt must be ready to paste into ChatGPT image generation together with the seller's product reference photo.
- Every image prompt must include these concise sections inside prompt_en: Goal, Product lock, Scene/composition, On-image text, Amazon compliance, Negative constraints.
- Product lock must explicitly say not to change the product category, shape, material, visible color, coating, arbor/hole, thickness, quantity, package contents, or scale relationships shown in the seller reference image.
- For Main Image, require pure white background, no props, no text, product centered, Amazon-ready square image.
- For Size Image, require exact measurement callouts from product inputs and avoid invented specs.
- For Feature/Application images, keep the same product appearance from the reference photo and only change environment, annotations, or safe supporting props.
- Do not hallucinate a different product. If the product appearance is unclear, say what reference image is still needed.
- Do not include private seller identity or store data.

Context JSON:
{_json(_without_image_data(context))}

Image attachment:
{"A seller main product reference image is attached. Use it for product appearance accuracy." if has_image else "No image data attached; rely on product inputs and ask for a real product image where needed."}

Required JSON shape:
{schema_hint}
"""
    user_message: dict[str, Any]
    image_url = _image_data_url(context)
    if image_url:
        user_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    else:
        user_message = {"role": "user", "content": user_prompt}
    response = client.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "system", "content": system_prompt},
            user_message,
        ],
        temperature=0.55,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    return _safe_json_loads(raw)


def _ai_listing_data(context: dict[str, Any]) -> dict[str, Any] | None:
    count = _safe_count(context.get("version_count"), default=1, max_value=10)
    schema = """{
  "versions": [
    {
      "version_name": "Listing Version 1 - SEO Balanced",
      "title": "Amazon title, max 190 chars",
      "bullet_points": ["five bullet points, English, concrete specs and benefits"],
      "description": "English product description",
      "backend_search_terms": "search terms under 240 bytes, no commas if possible",
      "seo_score": 0-100,
      "conversion_score": 0-100,
      "compliance_risk_notes": "Chinese risk notes",
      "generation_notes": "Chinese explanation of strategy"
    }
  ]
}"""
    return _call_listing_llm(f"Generate exactly {count} differentiated Amazon listing copy versions.", context, schema, context.get("selected_model"))


def _ai_image_prompt_data(context: dict[str, Any]) -> dict[str, Any] | None:
    image_set_count = _safe_count(context.get("image_set_count"), default=1, max_value=5)
    image_types = _as_list(context.get("image_types_per_set"))
    count = image_set_count * max(1, len(image_types))
    schema = """{
  "image_prompts": [
    {
      "version_name": "Main Image Prompt V1",
      "image_type": "Main Image / Size Image / Feature Image / Compatibility Image / Application Image / Package Includes Image",
      "image_goal": "goal",
      "required_reference_images": "what real images user should provide",
      "reference_usage_notes": "how to use references safely",
      "image_text": "exact text/callouts for the image, or No text on image",
      "prompt_en": "Ready-to-copy English prompt for ChatGPT image generation. It must assume the user will attach the seller product reference photo. Include Goal, Product lock, Scene/composition, On-image text, Amazon compliance, Negative constraints. Be specific enough to generate this exact seller product image, not a generic product.",
      "prompt_cn": "Chinese explanation. Explain how to use this prompt: upload seller product main photo first, then paste prompt. Explain what product details are locked and what can vary.",
      "negative_prompt": "Specific negative prompt: what must not appear or change",
      "size_recommendation": "Amazon image size recommendation",
      "notes": "Chinese operational note"
    }
  ]
}"""
    return _call_listing_llm(
        "Generate exactly "
        f"{count} Amazon listing image prompts using the selected model: {image_set_count} complete product image set(s), "
        f"each set covering these listing image types only: {', '.join(str(item) for item in image_types)}. "
        "Do not generate A+ image modules here. Do not produce generic prompts. "
        "The output prompt_en must be strong enough that if the seller uploads their product photo to ChatGPT and pastes prompt_en, ChatGPT knows exactly what image to create while preserving the real product.",
        context,
        schema,
        context.get("selected_model"),
    )


def _ai_aplus_data(context: dict[str, Any]) -> dict[str, Any] | None:
    schema = """{
  "aplus": {
    "version_name": "A+ Version 1 - Conversion Structure",
    "banner_copy": "English banner copy",
    "brand_story_copy": "English brand story without private seller name",
    "feature_modules": "JSON string or readable module list with module title, copy and image direction",
    "specification_module": "spec table copy",
    "application_module": "application/use-case module copy",
    "comparison_chart": "comparison chart plan",
    "image_prompt_notes": "Chinese image prompt and compliance notes"
  }
}"""
    return _call_listing_llm("Generate a practical Amazon A+ content plan.", context, schema, context.get("selected_model"))


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


def delete_listing_project(db: Session, project_id: int, user_id: int | None = None) -> dict[str, int | bool]:
    project = get_listing_project(db, project_id, user_id=user_id)
    counts = {
        "inputs": 0,
        "competitors": 0,
        "listing_versions": 0,
        "image_prompt_versions": 0,
        "aplus_versions": 0,
    }
    for model, key in [
        (ListingProjectInput, "inputs"),
        (CompetitorReference, "competitors"),
        (ListingVersion, "listing_versions"),
        (ImagePromptVersion, "image_prompt_versions"),
        (AplusVersion, "aplus_versions"),
    ]:
        counts[key] = db.execute(select(func.count()).select_from(model).where(model.project_id == project_id)).scalar_one()
        db.execute(delete(model).where(model.project_id == project_id))
    db.flush()
    db.delete(project)
    db.commit()
    return {"ok": True, "deleted_id": project_id, **counts}


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


def generate_listing_versions(
    db: Session,
    project_id: int,
    user_id: int | None = None,
    model: str | None = None,
    version_count: int = 1,
    product_reference_image: dict[str, Any] | None = None,
) -> list[ListingVersion]:
    project, inputs, competitors = _context(db, project_id, user_id=user_id)
    selected_model = _text(model) or get_settings().openai_model
    count = _safe_count(version_count, default=1, max_value=10)
    try:
        ai_data = _ai_listing_data(_build_ai_context(project, inputs, competitors, selected_model=selected_model, version_count=count, product_reference_image=product_reference_image))
    except Exception:
        ai_data = None
    if ai_data and _as_list(ai_data.get("versions")):
        created = []
        for index, item in enumerate(_as_list(ai_data.get("versions"), limit=count), start=1):
            bullets = [str(bullet or "").strip() for bullet in _as_list(item.get("bullet_points"), limit=5)]
            bullets = (bullets + [""] * 5)[:5]
            version = ListingVersion(
                project_id=project_id,
                version_name=_text(item.get("version_name")) or f"AI Listing Version {index}",
                title=_text(item.get("title"))[:190],
                bullet_1=bullets[0],
                bullet_2=bullets[1],
                bullet_3=bullets[2],
                bullet_4=bullets[3],
                bullet_5=bullets[4],
                description=_text(item.get("description")),
                backend_search_terms=_text(item.get("backend_search_terms"))[:240],
                seo_score=_safe_float(item.get("seo_score")),
                conversion_score=_safe_float(item.get("conversion_score")),
                compliance_risk_notes=_text(item.get("compliance_risk_notes")) or _risk_notes(inputs),
                generation_notes=(_text(item.get("generation_notes")) or "AI generated via configured LLM.") + f" Model: {selected_model}.",
            )
            db.add(version)
            created.append(version)
        project.status = "ready"
        db.commit()
        for item in created:
            db.refresh(item)
        return created

    raise ValueError(
        f"Listing 文案必须由模型生成，本次模型 {selected_model} 没有返回有效 JSON。"
        "请检查 OpenRouter/OpenAI Key、模型名称、余额，或换用 openai/gpt-4o、openai/gpt-4.1-mini、anthropic/claude-3.5-sonnet 后重试。"
    )


IMAGE_TYPES = [
    ("Main Image", "Show exact product clearly on pure white background"),
    ("Size Image", "Explain dimensions and key specifications"),
    ("Feature Image", "Show material, durability, and main benefit"),
    ("Compatibility Image", "Show compatible models or fitment notes without third-party logos"),
    ("Application Image", "Show realistic use case or workshop context"),
    ("Package Includes Image", "Show included quantity and what is not included"),
]


def generate_image_prompts(
    db: Session,
    project_id: int,
    user_id: int | None = None,
    model: str | None = None,
    version_count: int = 1,
    product_reference_image: dict[str, Any] | None = None,
) -> list[ImagePromptVersion]:
    project, inputs, competitors = _context(db, project_id, user_id=user_id)
    selected_model = _text(model) or get_settings().openai_model
    image_set_count = _safe_count(version_count, default=1, max_value=5)
    count = image_set_count * len(IMAGE_TYPES)
    try:
        context = _build_ai_context(
            project,
            inputs,
            competitors,
            selected_model=selected_model,
            version_count=count,
            product_reference_image=product_reference_image,
        )
        context["image_set_count"] = image_set_count
        context["image_types_per_set"] = [name for name, _ in IMAGE_TYPES]
        ai_data = _ai_image_prompt_data(context)
    except Exception:
        ai_data = None
    if ai_data and _as_list(ai_data.get("image_prompts")):
        created = []
        for index, item in enumerate(_as_list(ai_data.get("image_prompts"), limit=count), start=1):
            prompt = ImagePromptVersion(
                project_id=project_id,
                version_name=_text(item.get("version_name")) or f"AI Image Prompt {index}",
                image_type=_text(item.get("image_type")) or "Listing Image",
                image_goal=_text(item.get("image_goal")),
                required_reference_images=_text(item.get("required_reference_images")) or "真实产品图；包装图；必要时上传使用场景图。",
                reference_usage_notes=_text(item.get("reference_usage_notes")) or "真实产品图用于外观准确性，同行资料只用于结构参考，不复制。",
                image_text=_text(item.get("image_text")),
                prompt_en=_text(item.get("prompt_en")),
                prompt_cn=_text(item.get("prompt_cn")),
                negative_prompt=_text(item.get("negative_prompt")) or "Do not copy competitor images, logos, brand elements, or misleading accessories.",
                size_recommendation=_text(item.get("size_recommendation")) or "Amazon square 2000x2000 for listing images.",
                notes=(_text(item.get("notes")) or "AI generated image prompt.") + f" Model: {selected_model}.",
            )
            db.add(prompt)
            created.append(prompt)
        project.status = "ready"
        db.commit()
        for item in created:
            db.refresh(item)
        return created

    raise ValueError(
        f"图片 Prompt 必须由模型生成，本次模型 {selected_model} 没有返回有效 JSON。"
        "请检查 OpenRouter/OpenAI Key、模型是否支持视觉输入，或换用 openai/gpt-4o、google/gemini-2.5-pro 等视觉模型后重试。"
    )


def generate_aplus_version(
    db: Session,
    project_id: int,
    user_id: int | None = None,
    model: str | None = None,
    version_count: int = 1,
    product_reference_image: dict[str, Any] | None = None,
) -> AplusVersion:
    project, inputs, competitors = _context(db, project_id, user_id=user_id)
    selected_model = _text(model) or get_settings().openai_model
    try:
        ai_data = _ai_aplus_data(_build_ai_context(project, inputs, competitors, selected_model=selected_model, version_count=_safe_count(version_count, default=1, max_value=5), product_reference_image=product_reference_image))
    except Exception:
        ai_data = None
    if ai_data and isinstance(ai_data.get("aplus"), dict):
        item = ai_data["aplus"]
        version = AplusVersion(
            project_id=project_id,
            version_name=_text(item.get("version_name")) or "AI A+ Version 1",
            banner_copy=_text(item.get("banner_copy")),
            brand_story_copy=_text(item.get("brand_story_copy")),
            feature_modules=_text(item.get("feature_modules")),
            specification_module=_text(item.get("specification_module")),
            application_module=_text(item.get("application_module")),
            comparison_chart=_text(item.get("comparison_chart")),
            image_prompt_notes=(_text(item.get("image_prompt_notes")) or "AI generated A+ plan.") + f" Model: {selected_model}.",
        )
        db.add(version)
        project.status = "ready"
        db.commit()
        db.refresh(version)
        return version

    raise ValueError(
        f"A+ 页面方案必须由模型生成，本次模型 {selected_model} 没有返回有效 JSON。"
        "请检查 OpenRouter/OpenAI Key、模型名称、余额，或换用更稳定的模型后重试。"
    )


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
    data = {column.name: getattr(item, column.name) for column in ListingVersion.__table__.columns}
    data["generated_model"] = _model_source_from_note(data.get("generation_notes"))
    return data


def serialize_image_prompt(item: ImagePromptVersion) -> dict[str, Any]:
    data = {column.name: getattr(item, column.name) for column in ImagePromptVersion.__table__.columns}
    data["generated_model"] = _model_source_from_note(data.get("notes"))
    return data


def serialize_aplus(item: AplusVersion) -> dict[str, Any]:
    data = {column.name: getattr(item, column.name) for column in AplusVersion.__table__.columns}
    data["generated_model"] = _model_source_from_note(data.get("image_prompt_notes"))
    return data
