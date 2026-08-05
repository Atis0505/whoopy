from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.config import settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Érvénytelen vagy hiányzó X-API-Key",
        )
    return x_api_key
