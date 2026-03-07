from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConversationResponse(BaseModel):
    id: str
    number: Optional[int] = None
    customer_id: str
    assigned_to: Optional[str] = None
    channel: str
    status: str
    priority: str
    handler: str = "chatbot"
    ai_enabled: bool = True
    ai_attempts: int = 0
    subject: Optional[str] = None
    tags: Optional[list] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    customer_id: str
    channel: str = "chat"
    subject: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content_type: str
    content: str
    channel_message_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str
    content_type: str = "text"


class ChatbotFlowResponse(BaseModel):
    id: str
    name: str
    trigger_type: str
    trigger_config: Optional[dict] = None
    steps: Optional[list] = None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotFlowCreate(BaseModel):
    name: str
    trigger_type: str
    trigger_config: Optional[dict] = None
    steps: Optional[list] = None
    active: bool = True
