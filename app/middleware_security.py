"""Security middleware: headers, simple in-memory API rate limit."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if settings.force_https or settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limit for /api/v1 (per client IP)."""

    def __init__(self, app, *, limit: int | None = None, window_sec: int = 60):
        super().__init__(app)
        self.limit = limit or settings.rate_limit_api_per_minute
        self.window = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)
        path = request.url.path
        if not path.startswith("/api/v1"):
            return await call_next(request)
        # health / docs-style meta under api still limited lightly — OK
        key = self._client_key(request)
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return JSONResponse(
                {"detail": "Rate limit exceeded — próbáld később"},
                status_code=429,
                headers={"Retry-After": str(self.window)},
            )
        q.append(now)
        return await call_next(request)
