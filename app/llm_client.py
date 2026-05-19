from __future__ import annotations

from openai import OpenAI

from app.config import get_settings


def get_openai_client() -> OpenAI:
    settings = get_settings()
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    headers = {}
    if settings.openrouter_http_referer:
        headers["HTTP-Referer"] = settings.openrouter_http_referer
    if settings.openrouter_app_name:
        headers["X-Title"] = settings.openrouter_app_name
    if headers:
        kwargs["default_headers"] = headers

    return OpenAI(**kwargs)
