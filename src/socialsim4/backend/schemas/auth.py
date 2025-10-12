from datetime import datetime

from pydantic import BaseModel, EmailStr


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    organization: str | None = None
    email: EmailStr
    username: str
    full_name: str
    phone_number: str
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str


class EmailVerification(BaseModel):
    token: str
    verified_at: datetime


class RefreshRequest(BaseModel):
    refresh_token: str
