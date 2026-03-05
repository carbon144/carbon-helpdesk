import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    number: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("customers.id"), index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    handler: Mapped[str] = mapped_column(String(10), default="chatbot")
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_attempts: Mapped[int] = mapped_column(Integer, default=0)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", backref="conversations")
    assigned_agent = relationship("User", foreign_keys=[assigned_to])
    chat_messages = relationship("ChatMessage", back_populates="conversation", lazy="selectin", order_by="ChatMessage.created_at")
