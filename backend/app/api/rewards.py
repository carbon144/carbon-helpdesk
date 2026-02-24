"""Rewards/prizes system — admin-configurable."""
import logging
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.reward import Reward, RewardClaim

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
    result = await db.execute(select(Reward).order_by(Reward.points_required.asc()))
    rewards = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "description": r.description,
            "icon": r.icon, "color": r.color, "points_required": r.points_required,
            "category": r.category, "is_active": r.is_active,
            "max_claims": r.max_claims, "created_by": r.created_by,
            "created_at": r.created_at,
        }
        for r in rewards
    ]


@router.post("/create")
async def create_reward(
    data: RewardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a reward (admin only)."""
    if user.role not in ("admin", "supervisor", "super_admin"):
        raise HTTPException(403, "Apenas admins podem criar premiações")

    reward = Reward(
        name=data.name, description=data.description, icon=data.icon,
        color=data.color, points_required=data.points_required,
        category=data.category, is_active=data.is_active,
        max_claims=data.max_claims, created_by=user.id,
    )
    db.add(reward)
    await db.commit()
    await db.refresh(reward)
    return {"id": reward.id, "message": "Premiação criada"}


@router.put("/{reward_id}")
async def update_reward(
    reward_id: str,
    data: RewardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update reward (admin only)."""
    if user.role not in ("admin", "supervisor", "super_admin"):
        raise HTTPException(403, "Apenas admins")

    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(404, "Premiação não encontrada")

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "Nenhum campo para atualizar")

    for field, value in updates.items():
        setattr(reward, field, value)

    await db.commit()
    return {"message": "Atualizado"}


@router.delete("/{reward_id}")
async def delete_reward(
    reward_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete reward (admin only)."""
    if user.role not in ("admin", "supervisor", "super_admin"):
        raise HTTPException(403, "Apenas admins")

    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(404, "Premiação não encontrada")

    await db.delete(reward)
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
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(404, "Premiação não encontrada")
    if not reward.is_active:
        raise HTTPException(400, "Premiação inativa")

    # Check max claims
    if reward.max_claims > 0:
        claims_count = await db.execute(
            select(func.count(RewardClaim.id)).where(RewardClaim.reward_id == reward_id)
        )
        if claims_count.scalar() >= reward.max_claims:
            raise HTTPException(400, "Limite de resgates atingido")

    # Check agent score (points)
    from app.api.gamification import _calc_agent_score
    score = await _calc_agent_score(db, user.id)
    if score < reward.points_required:
        raise HTTPException(400, f"Pontos insuficientes ({score}/{reward.points_required})")

    claim = RewardClaim(
        reward_id=reward_id, agent_id=user.id,
        agent_name=user.name, points_spent=reward.points_required,
    )
    db.add(claim)
    await db.commit()
    return {"id": claim.id, "message": "Resgate solicitado! Aguardando aprovação do admin."}


@router.get("/claims")
async def list_claims(
    status: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List reward claims. Admins see all, agents see their own."""
    query = select(RewardClaim)
    if user.role not in ("admin", "supervisor", "super_admin"):
        query = query.where(RewardClaim.agent_id == user.id)
    if status:
        query = query.where(RewardClaim.status == status)
    query = query.order_by(RewardClaim.created_at.desc())

    result = await db.execute(query)
    claims = result.scalars().all()

    # Fetch reward names for display
    reward_ids = list({c.reward_id for c in claims})
    rewards_map = {}
    if reward_ids:
        rewards_result = await db.execute(select(Reward).where(Reward.id.in_(reward_ids)))
        for r in rewards_result.scalars().all():
            rewards_map[r.id] = r

    return [
        {
            "id": c.id, "reward_id": c.reward_id, "agent_id": c.agent_id,
            "agent_name": c.agent_name, "points_spent": c.points_spent,
            "status": c.status, "approved_by": c.approved_by,
            "approved_at": c.approved_at, "created_at": c.created_at,
            "reward_name": rewards_map.get(c.reward_id, Reward()).name if c.reward_id in rewards_map else "",
            "icon": rewards_map[c.reward_id].icon if c.reward_id in rewards_map else "fa-gift",
            "color": rewards_map[c.reward_id].color if c.reward_id in rewards_map else "#a855f7",
        }
        for c in claims
    ]


@router.put("/claims/{claim_id}/approve")
async def approve_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin approves a claim."""
    if user.role not in ("admin", "supervisor", "super_admin"):
        raise HTTPException(403, "Apenas admins")

    result = await db.execute(select(RewardClaim).where(RewardClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Solicitação não encontrada")

    claim.status = "approved"
    claim.approved_by = user.id
    claim.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Aprovado"}


@router.put("/claims/{claim_id}/reject")
async def reject_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin rejects a claim."""
    if user.role not in ("admin", "supervisor", "super_admin"):
        raise HTTPException(403, "Apenas admins")

    result = await db.execute(select(RewardClaim).where(RewardClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Solicitação não encontrada")

    claim.status = "rejected"
    claim.approved_by = user.id
    claim.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Rejeitado"}
