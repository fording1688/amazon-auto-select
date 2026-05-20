from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.models import AdRecommendation


class AmazonAdsApiClient:
    """Mock-first Amazon Ads client.

    Real API calls are intentionally blocked unless the global feature flag is enabled
    and the recommendation has already been approved by a human.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _ensure_can_execute(self, recommendation: AdRecommendation) -> None:
        if not self.settings.amazon_ads_api_enabled:
            raise RuntimeError("Amazon Ads API 未启用，当前只允许生成执行计划。")
        if recommendation.status != "approved":
            raise RuntimeError("只有人工确认为 approved 的建议才允许执行。")
        if not recommendation.execution_plan_json:
            raise RuntimeError("缺少 execution_plan_json，禁止执行。")

    def create_exact_keyword(self, recommendation: AdRecommendation, **payload: Any) -> dict[str, Any]:
        self._ensure_can_execute(recommendation)
        return {"mock": True, "operation": "create_exact_keyword", "payload": payload}

    def update_keyword_bid(self, recommendation: AdRecommendation, **payload: Any) -> dict[str, Any]:
        self._ensure_can_execute(recommendation)
        return {"mock": True, "operation": "update_keyword_bid", "payload": payload}

    def update_campaign_budget(self, recommendation: AdRecommendation, **payload: Any) -> dict[str, Any]:
        self._ensure_can_execute(recommendation)
        return {"mock": True, "operation": "update_campaign_budget", "payload": payload}

    def add_negative_keyword(self, recommendation: AdRecommendation, **payload: Any) -> dict[str, Any]:
        self._ensure_can_execute(recommendation)
        return {"mock": True, "operation": "add_negative_keyword", "payload": payload}

    def pause_keyword(self, recommendation: AdRecommendation, **payload: Any) -> dict[str, Any]:
        self._ensure_can_execute(recommendation)
        return {"mock": True, "operation": "pause_keyword", "payload": payload}

    def get_campaigns(self) -> list[dict[str, Any]]:
        return []

    def get_ad_groups(self, campaign_id: str | None = None) -> list[dict[str, Any]]:
        return []
