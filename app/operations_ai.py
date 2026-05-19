from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm_client import get_openai_client
from app.models import ImportBatch, OperationsAiReport
from app.report_importer import (
    build_ad_actions,
    build_business_overview,
    build_listing_audits,
    build_sku_dashboard,
)


OPERATIONS_SYSTEM_PROMPT = """你是一名资深亚马逊美国站运营总监和广告操盘手，服务对象是五金工具、金刚石工具、CBN磨轮、玻璃工具、工业耗材、替换件类卖家。

你不是写泛泛建议的顾问。你必须根据给定数据做经营判断，输出能直接执行的运营动作。

要求：
1. 每条动作必须包含明确对象，例如 SKU、ASIN、广告活动、搜索词、Listing 问题。
2. 每条动作必须引用数据证据，例如花费、销售额、ACOS、TACOS、CVR、Session、利润、库存或上传缺口。
3. 每条动作必须具体到“调什么、怎么调、先做什么、观察什么指标”。
4. 不要输出“优化标题”“关注广告”这种空话，必须说清楚优化方向。
5. 如果数据不足，要明确告诉卖家缺哪份报告，缺了以后哪些结论不能下。
6. 不要建议大规模改动；优先给 7 天内能落地、可验证、风险可控的动作。
7. 输出必须是合法 JSON。
"""

OPERATIONS_USER_PROMPT = """请基于下面这组亚马逊运营数据，给出高质量经营建议。

我的经营目标：
- 维护现有盈利链接，先提高利润和广告效率。
- 找出该放量、该止损、该调价、该优化 Listing、该做多件装的 SKU。
- 避免建议我操作已经关闭或无数据支撑的广告。
- 建议要足够具体，最好能直接变成我今天的工作清单。

数据：
{context_json}

请输出 JSON，格式如下：
{{
  "executive_summary": [
    "整体判断1",
    "整体判断2",
    "整体判断3"
  ],
  "urgent_actions": [
    {{
      "priority": "P0/P1/P2",
      "area": "广告/利润/Listing/库存/选品",
      "object": "具体 SKU、ASIN、广告活动或搜索词",
      "evidence": "用数字说明为什么",
      "action": "具体要怎么做",
      "expected_impact": "预期改善什么指标",
      "risk_check": "执行前要确认什么"
    }}
  ],
  "sku_actions": [
    {{
      "sku": "",
      "decision": "放量/控费/优化转化/提价/降价/观察/止损",
      "evidence": "",
      "action": "",
      "watch_metric": ""
    }}
  ],
  "ad_actions": [
    {{
      "campaign_or_term": "",
      "action": "加预算/降价/否定/拆 exact/保留观察/暂停",
      "evidence": "",
      "exact_change": "例如 bid 下调 20%，否定 exact，预算 +20%，或拆到 exact 活动",
      "watch_metric": ""
    }}
  ],
  "listing_actions": [
    {{
      "sku_or_asin": "",
      "problem": "",
      "action": "",
      "image_or_copy_direction": ""
    }}
  ],
  "budget_actions": [
    {{
      "object": "",
      "current_issue": "",
      "budget_or_bid_change": "",
      "reason": ""
    }}
  ],
  "data_gaps": [
    "还缺什么数据，以及缺失会影响什么判断"
  ],
  "next_7_days_plan": {{
    "day_1": "",
    "day_2_to_3": "",
    "day_4_to_7": "",
    "success_criteria": "",
    "stop_loss_criteria": ""
  }},
  "do_not_do": [
    "现在不要做的事情和原因"
  ]
}}
"""


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _safe_json_loads(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    return json.loads(raw)


def build_operations_ai_context(db: Session) -> dict[str, Any]:
    sku_rows = build_sku_dashboard(db)
    ad_actions = build_ad_actions(db)
    listing_audits = build_listing_audits(db)
    business = build_business_overview(db)
    latest_imports = db.execute(select(ImportBatch).order_by(desc(ImportBatch.created_at)).limit(12)).scalars().all()

    return {
        "business_summary": business.get("summary") or {},
        "business_insights": business.get("insights") or [],
        "top_skus_by_profit": [
            {
                "sku": row.sku,
                "asin": row.asin,
                "title": row.title,
                "sales": round(row.sales, 2),
                "units": row.units,
                "sessions": row.sessions,
                "conversion_rate": row.conversion_rate,
                "ad_spend": round(row.ad_spend, 2),
                "ad_sales": round(row.ad_sales, 2),
                "acos": row.acos,
                "tacos": row.tacos,
                "estimated_profit": round(row.estimated_profit, 2),
                "margin": row.margin,
                "tags": row.tags,
                "rule_recommendations": row.recommendations,
            }
            for row in sku_rows[:25]
        ],
        "weak_skus_by_profit": [
            {
                "sku": row.sku,
                "asin": row.asin,
                "title": row.title,
                "sales": round(row.sales, 2),
                "ad_spend": round(row.ad_spend, 2),
                "acos": row.acos,
                "tacos": row.tacos,
                "estimated_profit": round(row.estimated_profit, 2),
                "margin": row.margin,
                "tags": row.tags,
            }
            for row in sorted(sku_rows, key=lambda item: item.estimated_profit)[:15]
        ],
        "rule_ad_actions": ad_actions[:40],
        "listing_audits": listing_audits[:25],
        "latest_imports": [
            {
                "type": item.report_type,
                "file_name": item.file_name,
                "rows": item.row_count,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in latest_imports
        ],
    }


def _fallback_report(error: str, context: dict[str, Any]) -> dict[str, Any]:
    ad_actions = context.get("rule_ad_actions") or []
    sku_rows = context.get("top_skus_by_profit") or []
    listing_audits = context.get("listing_audits") or []
    return {
        "executive_summary": [
            "当前为本地规则兜底报告，大模型未成功返回；可以先按 P0/P1 动作处理最明显的问题。",
            "优先处理有花费、无订单、高 ACOS 的搜索词；其次放大低 ACOS 且有订单的词。",
            "如果缺少成本表，利润判断只能做粗估，调价和放量前需要补成本。",
        ],
        "urgent_actions": [
            {
                "priority": item.get("priority", "P1"),
                "area": "广告",
                "object": item.get("search_term", ""),
                "evidence": f"点击 {item.get('clicks', 0):.0f}，花费 ${item.get('spend', 0):.2f}，销售 ${item.get('sales', 0):.2f}。",
                "action": item.get("action", "保留观察"),
                "expected_impact": "降低浪费花费或把有效词单独放大。",
                "risk_check": "执行前确认该词所在活动仍在启用，并检查是否有最近 3 天订单滞后。",
            }
            for item in ad_actions[:8]
        ],
        "sku_actions": [
            {
                "sku": item.get("sku", ""),
                "decision": "放量" if (item.get("margin") or 0) > 0.25 else "控费",
                "evidence": f"销售 ${item.get('sales', 0):.2f}，预估利润 ${item.get('estimated_profit', 0):.2f}，TACOS {((item.get('tacos') or 0) * 100):.1f}%。",
                "action": "利润健康的 SKU 优先加精准词预算；利润偏低的 SKU 先控 broad/auto 花费。",
                "watch_metric": "未来 7 天 TACOS、CVR、自然单占比。",
            }
            for item in sku_rows[:8]
        ],
        "ad_actions": [
            {
                "campaign_or_term": item.get("search_term", ""),
                "action": item.get("action", "观察"),
                "evidence": item.get("reason", ""),
                "exact_change": "按规则建议执行，幅度先控制在 15%-25%。",
                "watch_metric": "3-7 天内 ACOS、订单数、花费变化。",
            }
            for item in ad_actions[:12]
        ],
        "listing_actions": [
            {
                "sku_or_asin": item.get("sku") or item.get("asin") or "",
                "problem": "；".join(item.get("issues", [])[:3]),
                "action": "先修复影响转化的标题、主图、五点和规格说明。",
                "image_or_copy_direction": "补充尺寸、适配型号、使用场景和多件装数量对比。",
            }
            for item in listing_audits[:8]
        ],
        "budget_actions": [],
        "data_gaps": [error],
        "next_7_days_plan": {
            "day_1": "先处理 P0 广告浪费词和明显缺失的成本/Listings 数据。",
            "day_2_to_3": "把低 ACOS 有订单的词拆 exact，小幅加预算；高花费无单词做否定或降价。",
            "day_4_to_7": "复盘调整后的 ACOS、TACOS、CVR，决定继续放量或止损。",
            "success_criteria": "TACOS 下降或销售不降的情况下广告花费下降，重点 SKU 利润率改善。",
            "stop_loss_criteria": "降价/加预算后 7 天内订单无改善且花费继续扩大。",
        },
        "do_not_do": ["不要在缺少成本表时大规模加预算；不要一次性改太多 Listing 元素导致无法判断效果。"],
    }


def latest_operations_ai_report(db: Session) -> OperationsAiReport | None:
    return db.execute(select(OperationsAiReport).order_by(desc(OperationsAiReport.created_at)).limit(1)).scalar_one_or_none()


def save_operations_ai_report(db: Session, data: dict[str, Any], raw: str = "", error: str | None = None) -> OperationsAiReport:
    report = OperationsAiReport(
        status="failed" if error else "success",
        executive_summary_json=_json(data.get("executive_summary") or []),
        urgent_actions_json=_json(data.get("urgent_actions") or []),
        sku_actions_json=_json(data.get("sku_actions") or []),
        ad_actions_json=_json(data.get("ad_actions") or []),
        listing_actions_json=_json(data.get("listing_actions") or []),
        budget_actions_json=_json(data.get("budget_actions") or []),
        data_gaps_json=_json(data.get("data_gaps") or []),
        next_7_days_plan_json=_json(data.get("next_7_days_plan") or {}),
        do_not_do_json=_json(data.get("do_not_do") or []),
        raw_ai_response=raw,
        error_message=error,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def generate_operations_ai_report(db: Session) -> OperationsAiReport:
    settings = get_settings()
    context = build_operations_ai_context(db)
    if not settings.openai_api_key:
        data = _fallback_report("未配置 OPENAI_API_KEY，因此这次使用本地规则兜底。", context)
        return save_operations_ai_report(db, data, raw="", error="未配置 OPENAI_API_KEY")

    prompt = OPERATIONS_USER_PROMPT.format(context_json=json.dumps(context, ensure_ascii=False, indent=2, default=str))
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": OPERATIONS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
        )
        raw = response.choices[0].message.content or ""
        data = _safe_json_loads(raw)
        return save_operations_ai_report(db, data, raw=raw)
    except Exception as exc:
        error = f"AI 运营分析失败：{exc}"
        data = _fallback_report(error, context)
        return save_operations_ai_report(db, data, raw=str(exc), error=error)


def report_to_view(report: OperationsAiReport | None) -> dict[str, Any] | None:
    if not report:
        return None

    def load(value: str | None, default: Any):
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    return {
        "id": report.id,
        "status": report.status,
        "created_at": report.created_at,
        "error_message": report.error_message,
        "executive_summary": load(report.executive_summary_json, []),
        "urgent_actions": load(report.urgent_actions_json, []),
        "sku_actions": load(report.sku_actions_json, []),
        "ad_actions": load(report.ad_actions_json, []),
        "listing_actions": load(report.listing_actions_json, []),
        "budget_actions": load(report.budget_actions_json, []),
        "data_gaps": load(report.data_gaps_json, []),
        "next_7_days_plan": load(report.next_7_days_plan_json, {}),
        "do_not_do": load(report.do_not_do_json, []),
    }
