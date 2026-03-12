"""AI Agent model — specialized agents organized by sector for autonomous ticket response."""
import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

from app.core.database import Base


class AIAgent(Base):
    __tablename__ = "ai_agents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))  # e.g. "Isabela-IA"
    human_name: Mapped[str] = mapped_column(String(255))  # e.g. "Agente IA Atendimento"
    role: Mapped[str] = mapped_column(String(100))  # e.g. "Agente Nivel 1"
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1=agente, 2=coord, 3=supervisor

    # Sector & specialty
    sector: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # atendimento, logistica, garantia, retencao, supervisao
    specialty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "rastreio_status", "reenvio", etc.
    coordinator_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("ai_agents.id"), nullable=True)
    slack_channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "#ia-operacao", "#ia-logistica", etc.

    # What this agent handles
    categories: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # ["duvida", "meu_pedido"]
    tools_enabled: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # ["shopify", "tracking"]

    # AI behavior
    system_prompt: Mapped[str] = mapped_column(Text)
    few_shot_examples: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # [{input, output}, ...]
    escalation_keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7)

    # Autonomy
    auto_send: Mapped[bool] = mapped_column(Boolean, default=False)  # starts in review mode
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stats
    total_replies: Mapped[int] = mapped_column(Integer, default=0)
    total_approved: Mapped[int] = mapped_column(Integer, default=0)
    total_escalated: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    coordinator = relationship("AIAgent", remote_side=[id], foreign_keys=[coordinator_id], lazy="selectin")
