"""Maintenance mode + request.state storefront ops flags."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from app.database import SessionLocal
from app.services.store_settings import get_store_settings

_ALLOW_PREFIXES = (
    "/admin",
    "/login",
    "/logout",
    "/static",
    "/media",
    "/api",
    "/healthz",
    "/pay/webhook",
    "/feeds",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon",
)


def _allowed(path: str) -> bool:
    if path in ("/login", "/logout", "/healthz"):
        return True
    return any(path == p or path.startswith(p + "/") or path.startswith(p) for p in _ALLOW_PREFIXES)


_MAINTENANCE_HTML = """<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bolt zárva – Whoopy</title>
  <style>
    body {{ margin:0; min-height:100vh; display:grid; place-items:center;
      font-family: Manrope, system-ui, sans-serif; background:#0b1220; color:#e2e8f0; padding:1.5rem; }}
    .box {{ max-width:28rem; text-align:center; }}
    h1 {{ font-family: Sora, system-ui, sans-serif; font-size:clamp(1.4rem,4vw,1.85rem); margin:0 0 .75rem; }}
    p {{ color:#94a3b8; line-height:1.55; }}
    a {{ color:#5eead4; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Whoopy.hu</h1>
    <p>{message}</p>
    <p><a href="/login">Belépés (admin / dolgozó)</a></p>
  </div>
</body>
</html>
"""


class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path or "/"
        db = SessionLocal()
        try:
            store = get_store_settings(db)
            request.state.maintenance_mode = bool(store.maintenance_mode)
            try:
                from app.services.storefront_ops import pending_order_count

                request.state.pending_orders = pending_order_count(db) if path.startswith("/admin") else 0
            except Exception:
                request.state.pending_orders = 0

            if _allowed(path):
                return await call_next(request)

            if not store.maintenance_mode:
                return await call_next(request)

            user_id = request.session.get("user_id") if hasattr(request, "session") else None
            if user_id:
                from app.models import User

                user = db.get(User, user_id)
                if user and user.is_staff:
                    return await call_next(request)

            msg = (store.maintenance_message or "A bolt átmenetileg zárva van.").replace("<", "&lt;")
            return HTMLResponse(_MAINTENANCE_HTML.format(message=msg), status_code=503)
        finally:
            db.close()
