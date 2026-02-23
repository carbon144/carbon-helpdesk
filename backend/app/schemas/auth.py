from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    avatar_url: str | None = None
    specialty: str | None = None
    max_tickets: int = 20
    email_signature: str | None = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "agent"
    specialty: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    specialty: str | None = None
    max_tickets: int | None = None
    is_active: bool | None = None
    email_signature: str | None = None
