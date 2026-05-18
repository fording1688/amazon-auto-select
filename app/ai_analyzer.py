from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT
from app.scoring import classify_decision


def _fallback_analysis(product: dict, score_result: dict, error: str | None = None) -> dict[str, Any]:
    price = float(product.get("price") or 0)
    score = int(score_result["opportunity_score"])
    decision = classify_decision(score)
    pack_prices = {
        "single_pack_price": f"${price:.2f}" if price else "",
        "three_pack_price": f"${price * 2.65:.2f}" if price else "",
        "five_pack_price": f"${price * 4.25:.2f}" if price else "",
        "ten_pack_price": f"${price * 8.00:.2f}" if price else "",
    }
    return {
        "decision": decision,
        "opportunity_score": score,
        "summary": f"规则评分显示该产品适合进入“{decision}”池，建议先用 mock/规则报告做初筛。",
        "reasons": [
            "属于五金工具/耗材/替换件方向，符合小众复购型选品偏好。",
            "价格区间和评论量具备初步测试价值。",
            "可通过 3-pack、5-pack 或 10-pack 做差异化和客单价提升。",
        ],
        "risks": [
            "当前为规则兜底分析，未调用 OpenAI 或返回 JSON 解析失败。",
            error or "需要进一步核查侵权、适配型号和真实供应链成本。",
        ],
        "bundle_strategy": {
            "suitable_for_bundle": score >= 60,
            "recommended_packs": ["3-pack", "5-pack", "10-pack"] if score >= 60 else ["1-pack"],
            "reason": "耗材/替换件适合用多件装降低单件到手价，并提高 FBM 测款客单价。",
        },
        "pricing_suggestion": pack_prices,
        "listing_suggestion": {
            "title": f"{product.get('title', '')[:120]} for Replacement and Workshop Use",
            "bullet_points": [
                "Designed for repair, replacement, and workshop inventory needs.",
                "Offer multi-pack options for frequent users and small shops.",
                "Check compatibility before purchase to reduce returns.",
                "Clear size and application images should be shown in listing.",
                "Use FBM small batch testing before expanding inventory.",
            ],
            "description": "先用小批量 FBM 验证点击率、转化率和真实售后问题。",
        },
        "image_selling_points": ["主图展示数量和规格", "尺寸图", "适配场景", "材料/工艺", "多件装对比"],
        "ad_keywords": [product.get("keyword", ""), "replacement parts", "compatible tool accessory"],
        "negative_keywords": ["free", "manual", "used"],
        "fbm_test_plan_14_days": {
            "day_1_to_3": "上架 1-pack 和 3-pack，低预算精准词测试。",
            "day_4_to_7": "根据点击和转化筛选关键词，补充 5-pack 价格锚点。",
            "day_8_to_14": "保留 ACOS 可控词，观察退货和咨询问题。",
            "success_criteria": "CTR > 0.4%，14 天有稳定加购或出单，毛利覆盖广告。",
            "stop_loss_criteria": "点击无转化、适配问题多、价格被头部竞品压制。",
        },
        "next_action": "先核算采购成本和尺寸重量，再建立 3-pack/5-pack FBM 测试链接。",
        "raw_ai_response": "",
    }


def analyze_product(product: dict, score_result: dict) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        return _fallback_analysis(product, score_result, "未配置 OPENAI_API_KEY，已使用本地规则兜底分析。")

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        product_json=json.dumps(product, ensure_ascii=False, indent=2),
        score_json=json.dumps(score_result, ensure_ascii=False, indent=2),
    )
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        data["raw_ai_response"] = raw
        data["opportunity_score"] = int(data.get("opportunity_score") or score_result["opportunity_score"])
        data["decision"] = data.get("decision") or classify_decision(data["opportunity_score"])
        return data
    except Exception as exc:
        fallback = _fallback_analysis(product, score_result, f"AI 分析失败：{exc}")
        fallback["raw_ai_response"] = str(exc)
        return fallback
