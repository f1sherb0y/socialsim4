from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from socialsim4.api import auth, database, schemas

router = APIRouter()


@router.post(
    "/providers", response_model=List[schemas.Provider], status_code=status.HTTP_200_OK
)
async def upsert_providers(
    providers: List[schemas.ProviderCreate],
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    # Get existing providers for the user
    result = await db.execute(
        select(database.Provider).filter(
            database.Provider.username == current_user.username
        )
    )
    existing_providers = {p.usage: p for p in result.scalars().all()}

    response_providers = []

    for provider_data in providers:
        if provider_data.usage in existing_providers:
            # Update existing provider
            existing_provider = existing_providers[provider_data.usage]
            for key, value in provider_data.dict().items():
                setattr(existing_provider, key, value)
            response_providers.append(existing_provider)
        else:
            # Create new provider
            new_provider = database.Provider(
                **provider_data.dict(), username=current_user.username
            )
            db.add(new_provider)
            response_providers.append(new_provider)

    try:
        await db.commit()
        for p in response_providers:
            await db.refresh(p)
        return response_providers
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An integrity error occurred.",
        )


@router.get("/providers", response_model=List[schemas.Provider])
async def get_providers(
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(database.Provider).filter(
            database.Provider.username == current_user.username
        )
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
