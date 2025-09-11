import os
import secrets
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from socialsimv4.api import auth, database, schemas
from socialsimv4.api.config import STORAGE_PATH

router = APIRouter()

user_templates_path = os.path.join(STORAGE_PATH, "user_templates")

@router.post("/register", response_model=schemas.User)
async def register(user_data: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    existing_user = await auth.get_user(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    hashed_password = auth.get_password_hash(user_data.password)

    new_user = database.User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    return new_user

@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(database.get_db)
):
    user = await auth.get_user(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(key="auth_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.post("/logout")
async def logout():
    response = JSONResponse(content={"status": "success"})
    response.delete_cookie("auth_token")
    return response

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(auth.get_current_active_user)):
    return current_user
