import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VoiceCall(Base):
    __tablename__ = "voice_calls"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tickets.id"), nullable=True, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=True, index=True)
    vapi_call_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    caller_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    recording_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ended_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    ticket = relationship("Ticket", backref="voice_calls")
    conversation = relationship("Conversation", backref="voice_calls")
