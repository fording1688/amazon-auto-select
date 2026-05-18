from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KeywordCreate(BaseModel):
    keyword: str
    category: str = ""
    priority: str = "中"
    status: str = "active"


class KeywordRead(KeywordCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductRead(BaseModel):
    id: int
    asin: str
    title: str
    price: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    brand: Optional[str]
    image_url: Optional[str]

    class Config:
        from_attributes = True
