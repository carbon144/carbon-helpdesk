from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token, get_current_user
from app.models.user import User
from pydantic import BaseModel
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, UserCreate, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
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
    if user.role not in ("super_admin", "admin", "supervisor"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores e supervisores")
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
