import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TicketView(Base):
    __tablename__ = "ticket_views"
    __table_args__ = (
        UniqueConstraint("user_id", "ticket_id", name="uq_ticket_views_user_ticket"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    ticket_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tickets.id"), index=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
