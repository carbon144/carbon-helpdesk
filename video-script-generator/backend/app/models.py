import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.database import Base


class VideoScript(Base):
    """Roteiro de video gerado por AI."""
    __tablename__ = "video_scripts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Brief
    title: Mapped[str] = mapped_column(String(300))
    product_name: Mapped[str] = mapped_column(String(200))
    product_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    additional_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Script type: teleprompter, ugc, founder_ad, meta_ad
    script_type: Mapped[str] = mapped_column(String(50), index=True)

    # Duration target in seconds
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Generated content
    script_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    hook_options: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    cta_options: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    thumbnail_suggestions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Customer insights used (from helpdesk)
    customer_insights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source_ticket_ids: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Meta Ads tracking
    meta_ad_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    meta_campaign_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meta_adset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Performance metrics (synced from Meta)
    impressions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spend: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    conversions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_watch_25: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_watch_50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_watch_75: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_watch_100: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hook_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hold_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    performance_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status: draft, generating, completed, error, archived
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rating (manual user feedback)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rating_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CustomerInsight(Base):
    """Insights agregados dos tickets do helpdesk."""
    __tablename__ = "customer_insights"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Insight type: faq, pain_point, objection, praise, feature_request
    insight_type: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[str] = mapped_column(Text)
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    example_messages: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    source_ticket_ids: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    product_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
