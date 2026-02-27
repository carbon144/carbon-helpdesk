import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

from app.core.database import Base

# Valid statuses (checked in API, not DB enum for flexibility)
VALID_STATUSES = [
    "open", "in_progress", "waiting", "waiting_supplier", "waiting_resend",
    "analyzing", "resolved", "closed", "escalated", "archived", "merged",
]

VALID_PRIORITIES = ["low", "medium", "high", "urgent"]

STATUS_LABELS = {
    "open": "Aberto",
    "in_progress": "Em Andamento",
    "waiting": "Aguardando Cliente",
    "waiting_supplier": "Aguardando Fornecedor",
    "waiting_resend": "Aguardando Reenvio",
    "analyzing": "Em Análise",
    "resolved": "Resolvido",
    "closed": "Fechado",
    "escalated": "Escalado",
    "archived": "Arquivado",
    "merged": "Mesclado",
}


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    number: Mapped[int] = mapped_column(Integer, autoincrement=True, unique=True)
    subject: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("customers.id"), index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True, index=True)
    inbox_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("inboxes.id"), nullable=True)

    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_response_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)

    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legal_risk: Mapped[bool] = mapped_column(Boolean, default=False)

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)

    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Slack integration
    slack_channel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    slack_thread_ts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), default="web", nullable=True)

    # Meta integration (WhatsApp, Instagram, Facebook)
    meta_conversation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    meta_platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ai_auto_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_paused_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    ai_paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Protocol number
    protocol: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, unique=True, index=True)
    protocol_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Internal notes (sticky, separate from messages)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Merge support
    merged_into_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    email_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Supplier communication
    supplier_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Escalation tracking
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_agent_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Tracking / logistics
    tracking_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    csat_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
    agent = relationship("User", foreign_keys=[assigned_to], lazy="selectin")
    messages = relationship("Message", back_populates="ticket", lazy="select", order_by="Message.created_at")
