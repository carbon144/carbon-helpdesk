"""Rewards/prizes system — admin-configurable."""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rewards", tags=["rewards"])

# ── Pydantic schemas ──

class RewardCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "fa-gift"
    color: str = "#a855f7"
    points_required: int = 100
    category: str = "geral"  # geral, mensal, semanal
    is_active: bool = True
    max_claims: int = 0  # 0 = unlimited

class RewardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    points_required: Optional[int] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    max_claims: Optional[int] = None


# ── CRUD endpoints (admin only) ──

@router.get("/list")
async def list_rewards(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all rewards."""
    result = await db.execute(text(
        "SELECT * FROM rewards ORDER BY points_required ASC"
    ))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.post("/create")
async def create_reward(
    data: RewardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a reward (admin only)."""
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins podem criar premiações")

    reward_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO rewards (id, name, description, icon, color, points_required, category, is_active, max_claims, created_by)
        VALUES (:id, :name, :description, :icon, :color, :points_required, :category, :is_active, :max_claims, :created_by)
    """), {
        "id": reward_id, "name": data.name, "description": data.description,
        "icon": data.icon, "color": data.color, "points_required": data.points_required,
        "category": data.category, "is_active": data.is_active,
        "max_claims": data.max_claims, "created_by": user.id,
    })
    await db.commit()
    return {"id": reward_id, "message": "Premiação criada"}


@router.put("/{reward_id}")
async def update_reward(
    reward_id: str,
    data: RewardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update reward (admin only)."""
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins")

    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nenhum campo para atualizar")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = reward_id
    await db.execute(text(f"UPDATE rewards SET {set_clause} WHERE id = :id"), updates)
    await db.commit()
    return {"message": "Atualizado"}


@router.delete("/{reward_id}")
async def delete_reward(
    reward_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete reward (admin only)."""
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins")

    await db.execute(text("DELETE FROM rewards WHERE id = :id"), {"id": reward_id})
    await db.commit()
    return {"message": "Removido"}


# ── Agent claims ──

@router.post("/{reward_id}/claim")
async def claim_reward(
    reward_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agent claims a reward with their points."""
    # Get reward
    result = await db.execute(text("SELECT * FROM rewards WHERE id = :id"), {"id": reward_id})
    reward = result.mappings().first()
    if not reward:
        raise HTTPException(404, "Premiação não encontrada")
    if not reward["is_active"]:
        raise HTTPException(400, "Premiação inativa")

    # Check max claims
    if reward["max_claims"] > 0:
        claims_count = await db.execute(text(
            "SELECT COUNT(*) FROM reward_claims WHERE reward_id = :rid"
        ), {"rid": reward_id})
        if claims_count.scalar() >= reward["max_claims"]:
            raise HTTPException(400, "Limite de resgates atingido")

    # Check agent score (points)
    from app.api.gamification import _calc_agent_score
    score = await _calc_agent_score(db, user.id)
    if score < reward["points_required"]:
        raise HTTPException(400, f"Pontos insuficientes ({score}/{reward['points_required']})")

    claim_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO reward_claims (id, reward_id, agent_id, agent_name, points_spent, status)
        VALUES (:id, :reward_id, :agent_id, :agent_name, :points_spent, 'pending')
    """), {
        "id": claim_id, "reward_id": reward_id, "agent_id": user.id,
        "agent_name": user.name, "points_spent": reward["points_required"],
    })
    await db.commit()
    return {"id": claim_id, "message": "Resgate solicitado! Aguardando aprovação do admin."}


@router.get("/claims")
async def list_claims(
    status: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List reward claims. Admins see all, agents see their own."""
    if user.role in ("admin", "supervisor"):
        q = "SELECT rc.*, r.name as reward_name, r.icon, r.color FROM reward_claims rc JOIN rewards r ON r.id = rc.reward_id"
        params = {}
        if status:
            q += " WHERE rc.status = :status"
            params["status"] = status
        q += " ORDER BY rc.created_at DESC"
    else:
        q = "SELECT rc.*, r.name as reward_name, r.icon, r.color FROM reward_claims rc JOIN rewards r ON r.id = rc.reward_id WHERE rc.agent_id = :agent_id"
        params = {"agent_id": user.id}
        if status:
            q += " AND rc.status = :status"
            params["status"] = status
        q += " ORDER BY rc.created_at DESC"

    result = await db.execute(text(q), params)
    return [dict(r) for r in result.mappings().all()]


@router.put("/claims/{claim_id}/approve")
async def approve_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin approves a claim."""
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins")
    await db.execute(text(
        "UPDATE reward_claims SET status = 'approved', approved_by = :by, approved_at = NOW() WHERE id = :id"
    ), {"id": claim_id, "by": user.id})
    await db.commit()
    return {"message": "Aprovado"}


@router.put("/claims/{claim_id}/reject")
async def reject_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin rejects a claim."""
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(403, "Apenas admins")
    await db.execute(text(
        "UPDATE reward_claims SET status = 'rejected', approved_by = :by, approved_at = NOW() WHERE id = :id"
    ), {"id": claim_id, "by": user.id})
    await db.commit()
    return {"message": "Rejeitado"}
