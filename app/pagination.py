from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Sequence, TypeVar


T = TypeVar("T")


@dataclass
class Pagination:
    page: int
    per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool
    prev_page: int
    next_page: int
    base_url: str
    separator: str


def build_pagination(total: int, page: int, per_page: int, base_url: str) -> Pagination:
    total_pages = max(ceil(total / per_page), 1)
    page = min(max(page, 1), total_pages)
    return Pagination(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_page=page - 1,
        next_page=page + 1,
        base_url=base_url,
        separator="&" if "?" in base_url else "?",
    )


def paginate_list(items: Sequence[T], page: int, per_page: int, base_url: str) -> tuple[list[T], Pagination]:
    pagination = build_pagination(len(items), page, per_page, base_url)
    start = (pagination.page - 1) * pagination.per_page
    end = start + pagination.per_page
    return list(items[start:end]), pagination
