from __future__ import annotations

import time
from typing import Any

import requests

from app.config import get_settings


class SerpApiError(RuntimeError):
    pass


def resolve_serpapi_key() -> str:
    settings = get_settings()
    return (settings.serpapi_api_key or settings.serpapi_key or "").strip()


class SerpApiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://serpapi.com/search.json", timeout: int = 30):
        self.api_key = (api_key or resolve_serpapi_key()).strip()
        self.base_url = base_url
        self.timeout = timeout

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise SerpApiError("未配置 SERPAPI_API_KEY，无法调用 SerpApi。请在后端 .env 配置后重启服务。")
        safe_params = {
            **params,
            "api_key": self.api_key,
            "output": "json",
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.get(self.base_url, params=safe_params, timeout=self.timeout)
                if response.status_code >= 500 and attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict) and payload.get("error"):
                    raise SerpApiError(str(payload["error"]))
                if not isinstance(payload, dict):
                    raise SerpApiError("SerpApi 返回格式异常。")
                return payload
            except (requests.RequestException, ValueError, SerpApiError) as exc:
                last_error = exc
                if attempt < 2 and not isinstance(exc, SerpApiError):
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break
        raise SerpApiError(str(last_error or "SerpApi 请求失败。"))
