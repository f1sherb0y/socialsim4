from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import auth, database, schemas

router = APIRouter()


@router.post(
    "/providers", response_model=schemas.Provider, status_code=status.HTTP_201_CREATED
)
async def create_provider(
    provider: schemas.ProviderCreate,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    new_provider = database.Provider(**provider.dict(), username=current_user.username)
    db.add(new_provider)
    try:
        await db.commit()
        await db.refresh(new_provider)
        return new_provider
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider with this usage already exists for the user.",
        )


@router.get("/providers", response_model=List[schemas.Provider])
async def get_providers(
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(database.Provider).filter(database.Provider.username == current_user.username)
    )
    return result.scalars().all()


@router.delete("/providers/{usage}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    usage: str,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(database.Provider).filter(
            database.Provider.username == current_user.username,
            database.Provider.usage == usage,
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    await db.delete(provider)
    await db.commit()
