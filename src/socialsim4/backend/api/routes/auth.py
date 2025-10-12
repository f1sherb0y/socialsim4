from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.security import create_access_token, create_refresh_token, hash_password, verify_password
from ...dependencies import get_current_user, get_db_session
from ...models.token import RefreshToken
from ...models.user import User
from ...schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from ...schemas.user import UserCreate, UserPublic


router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> UserPublic:
    if (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if (await session.execute(select(User).where(User.username == payload.username))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    user = User(
        organization=payload.organization,
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPair:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")

    access_token, access_exp = create_access_token(str(user.id))
    refresh_token, refresh_exp = create_refresh_token(str(user.id))

    session.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=refresh_exp,
            created_at=datetime.now(timezone.utc),
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_exp - datetime.now(timezone.utc)).total_seconds()),
    )


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user


@router.post("/token/refresh", response_model=TokenPair)
async def refresh_token(payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPair:
    try:
        decoded = jwt.decode(
            payload.refresh_token,
            key=settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    subject = decoded.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    token_q = await session.execute(
        select(RefreshToken).where(RefreshToken.token == payload.refresh_token)
    )
    token_db = token_q.scalar_one_or_none()
    if token_db is None or token_db.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    if token_db.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    access_token, access_exp = create_access_token(subject)
    refresh_token, refresh_exp = create_refresh_token(subject)

    token_db.token = refresh_token
    token_db.expires_at = refresh_exp
    await session.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_exp - datetime.now(timezone.utc)).total_seconds()),
    )
