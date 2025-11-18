from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from starlette.responses import StreamingResponse

from chatkit.server import NonStreamingResult, StreamingResult

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.chatkit.marketing_server import get_marketing_chat_server
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.marketing_token_service import (
    MarketingTokenError,
    MarketingTokenService,
)

router = APIRouter(prefix="/marketing", tags=["marketing"])


@lru_cache(maxsize=1)
def _token_service() -> MarketingTokenService:
    settings = get_settings()
    return MarketingTokenService(settings.marketing_chatkit_token_secret)


async def require_marketing_context(
    authorization: Annotated[str | None, Header(convert_underscores=False)] = None,
    marketing_client_secret: Annotated[
        str | None, Header(alias="x-marketing-client-secret", convert_underscores=False)
    ] = None,
) -> MarketingRequestContext:
    token: str | None = None

    if marketing_client_secret:
        token = marketing_client_secret.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing marketing client token",
        )
    try:
        claims = _token_service().verify(token)
    except MarketingTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return MarketingRequestContext(
        user_id=claims.sub,
        user_email=claims.email,
        user_name=claims.name,
    )


@router.post("/chatkit")
async def marketing_chatkit(
    request: Request,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    server = get_marketing_chat_server()
    body = await request.body()
    result = await server.process(body, context=context)
    if isinstance(result, StreamingResult):
        return StreamingResponse(
            result,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    if isinstance(result, NonStreamingResult):
        return Response(
            content=result.json,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unhandled ChatKit response",
    )
