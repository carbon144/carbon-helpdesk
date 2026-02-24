import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tickets.id"), index=True)
    type: Mapped[str] = mapped_column(
        SAEnum("inbound", "outbound", "internal_note", name="message_type"),
    )
    sender_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gmail_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    attachments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ai_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slack_ts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    meta_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meta_platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Email thread tracking
    email_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_references: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # CC/BCC tracking
    cc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bcc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scheduled send
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    ticket = relationship("Ticket", back_populates="messages")
