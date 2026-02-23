from pydantic import BaseModel
from datetime import datetime


class KBArticleCreate(BaseModel):
    title: str
    content: str
    category: str
    tags: list[str] | None = None


class KBArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_published: bool | None = None


class KBArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str
    tags: list[str] | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MacroAction(BaseModel):
    type: str  # set_status, set_priority, add_tag, set_category, assign_to
    value: str


class MacroCreate(BaseModel):
    name: str
    content: str
    category: str | None = None
    actions: list[MacroAction] | None = None


class MacroUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    category: str | None = None
    is_active: bool | None = None
    actions: list[MacroAction] | None = None


class MacroResponse(BaseModel):
    id: str
    name: str
    content: str
    category: str | None = None
    is_active: bool
    actions: list[dict] | None = None

    class Config:
        from_attributes = True
