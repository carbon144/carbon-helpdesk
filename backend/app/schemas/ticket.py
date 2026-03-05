from __future__ import annotations
from pydantic import BaseModel, EmailStr
from datetime import datetime


class TicketCreate(BaseModel):
    subject: str
    customer_email: EmailStr
    customer_name: str
    body: str
    priority: str = "medium"
    tags: list[str] | None = None


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    inbox_id: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    supplier_notes: str | None = None
    tracking_code: str | None = None
    tracking_status: str | None = None


class TicketBulkAssign(BaseModel):
    ticket_ids: list[str]
    assigned_to: str | None = None
    inbox_id: str | None = None


class TicketBulkUpdate(BaseModel):
    ticket_ids: list[str]
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    inbox_id: str | None = None


class MessageCreate(BaseModel):
    body_text: str
    body_html: str | None = None
    type: str = "outbound"  # outbound or internal_note
    cc: list[str] | None = None
    bcc: list[str] | None = None
    scheduled_at: datetime | None = None
    attachments: list[dict] | None = None  # [{name, drive_url, drive_file_id, size, mime_type}]


class MessageResponse(BaseModel):
    id: str
    ticket_id: str
    type: str
    sender_email: str | None = None
    sender_name: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    ai_suggestion: str | None = None
    cc: str | None = None
    bcc: str | None = None
    attachments: dict | list | None = None
    scheduled_at: datetime | None = None
    is_scheduled: bool = False
    original_ticket_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str
    cpf: str | None = None
    phone: str | None = None
    total_tickets: int
    is_repeat: bool
    risk_score: float
    is_blacklisted: bool = False
    blacklist_reason: str | None = None
    chargeback_count: int = 0
    resend_count: int = 0
    alternate_emails: list[str] | None = None
    merged_into_id: str | None = None

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: str
    number: int
    subject: str
    status: str
    priority: str
    category: str | None = None
    customer: CustomerResponse | None = None
    assigned_to: str | None = None
    agent_name: str | None = None
    inbox_id: str | None = None
    sla_deadline: datetime | None = None
    sla_response_deadline: datetime | None = None
    sla_breached: bool
    sentiment: str | None = None
    ai_category: str | None = None
    ai_confidence: float | None = None
    ai_summary: str | None = None
    legal_risk: bool
    is_locked: bool
    tags: list[str] | None = None
    source: str | None = None
    slack_channel_id: str | None = None
    slack_thread_ts: str | None = None
    meta_conversation_id: str | None = None
    meta_platform: str | None = None
    ai_auto_mode: bool = True
    ai_paused_by: str | None = None
    ai_paused_at: datetime | None = None
    protocol: str | None = None
    protocol_sent: bool = False
    internal_notes: str | None = None
    merged_into_id: str | None = None
    supplier_notes: str | None = None
    tracking_code: str | None = None
    tracking_status: str | None = None
    escalated_at: datetime | None = None
    escalation_reason: str | None = None
    received_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    first_response_at: datetime | None = None
    last_agent_response_at: datetime | None = None
    customer_name: str | None = None
    messages: list[MessageResponse] | None = None
    is_unread: bool = False

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int
    page: int
    per_page: int
