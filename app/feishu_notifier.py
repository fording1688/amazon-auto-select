from __future__ import annotations

import json
from typing import Iterable

import requests

from app.config import get_settings


def _text_from_report(item: dict) -> str:
    reasons = item.get("reasons") or []
    bundle = item.get("bundle_strategy") or {}
    pricing = item.get("pricing_suggestion") or {}
    return "\n".join(
        [
            f"产品名称：{item.get('title')}",
            f"ASIN：{item.get('asin')}",
            f"关键词：{item.get('keyword')}",
            f"当前价格：${item.get('price')}",
            f"评论数：{item.get('review_count')}，评分：{item.get('rating')}",
            f"机会分数：{item.get('opportunity_score')}，推荐决策：{item.get('decision')}",
            f"推荐理由：{'；'.join(reasons[:3])}",
            f"批量包建议：{bundle.get('recommended_packs', [])} - {bundle.get('reason', '')}",
            f"建议售价：{json.dumps(pricing, ensure_ascii=False)}",
            f"下一步操作：{item.get('next_action')}",
        ]
    )


def send_top_products(items: Iterable[dict]) -> bool:
    settings = get_settings()
    reports = list(items)
    if not settings.feishu_webhook_url:
        return False
    lines = ["亚马逊自动测款分析 Top 5", ""]
    for index, item in enumerate(reports, start=1):
        lines.append(f"#{index}")
        lines.append(_text_from_report(item))
        lines.append("")
    payload = {"msg_type": "text", "content": {"text": "\n".join(lines)}}
    response = requests.post(settings.feishu_webhook_url, json=payload, timeout=10)
    response.raise_for_status()
    return True
