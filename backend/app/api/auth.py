from __future__ import annotations
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token, get_current_user
from app.models.user import User
from pydantic import BaseModel
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, UserCreate, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple in-memory rate limiting for login
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX = 10  # max attempts
_RATE_LIMIT_WINDOW = 900  # 15 minutes


def _check_rate_limit(key: str):
    now = time.time()
    attempts = _login_attempts[key]
    # Remove expired attempts
    _login_attempts[key] = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(_login_attempts[key]) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente em 15 minutos.")
    _login_attempts[key].append(now)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("super_admin", "admin", "supervisor", "agent"):
        raise HTTPException(status_code=403, detail="Acesso restrito")
    result = await db.execute(select(User).order_by(User.name))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)):
    if current.role != "super_admin":
        raise HTTPException(status_code=403, detail="Apenas o super admin pode criar usuários")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        specialty=body.specialty,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


class ProfileUpdate(BaseModel):
    name: str | None = None
    email_signature: str | None = None


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(body: ProfileUpdate, db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)):
    """Agente atualiza próprio perfil (nome, assinatura)."""
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current, field, value)
    await db.commit()
    await db.refresh(current)
    return UserResponse.model_validate(current)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, body: UserUpdate, db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)):
    if current.role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Apenas admins podem editar usuários")
    # Apenas super_admin pode mudar role
    if body.role is not None and current.role != "super_admin":
        raise HTTPException(status_code=403, detail="Apenas o super admin pode alterar cargos")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)):
    if not verify_password(body.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 6 caracteres")
    current.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Senha alterada com sucesso"}


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, body: ResetPasswordRequest, db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)):
    if current.role != "super_admin":
        raise HTTPException(status_code=403, detail="Apenas o super admin pode resetar senhas")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 6 caracteres")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": f"Senha de {user.name} resetada com sucesso"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)):
    if current.role != "super_admin":
        raise HTTPException(status_code=403, detail="Apenas o super admin pode remover usuários")

    if user_id == current.id:
        raise HTTPException(status_code=400, detail="Você não pode remover a si mesmo")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    await db.delete(user)
    await db.commit()
