"""Chatbot flow management API endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.chat import ChatbotFlowResponse, ChatbotFlowCreate
from app.services.chatbot_engine import list_flows, get_flow, create_flow, update_flow, delete_flow

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.get("/flows", response_model=list[ChatbotFlowResponse])
async def api_list_flows(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_flows(db)


@router.post("/flows", response_model=ChatbotFlowResponse)
async def api_create_flow(
    data: ChatbotFlowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_flow(db, data.model_dump())


@router.put("/flows/{flow_id}", response_model=ChatbotFlowResponse)
async def api_update_flow(
    flow_id: str,
    data: ChatbotFlowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    flow = await update_flow(db, flow_id, data.model_dump(exclude_unset=True))
    if not flow:
        raise HTTPException(404, "Flow not found")
    return flow


@router.delete("/flows/{flow_id}")
async def api_delete_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ok = await delete_flow(db, flow_id)
    if not ok:
        raise HTTPException(404, "Flow not found")
    return {"deleted": True}
