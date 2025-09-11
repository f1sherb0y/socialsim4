from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth, database, schemas

router = APIRouter()


@router.post(
    "/providers", response_model=schemas.Provider, status_code=status.HTTP_201_CREATED
)
async def create_provider(
    provider: schemas.ProviderCreate,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    new_provider = database.Provider(**provider.dict(), username=current_user.username)
    db.add(new_provider)
    try:
        db.commit()
        db.refresh(new_provider)
        return new_provider
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider with this usage already exists for the user.",
        )


@router.get("/providers", response_model=List[schemas.Provider])
async def get_providers(
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    return (
        db.query(database.Provider)
        .filter(database.Provider.username == current_user.username)
        .all()
    )


@router.delete("/providers/{usage}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    usage: str,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    provider = (
        db.query(database.Provider)
        .filter(
            database.Provider.username == current_user.username,
            database.Provider.usage == usage,
        )
        .first()
    )
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    db.delete(provider)
    db.commit()
