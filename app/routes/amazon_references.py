from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.amazon_image_prompts import build_amazon_image_prompt
from app.amazon_url_parser import parse_amazon_url
from app.auth import get_current_user
from app.models import User
from app.reference_analysis import analyze_references
from app.serpapi_amazon import SerpApiAmazonProductAdapter, SerpApiAmazonSearchAdapter
from app.serpapi_client import SerpApiError


router = APIRouter(prefix="/api", tags=["amazon-references"])


def _domain(payload: dict[str, Any], fallback: str = "amazon.com") -> str:
    return str(payload.get("amazonDomain") or payload.get("amazon_domain") or fallback or "amazon.com").strip()


def _reference_from_product(product: dict[str, Any], allowed_usage: str = "public_analysis_only") -> dict[str, Any]:
    return {
        "id": f"amazon-{product.get('asin') or 'unknown'}",
        "url": product.get("productLink"),
        "asin": product.get("asin"),
        "amazonDomain": product.get("amazonDomain"),
        "platform": "amazon",
        "referenceType": "similar_product",
        "permissionStatus": "public_analysis_only",
        "allowedUsage": allowed_usage,
        "title": product.get("title"),
        "thumbnail": product.get("mainImage"),
        "productData": product,
        "userNotes": "Use for public analysis and layout inspiration only. Do not copy text, images, logos, packaging, or unique layouts.",
    }


@router.post("/amazon/parse-url")
def parse_url(payload: dict[str, Any], user: User = Depends(get_current_user)):
    return parse_amazon_url(str(payload.get("url") or payload.get("input") or ""))


@router.post("/serpapi/amazon-search")
def amazon_search(payload: dict[str, Any], user: User = Depends(get_current_user)):
    keyword = str(payload.get("keyword") or "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="请输入关键词。")
    try:
        return SerpApiAmazonSearchAdapter().search(
            keyword=keyword,
            amazon_domain=_domain(payload),
            language=str(payload.get("language") or "en_US"),
            page=int(payload.get("page") or 1),
            device=str(payload.get("device") or "desktop"),
        )
    except SerpApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/serpapi/amazon-product")
def amazon_product(payload: dict[str, Any], user: User = Depends(get_current_user)):
    asin = str(payload.get("asin") or "").strip().upper()
    if not asin:
        raise HTTPException(status_code=400, detail="请输入 ASIN。")
    try:
        return SerpApiAmazonProductAdapter().product(
            asin=asin,
            amazon_domain=_domain(payload),
            language=str(payload.get("language") or "en_US"),
            device=str(payload.get("device") or "desktop"),
        )
    except SerpApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/serpapi/amazon-product-by-url")
def amazon_product_by_url(payload: dict[str, Any], user: User = Depends(get_current_user)):
    parsed = parse_amazon_url(str(payload.get("url") or ""))
    asin = str(parsed.get("asin") or "").upper()
    if not asin:
        raise HTTPException(status_code=400, detail="没有从链接中解析到 ASIN。")
    domain = str(parsed.get("amazonDomain") or _domain(payload))
    try:
        product = SerpApiAmazonProductAdapter().product(
            asin=asin,
            amazon_domain=domain,
            language=str(payload.get("language") or "en_US"),
            device=str(payload.get("device") or "desktop"),
        )
        return {"parsed": parsed, "product": product, "reference": _reference_from_product(product)}
    except SerpApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/references/analyze")
def analyze(payload: dict[str, Any], user: User = Depends(get_current_user)):
    references = payload.get("references") or payload.get("similarProductReferences") or []
    if not isinstance(references, list):
        raise HTTPException(status_code=400, detail="references 必须是数组。")
    return analyze_references(
        references=references,
        confirmed_facts=payload.get("confirmedFacts") or {},
        use_model=bool(payload.get("useModel", True)),
        model=payload.get("model"),
    )


@router.post("/prompts/amazon-image")
def amazon_image_prompt(payload: dict[str, Any], user: User = Depends(get_current_user)):
    result = build_amazon_image_prompt(payload)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("errors") or ["Prompt 请求不完整。"])
    return result


@router.post("/images/amazon/edit")
def amazon_image_edit(payload: dict[str, Any], user: User = Depends(get_current_user)):
    return {
        "status": "not_enabled",
        "message": "第一版先生成可复制 Prompt，不直接调用生图接口。后续接 OpenAI Images 时仍只允许使用卖家自己的产品参考图。",
    }
