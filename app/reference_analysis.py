from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings
from app.llm_client import get_openai_client


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(items: list[str], limit: int = 12) -> list[str]:
    seen = set()
    output = []
    for item in items:
        clean = _text(item)
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output[:limit]


def _facts_from_reference(ref: dict[str, Any]) -> dict[str, Any]:
    product = ref.get("productData") or ref.get("serpapiProduct") or ref
    facts = product.get("normalizedFacts") if isinstance(product, dict) else {}
    return facts if isinstance(facts, dict) else {}


def _local_reference_insights(references: list[dict[str, Any]], confirmed_facts: dict[str, Any] | None = None) -> dict[str, Any]:
    titles: list[str] = []
    bullets: list[str] = []
    categories: list[str] = []
    image_hints: list[str] = []
    risky: list[str] = []
    candidates: dict[str, list[str]] = {}
    for ref in references:
        product = ref.get("productData") or ref.get("serpapiProduct") or ref
        if not isinstance(product, dict):
            continue
        titles.append(_text(product.get("title")))
        categories.extend([_text(item) for item in _as_list(product.get("categories"))])
        bullets.extend([_text(item) for item in _as_list(product.get("aboutItem"))])
        if product.get("mainImage"):
            image_hints.append("主图通常突出产品本体、材质边缘、孔径/尺寸关系。")
        if len(_as_list(product.get("images"))) >= 4:
            image_hints.append("竞品图片集通常包含主图、尺寸图、卖点图、使用场景图和包装图。")
        facts = _facts_from_reference(ref)
        for key, value in facts.items():
            if value:
                candidates.setdefault(key, []).append(_text(value))
        risk_text = " ".join([_text(product.get("title")), " ".join(bullets)])
        for word in ["official", "original", "authorized", "guaranteed", "lifetime warranty", "best"]:
            if re.search(rf"\b{re.escape(word)}\b", risk_text, re.I):
                risky.append(word)
    all_text = " ".join(titles + bullets)
    common_terms = re.findall(r"[A-Za-z][A-Za-z0-9+-]{3,}", all_text.lower())
    stop = {"with", "from", "this", "that", "product", "amazon", "inch", "pack", "tools", "for", "and", "the"}
    ranked = sorted({word for word in common_terms if word not in stop})[:18]
    fact_candidates = {key: _unique(values, limit=5) for key, values in candidates.items() if _unique(values, limit=5)}
    return {
        "categorySignals": _unique(categories + ranked, limit=18),
        "commonVisualPatterns": _unique(image_hints + ["不要照搬竞品构图，只借鉴模块类型和信息层级。"], limit=10),
        "commonImageTypes": ["main_image_clean", "dimension", "feature", "compatibility", "application", "package"],
        "safeStyleHints": ["clean Amazon infographic", "clear measurement callouts", "realistic material lighting", "plain non-branded workshop context"],
        "safeCompositionHints": ["主图白底居中", "尺寸图用箭头和标注", "卖点图突出材质/耐用/适配", "场景图避免出现第三方 Logo"],
        "buyerConcernHints": _unique(["尺寸是否正确", "孔径/厚度是否适配", "材质是否真实", "包装数量是否清楚", "是否包含附件"], limit=10),
        "overlayTextPatterns": ["Size", "Material", "Package Includes", "Compatible with", "Check dimensions before ordering"],
        "productFactsCandidates": fact_candidates,
        "riskyClaimsFound": _unique(risky, limit=10),
        "brandOrTrademarkRisks": ["不要使用竞品品牌 Logo、包装、A+ 版式、官方授权措辞。"],
        "unsafeToCopy": ["图片", "Logo", "品牌名", "包装设计", "独特版式", "完整标题/五点文案"],
        "recommendedQuestionsForUser": ["确认真实尺寸、材质、孔径、厚度、包装数量。", "上传自己的产品主图作为唯一外观依据。"],
        "warnings": ["竞品规格只能作为候选事实，必须由卖家确认后才能写进 Prompt。"],
        "analysisMode": "local_rules",
        "model": "",
    }


def analyze_references(
    references: list[dict[str, Any]],
    confirmed_facts: dict[str, Any] | None = None,
    use_model: bool = True,
    model: str | None = None,
) -> dict[str, Any]:
    base = _local_reference_insights(references, confirmed_facts=confirmed_facts)
    settings = get_settings()
    selected_model = _text(model) or settings.openai_text_model or settings.openai_model
    if not use_model or not settings.openai_api_key or not references:
        return base
    safe_payload = {
        "similar_product_references": references[:8],
        "confirmed_product_facts": confirmed_facts or {},
        "local_rule_insights": base,
    }
    prompt = f"""Analyze these Amazon reference products from normalized SerpApi JSON.
Use only structured JSON. Do not infer hidden facts from URLs.
Do not copy competitor copy, images, logos, packaging, or unique layouts.
Return valid JSON with these keys:
categorySignals, commonVisualPatterns, commonImageTypes, safeStyleHints, safeCompositionHints,
buyerConcernHints, overlayTextPatterns, productFactsCandidates, riskyClaimsFound,
brandOrTrademarkRisks, unsafeToCopy, recommendedQuestionsForUser, warnings.

Input JSON:
{json.dumps(safe_payload, ensure_ascii=False, default=str)}
"""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are an Amazon listing image reference analyst. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        if not isinstance(data, dict):
            return base
        merged = {**base, **data}
        merged["analysisMode"] = "llm"
        merged["model"] = selected_model
        return merged
    except Exception as exc:
        base["warnings"] = _as_list(base.get("warnings")) + [f"模型分析失败，已使用本地规则兜底：{exc}"]
        return base
