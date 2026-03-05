from __future__ import annotations
from pydantic import BaseModel


class InboxCreate(BaseModel):
    name: str
    type: str = "custom"
    icon: str = "fa-inbox"
    color: str = "#6366f1"
    filter_tags: list[str] | None = None
    filter_rules: dict | None = None


class InboxUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    filter_tags: list[str] | None = None
    filter_rules: dict | None = None
    is_active: bool | None = None


class InboxResponse(BaseModel):
    id: str
    name: str
    type: str
    icon: str
    color: str
    owner_id: str | None = None
    filter_tags: list[str] | None = None
    sort_order: int
    is_active: bool
    ticket_count: int = 0

    class Config:
        from_attributes = True
