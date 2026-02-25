"""Agent performance analysis report model."""
import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AgentReport(Base):
    __tablename__ = "agent_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str] = mapped_column(String(20), default="manual")
    quantitative_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    generated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent = relationship("User", foreign_keys=[agent_id], lazy="selectin")
