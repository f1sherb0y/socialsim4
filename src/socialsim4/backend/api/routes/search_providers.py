from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import get_current_user, get_db_session
from ...models.user import SearchProviderConfig
from ...schemas.search_provider import (
    SearchProviderBase,
    SearchProviderCreate,
    SearchProviderUpdate,
)
from ...schemas.user import UserPublic


router = APIRouter()


def _serialize(provider: SearchProviderConfig) -> SearchProviderBase:
    return SearchProviderBase(
        id=provider.id,
        provider=provider.provider,
        base_url=provider.base_url,
        has_api_key=bool(provider.api_key),
        config=provider.config,
    )


@router.get("/", response_model=list[SearchProviderBase])
async def list_search_providers(
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SearchProviderBase]:
    result = await session.execute(select(SearchProviderConfig).where(SearchProviderConfig.user_id == current_user.id))
    providers = result.scalars().all()
    return [_serialize(p) for p in providers]


@router.post("/", response_model=SearchProviderBase, status_code=status.HTTP_201_CREATED)
async def create_search_provider(
    payload: SearchProviderCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SearchProviderBase:
    # Enforce single search provider per user (unique constraint)
    result = await session.execute(select(SearchProviderConfig).where(SearchProviderConfig.user_id == current_user.id))
    existing = result.scalars().first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search provider already exists")
    provider = SearchProviderConfig(
        user_id=current_user.id,
        provider=payload.provider,
        base_url=payload.base_url,
        api_key=payload.api_key,
        config=payload.config or {},
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return _serialize(provider)


@router.patch("/{provider_id}", response_model=SearchProviderBase)
async def update_search_provider(
    provider_id: int,
    payload: SearchProviderUpdate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SearchProviderBase:
    provider = await session.get(SearchProviderConfig, provider_id)
    if provider is None or provider.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search provider not found")
    if payload.provider is not None:
        provider.provider = payload.provider
    if payload.base_url is not None:
        provider.base_url = payload.base_url
    if payload.api_key is not None:
        provider.api_key = payload.api_key
    if payload.config is not None:
        provider.config = payload.config
    await session.commit()
    await session.refresh(provider)
    return _serialize(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_provider(
    provider_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    provider = await session.get(SearchProviderConfig, provider_id)
    if provider is None or provider.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search provider not found")
    await session.delete(provider)
    await session.commit()

