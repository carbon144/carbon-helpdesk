"""Social comment moderation model — tracks AI moderation of Instagram/Facebook comments."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base
from typing import Optional


class SocialComment(Base):
    __tablename__ = "social_comments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Source info
    platform: Mapped[str] = mapped_column(String(20), index=True)  # "instagram" | "facebook"
    comment_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # Meta comment ID
    post_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # Post/media ID
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # If it's a reply to another comment

    # Author
    author_id: Mapped[str] = mapped_column(String(100))  # Meta user ID
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Content
    text: Mapped[str] = mapped_column(Text)
    post_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Caption of the post being commented on

    # AI moderation result
    ai_action: Mapped[str] = mapped_column(String(30), index=True)  # "replied" | "hidden" | "hidden_replied" | "ignored" | "flagged"
    ai_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI's reply text
    ai_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "positive" | "neutral" | "negative" | "offensive"
    ai_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "elogio" | "duvida" | "reclamacao" | "ofensivo" | "spam" | "mencao" | "outro"
    ai_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Status tracking
    reply_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    was_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    manually_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    commented_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    moderated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
