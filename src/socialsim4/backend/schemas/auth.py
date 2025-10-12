from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


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

    @field_validator("password")
    @classmethod
    def _check_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes when encoded as utf-8")
        return value


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def _check_reset_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes when encoded as utf-8")
        return value


class EmailVerification(BaseModel):
    token: str
    verified_at: datetime


class RefreshRequest(BaseModel):
    refresh_token: str


class VerificationRequest(BaseModel):
    token: str
