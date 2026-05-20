from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now() -> datetime:
    return datetime.utcnow()


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    priority: Mapped[str] = mapped_column(String(20), default="中")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="keyword", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("asin", "keyword_id", name="uq_product_asin_keyword"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asin: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float)
    rating: Mapped[Optional[float]] = mapped_column(Float)
    review_count: Mapped[Optional[int]] = mapped_column(Integer)
    brand: Mapped[Optional[str]] = mapped_column(String(120))
    seller: Mapped[Optional[str]] = mapped_column(String(120))
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    product_url: Mapped[Optional[str]] = mapped_column(Text)
    availability: Mapped[Optional[str]] = mapped_column(String(120))
    coupon: Mapped[Optional[str]] = mapped_column(String(120))
    variation_count: Mapped[Optional[int]] = mapped_column(Integer)
    package_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    bsr: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    keyword: Mapped[Keyword] = relationship("Keyword", back_populates="products")
    reports: Mapped[List["AnalysisReport"]] = relationship("AnalysisReport", back_populates="product", cascade="all, delete-orphan")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    opportunity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    reasons_json: Mapped[Optional[str]] = mapped_column(Text)
    risks_json: Mapped[Optional[str]] = mapped_column(Text)
    bundle_strategy_json: Mapped[Optional[str]] = mapped_column(Text)
    pricing_suggestion_json: Mapped[Optional[str]] = mapped_column(Text)
    listing_suggestion_json: Mapped[Optional[str]] = mapped_column(Text)
    image_selling_points_json: Mapped[Optional[str]] = mapped_column(Text)
    ad_keywords_json: Mapped[Optional[str]] = mapped_column(Text)
    negative_keywords_json: Mapped[Optional[str]] = mapped_column(Text)
    fbm_test_plan_json: Mapped[Optional[str]] = mapped_column(Text)
    next_action: Mapped[Optional[str]] = mapped_column(Text)
    raw_ai_response: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)

    product: Mapped[Product] = relationship("Product", back_populates="reports")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_keywords: Mapped[int] = mapped_column(Integer, default=0)
    total_products: Mapped[int] = mapped_column(Integer, default=0)
    total_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class KeywordResearchRun(Base):
    __tablename__ = "keyword_research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seed_keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="success", index=True)
    expanded_keywords_json: Mapped[Optional[str]] = mapped_column(Text)
    product_terms_json: Mapped[Optional[str]] = mapped_column(Text)
    modifier_terms_json: Mapped[Optional[str]] = mapped_column(Text)
    ad_keywords_json: Mapped[Optional[str]] = mapped_column(Text)
    negative_keywords_json: Mapped[Optional[str]] = mapped_column(Text)
    raw_titles_json: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="success", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class OperationsAiReport(Base):
    __tablename__ = "operations_ai_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="success", index=True)
    executive_summary_json: Mapped[Optional[str]] = mapped_column(Text)
    urgent_actions_json: Mapped[Optional[str]] = mapped_column(Text)
    sku_actions_json: Mapped[Optional[str]] = mapped_column(Text)
    ad_actions_json: Mapped[Optional[str]] = mapped_column(Text)
    listing_actions_json: Mapped[Optional[str]] = mapped_column(Text)
    budget_actions_json: Mapped[Optional[str]] = mapped_column(Text)
    data_gaps_json: Mapped[Optional[str]] = mapped_column(Text)
    next_7_days_plan_json: Mapped[Optional[str]] = mapped_column(Text)
    do_not_do_json: Mapped[Optional[str]] = mapped_column(Text)
    raw_ai_response: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class AdRecommendation(Base):
    __tablename__ = "ad_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    ad_group_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    search_term: Mapped[Optional[str]] = mapped_column(Text, index=True)
    targeting: Mapped[Optional[str]] = mapped_column(Text)
    match_type: Mapped[Optional[str]] = mapped_column(String(80))
    recommendation_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    clicks: Mapped[Optional[float]] = mapped_column(Float)
    spend: Mapped[Optional[float]] = mapped_column(Float)
    sales: Mapped[Optional[float]] = mapped_column(Float)
    orders: Mapped[Optional[float]] = mapped_column(Float)
    acos: Mapped[Optional[float]] = mapped_column(Float)
    suggested_bid: Mapped[Optional[float]] = mapped_column(Float)
    suggested_budget: Mapped[Optional[float]] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(30), default="low", index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    execution_plan_json: Mapped[Optional[str]] = mapped_column(Text)
    api_response_json: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class BusinessMetric(Base):
    __tablename__ = "business_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    title: Mapped[Optional[str]] = mapped_column(Text)
    sessions: Mapped[Optional[float]] = mapped_column(Float)
    page_views: Mapped[Optional[float]] = mapped_column(Float)
    units_ordered: Mapped[Optional[float]] = mapped_column(Float)
    ordered_sales: Mapped[Optional[float]] = mapped_column(Float)
    conversion_rate: Mapped[Optional[float]] = mapped_column(Float)
    buy_box_percentage: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class SearchTermMetric(Base):
    __tablename__ = "search_term_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    campaign_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    ad_group_name: Mapped[Optional[str]] = mapped_column(String(255))
    targeting: Mapped[Optional[str]] = mapped_column(Text)
    search_term: Mapped[Optional[str]] = mapped_column(Text, index=True)
    impressions: Mapped[Optional[float]] = mapped_column(Float)
    clicks: Mapped[Optional[float]] = mapped_column(Float)
    spend: Mapped[Optional[float]] = mapped_column(Float)
    sales: Mapped[Optional[float]] = mapped_column(Float)
    orders: Mapped[Optional[float]] = mapped_column(Float)
    acos: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class AdvertisedProductMetric(Base):
    __tablename__ = "advertised_product_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    campaign_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    impressions: Mapped[Optional[float]] = mapped_column(Float)
    clicks: Mapped[Optional[float]] = mapped_column(Float)
    spend: Mapped[Optional[float]] = mapped_column(Float)
    sales: Mapped[Optional[float]] = mapped_column(Float)
    orders: Mapped[Optional[float]] = mapped_column(Float)
    acos: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    campaign_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    campaign_status: Mapped[Optional[str]] = mapped_column(String(60), index=True)
    impressions: Mapped[Optional[float]] = mapped_column(Float)
    clicks: Mapped[Optional[float]] = mapped_column(Float)
    spend: Mapped[Optional[float]] = mapped_column(Float)
    sales: Mapped[Optional[float]] = mapped_column(Float)
    orders: Mapped[Optional[float]] = mapped_column(Float)
    acos: Mapped[Optional[float]] = mapped_column(Float)
    budget: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class TargetingMetric(Base):
    __tablename__ = "targeting_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    campaign_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    ad_group_name: Mapped[Optional[str]] = mapped_column(String(255))
    targeting: Mapped[Optional[str]] = mapped_column(Text, index=True)
    match_type: Mapped[Optional[str]] = mapped_column(String(80))
    status: Mapped[Optional[str]] = mapped_column(String(60), index=True)
    bid: Mapped[Optional[float]] = mapped_column(Float)
    impressions: Mapped[Optional[float]] = mapped_column(Float)
    clicks: Mapped[Optional[float]] = mapped_column(Float)
    spend: Mapped[Optional[float]] = mapped_column(Float)
    sales: Mapped[Optional[float]] = mapped_column(Float)
    orders: Mapped[Optional[float]] = mapped_column(Float)
    acos: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class BulkOperationItem(Base):
    __tablename__ = "bulk_operation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    record_type: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    operation: Mapped[Optional[str]] = mapped_column(String(80))
    campaign_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    campaign_status: Mapped[Optional[str]] = mapped_column(String(60), index=True)
    ad_group_name: Mapped[Optional[str]] = mapped_column(String(255))
    ad_group_id: Mapped[Optional[str]] = mapped_column(String(120))
    entity_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    entity_status: Mapped[Optional[str]] = mapped_column(String(60), index=True)
    keyword_text: Mapped[Optional[str]] = mapped_column(Text, index=True)
    match_type: Mapped[Optional[str]] = mapped_column(String(80))
    targeting_expression: Mapped[Optional[str]] = mapped_column(Text, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    bid: Mapped[Optional[float]] = mapped_column(Float)
    budget: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    fnsku: Mapped[Optional[str]] = mapped_column(String(80))
    product_name: Mapped[Optional[str]] = mapped_column(Text)
    available: Mapped[Optional[float]] = mapped_column(Float)
    inbound: Mapped[Optional[float]] = mapped_column(Float)
    reserved: Mapped[Optional[float]] = mapped_column(Float)
    days_of_supply: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class CostItem(Base):
    __tablename__ = "cost_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    product_name: Mapped[Optional[str]] = mapped_column(Text)
    purchase_cost: Mapped[Optional[float]] = mapped_column(Float)
    first_leg_shipping: Mapped[Optional[float]] = mapped_column(Float)
    packaging_cost: Mapped[Optional[float]] = mapped_column(Float)
    fba_fee: Mapped[Optional[float]] = mapped_column(Float)
    referral_fee_rate: Mapped[Optional[float]] = mapped_column(Float)
    other_cost: Mapped[Optional[float]] = mapped_column(Float)
    target_margin: Mapped[Optional[float]] = mapped_column(Float)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class ListingItem(Base):
    __tablename__ = "listing_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    title: Mapped[Optional[str]] = mapped_column(Text)
    bullet_1: Mapped[Optional[str]] = mapped_column(Text)
    bullet_2: Mapped[Optional[str]] = mapped_column(Text)
    bullet_3: Mapped[Optional[str]] = mapped_column(Text)
    bullet_4: Mapped[Optional[str]] = mapped_column(Text)
    bullet_5: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Optional[float]] = mapped_column(Float)
    coupon: Mapped[Optional[str]] = mapped_column(String(120))
    main_image_url: Mapped[Optional[str]] = mapped_column(Text)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
