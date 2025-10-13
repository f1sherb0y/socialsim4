from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import get_current_user, get_db_session
from ...models.user import ProviderConfig
from ...schemas.common import Message
from socialsim4.core.llm import create_llm_client
from socialsim4.core.llm_config import LLMConfig
from ...schemas.provider import ProviderBase, ProviderCreate, ProviderUpdate
from ...schemas.user import UserPublic


router = APIRouter()


def _serialize_provider(provider: ProviderConfig) -> ProviderBase:
    return ProviderBase(
        id=provider.id,
        name=provider.name,
        provider=provider.provider,
        model=provider.model,
        base_url=provider.base_url,
        has_api_key=bool(provider.api_key),
        last_test_status=provider.last_test_status,
        last_tested_at=provider.last_tested_at,
        last_error=provider.last_error,
        config=provider.config,
    )


@router.get("/", response_model=list[ProviderBase])
async def list_providers(
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ProviderBase]:
    result = await session.execute(
        select(ProviderConfig).where(ProviderConfig.user_id == current_user.id)
    )
    providers = result.scalars().all()
    return [_serialize_provider(p) for p in providers]


@router.post("/", response_model=ProviderBase, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ProviderCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProviderBase:
    provider = ProviderConfig(
        user_id=current_user.id,
        name=payload.name,
        provider=payload.provider,
        model=payload.model,
        base_url=payload.base_url,
        api_key=payload.api_key,
        config=payload.config or {},
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return _serialize_provider(provider)


@router.patch("/{provider_id}", response_model=ProviderBase)
async def update_provider(
    provider_id: int,
    payload: ProviderUpdate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProviderBase:
    provider = await session.get(ProviderConfig, provider_id)
    if provider is None or provider.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    if payload.name is not None:
        provider.name = payload.name
    if payload.provider is not None:
        provider.provider = payload.provider
    if payload.model is not None:
        provider.model = payload.model
    if payload.base_url is not None:
        provider.base_url = payload.base_url
    if payload.api_key is not None:
        provider.api_key = payload.api_key
    if payload.config is not None:
        provider.config = payload.config

    await session.commit()
    await session.refresh(provider)
    return _serialize_provider(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    provider = await session.get(ProviderConfig, provider_id)
    if provider is None or provider.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    await session.delete(provider)
    await session.commit()


@router.post("/{provider_id}/test", response_model=Message)
async def test_provider(
    provider_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    provider = await session.get(ProviderConfig, provider_id)
    if provider is None or provider.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    # Basic validation before test
    dialect = (provider.provider or "").lower()
    if dialect not in {"openai", "gemini", "mock"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid LLM provider dialect")
    if dialect != "mock" and not provider.api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LLM API key required")
    if not provider.model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LLM model required")

    cfg = LLMConfig(
        dialect=dialect,
        api_key=provider.api_key or "",
        model=provider.model,
        base_url=provider.base_url,
        temperature=0.7,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=64,
    )

    status_msg = ""
    provider.last_tested_at = datetime.now(timezone.utc)
    try:
        client = create_llm_client(cfg)
        # Minimal ping to validate credentials/connectivity
        _ = client.chat([
            {"role": "user", "content": "ping"}
        ])
        provider.last_test_status = "success"
        provider.last_error = None
        status_msg = "Provider connectivity verified"
    except Exception as exc:  # noqa: BLE001 - API layer may wrap exceptions
        provider.last_test_status = "error"
        provider.last_error = str(exc)
        status_msg = "Provider connectivity failed"

    await session.commit()

    return Message(message=status_msg)
