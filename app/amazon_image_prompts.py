from __future__ import annotations

from typing import Any


IMAGE_TYPES = {
    "main_image_clean": "Main Image",
    "dimension": "Dimension Image",
    "feature": "Feature Image",
    "compatibility": "Compatibility Image",
    "application": "Application Image",
    "package": "Package Includes Image",
    "material": "Material Image",
    "lifestyle": "Lifestyle Image",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _facts_text(facts: dict[str, Any]) -> str:
    pairs = []
    for key in ["productName", "productCategory", "material", "color", "diameter", "thickness", "arborHole", "grit", "quantity", "packageIncludes", "compatibilityTarget"]:
        value = _text(facts.get(key))
        if value:
            pairs.append(f"{key}: {value}")
    return "; ".join(pairs) or "Use only confirmed product facts from seller input."


def validate_amazon_image_request(payload: dict[str, Any]) -> list[str]:
    errors = []
    if not _text(payload.get("imageType")):
        errors.append("imageType is required.")
    if not isinstance(payload.get("confirmedFacts") or {}, dict):
        errors.append("confirmedFacts must be an object.")
    return errors


def build_amazon_image_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_amazon_image_request(payload)
    if errors:
        return {"valid": False, "errors": errors}
    image_type = _text(payload.get("imageType")) or "feature"
    facts = payload.get("confirmedFacts") or {}
    insights = payload.get("referenceInsights") or {}
    overlay_mode = _text(payload.get("overlayTextMode")) or ("none" if image_type == "main_image_clean" else "recommended")
    reference_note = _text(payload.get("productReferenceImageNote")) or "The seller will upload their own product reference photo."
    facts_line = _facts_text(facts)
    visual_patterns = "; ".join((insights.get("safeCompositionHints") or [])[:5]) if isinstance(insights, dict) else ""
    buyer_concerns = "; ".join((insights.get("buyerConcernHints") or [])[:5]) if isinstance(insights, dict) else ""

    if image_type == "main_image_clean":
        overlay_mode = "none"
        prompt_en = (
            "Goal: Create an Amazon-ready main product image.\n"
            f"Product lock: Use the seller uploaded product reference photo as the only source for product appearance. {reference_note} "
            f"Confirmed facts: {facts_line}. Preserve product category, shape, material, visible color, coating, arbor/hole, thickness, quantity, package contents, and scale relationships.\n"
            "Scene/composition: pure white background, product centered, sharp focus, realistic lighting, no shadows that obscure details, square crop.\n"
            "On-image text: none.\n"
            "Amazon compliance: no props, no badges, no logos, no watermark, no packaging unless the real product is sold in packaging and seller confirms it.\n"
            "Negative constraints: text, logo, watermark, badge, people, hands, tools not included, extra products, changed wheel shape, changed hole size, changed coating, misleading accessories."
        )
    else:
        title = IMAGE_TYPES.get(image_type, "Amazon Listing Image")
        overlay = "Use short factual callouts only from confirmed facts." if overlay_mode != "none" else "No overlay text."
        prompt_en = (
            f"Goal: Create a {title} for an Amazon listing.\n"
            f"Product lock: Use the seller uploaded product reference photo as the exact product appearance reference. {reference_note} "
            f"Confirmed facts: {facts_line}. Do not invent dimensions, compatibility, materials, quantity, or included accessories.\n"
            f"Reference insight: Safe composition ideas from similar Amazon products: {visual_patterns or 'clean infographic layout, clear hierarchy, no copied design'}.\n"
            f"Buyer concern to answer: {buyer_concerns or 'make size, material, package quantity, and use case clear'}.\n"
            f"Scene/composition: create an original Amazon infographic layout for this image type. Keep product realistic and consistent with the seller reference image.\n"
            f"On-image text: {overlay}\n"
            "Amazon compliance: do not use competitor logos, official authorization claims, copied packaging, copied photo angles, or unique competitor layouts.\n"
            "Negative constraints: do not change product shape, material, visible color, coating, arbor/hole, thickness, scale, package quantity, or included items; no third-party branding; no unsafe claims."
        )
    return {
        "valid": True,
        "imageType": image_type,
        "overlayTextMode": overlay_mode,
        "promptEn": prompt_en,
        "promptCn": "上传你自己的产品主图作为外观依据，再粘贴英文 Prompt。同行商品只用于模块方向和信息层级参考，不能复制图片、Logo、包装或文案。",
        "negativePrompt": "No competitor logos, no copied competitor images, no misleading accessories, no changed product shape, no changed dimensions, no fake certification, no official/authorized claims.",
        "source": "structured_serpapi_json_plus_confirmed_facts",
    }
