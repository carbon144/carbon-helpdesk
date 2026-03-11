from __future__ import annotations
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, hash_password, create_access_token, get_current_user
from app.models.user import User
from pydantic import BaseModel
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, UserCreate, UserUpdate

logger = logging.getLogger(__name__)

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
    # Rate limit by email, not IP (nginx proxy shares a single internal IP)
    _check_rate_limit(body.email.lower().strip())

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

    # Proteger super_admin: role só pode ser alterado via banco direto
    if user.role == "super_admin" and body.role is not None and body.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin não pode ser rebaixado pela interface")

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


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordWithTokenRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Envia email com link para redefinir senha."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Sempre retorna sucesso para não revelar se o email existe
    if not user or not user.is_active:
        return {"message": "Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha."}

    # Gera token JWT com expiração de 30 minutos
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    reset_token = jwt.encode(
        {"sub": user.id, "purpose": "password_reset", "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Monta o link de reset usando URL fixa (não confiar no Origin header)
    base_url = "https://helpdesk.brutodeverdade.com.br"
    reset_link = f"{base_url}?reset_token={reset_token}"

    # Envia email via Gmail
    try:
        from app.services.gmail_service import send_email
        email_body = f"""Olá {user.name},

Você solicitou a redefinição de sua senha no Carbon Expert Hub.

Clique no link abaixo para criar uma nova senha:
{reset_link}

Este link expira em 30 minutos.

Se você não solicitou esta redefinição, ignore este e-mail.

— Carbon Expert Hub"""

        send_email(
            to=user.email,
            subject="Redefinir senha — Carbon Expert Hub",
            body_text=email_body,
        )
        logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {user.email}: {e}")

    return {"message": "Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha."}


@router.post("/reset-password-with-token")
async def reset_password_with_token(body: ResetPasswordWithTokenRequest, db: AsyncSession = Depends(get_db)):
    """Redefine a senha usando o token recebido por email."""
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 6 caracteres")

    try:
        payload = jwt.decode(body.token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Link expirado ou inválido. Solicite um novo.")

    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Token inválido")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Senha redefinida com sucesso! Faça login com sua nova senha."}


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
