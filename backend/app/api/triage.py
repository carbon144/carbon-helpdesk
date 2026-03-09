"""Triage rules API — Victor configures, system executes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.triage_rule import TriageRule
from app.services.triage_service import get_online_agents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/triage", tags=["triage"])


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(TriageRule).order_by(TriageRule.priority.desc()))
    rules = result.scalars().all()
    return [_rule_to_dict(r) for r in rules]


@router.post("/rules")
async def create_rule(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas lider/admin pode criar regras")
    data = await request.json()
    rule = TriageRule(
        created_by=user.id,
        **{k: v for k, v in data.items() if k != "id" and hasattr(TriageRule, k) and k not in ("created_by", "created_at", "updated_at")}
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas lider/admin pode editar regras")
    result = await db.execute(select(TriageRule).where(TriageRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Regra nao encontrada")
    data = await request.json()
    for k, v in data.items():
        if hasattr(rule, k) and k not in ("id", "created_by", "created_at"):
            setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas lider/admin pode deletar regras")
    result = await db.execute(select(TriageRule).where(TriageRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404)
    await db.delete(rule)
    await db.commit()
    return {"ok": True}


@router.get("/online-agents")
async def list_online_agents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    agents = await get_online_agents(db)
    return [{"id": a.id, "name": a.name, "role": a.role, "specialty": a.specialty, "status": "online"} for a in agents]


def _rule_to_dict(r: TriageRule) -> dict:
    return {
        "id": r.id, "name": r.name, "is_active": r.is_active, "priority": r.priority,
        "category": r.category, "assign_to": r.assign_to, "set_priority": r.set_priority,
        "auto_reply": r.auto_reply,
        "agent_name": r.agent.name if r.agent else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
