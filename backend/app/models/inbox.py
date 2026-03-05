import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

from app.core.database import Base


class Inbox(Base):
    __tablename__ = "inboxes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(SAEnum("system", "agent", "custom", name="inbox_type"), default="custom")
    icon: Mapped[str] = mapped_column(String(50), default="fa-inbox")
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    owner_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    filter_tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    filter_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
