"""Storefront státusz: open / catalog_only / closed."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from app.database import SessionLocal
from app.services.store_settings import get_store_settings
from app.services.storefront_ops import (
    STATUS_CATALOG_ONLY,
    STATUS_CLOSED,
    get_storefront_status,
)

# Teljes záráskor is elérhető (admin + infra)
_CLOSED_ALLOW_PREFIXES = (
    "/admin",
    "/login",
    "/logout",
    "/static",
    "/media",
    "/api",
    "/healthz",
    "/pay/webhook",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon",
)

# Rendelés szünet: ezeken nincs új kosár / checkout
_ORDER_PATH_PREFIXES = (
    "/cart",
    "/checkout",
    "/pay/",
    "/account/subscriptions",
)


def _path_allowed_when_closed(path: str) -> bool:
    if path in ("/login", "/logout", "/healthz"):
        return True
    return any(path == p or path.startswith(p + "/") or path.startswith(p) for p in _CLOSED_ALLOW_PREFIXES)


def _is_order_path(path: str) -> bool:
    if path in ("/cart", "/checkout"):
        return True
    return any(path == p or path.startswith(p) for p in _ORDER_PATH_PREFIXES)


_CLOSED_HTML = """<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex" />
  <title>Bolt inaktív – Whoopy</title>
  <style>
    body {{ margin:0; min-height:100vh; display:grid; place-items:center;
      font-family: Manrope, system-ui, sans-serif; background:#0b1220; color:#e2e8f0; padding:1.5rem; }}
    .box {{ max-width:32rem; text-align:center; }}
    .mark {{
      width:3rem; height:3rem; border-radius:12px; margin:0 auto 1rem;
      background:linear-gradient(135deg,#14b8a6,#0f766e); display:grid; place-items:center;
      font-weight:800; font-family:Sora,system-ui,sans-serif;
    }}
    h1 {{ font-family: Sora, system-ui, sans-serif; font-size:clamp(1.5rem,4vw,2rem); margin:0 0 .5rem; }}
    .sub {{ color:#5eead4; font-weight:650; margin:0 0 1rem; letter-spacing:0.02em; }}
    p {{ color:#94a3b8; line-height:1.6; margin:0 0 1rem; }}
    a {{ color:#5eead4; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="mark">W</div>
    <h1>Whoopy.hu</h1>
    <p class="sub">A bolt jelenleg nem üzemel</p>
    <p>{message}</p>
    <p><a href="/login">Belépés (csak admin)</a></p>
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
            status = get_storefront_status(store)
            request.state.storefront_status = status
            request.state.orders_enabled = status == "open"
            request.state.maintenance_mode = status == STATUS_CLOSED
            try:
                from app.services.storefront_ops import pending_order_count

                request.state.pending_orders = pending_order_count(db) if path.startswith("/admin") else 0
            except Exception:
                request.state.pending_orders = 0

            if status == STATUS_CLOSED:
                if _path_allowed_when_closed(path):
                    return await call_next(request)
                msg = (
                    store.maintenance_message
                    or "Jelenleg a boltunk inaktív, nem üzemel — rendeléseket sem fogadunk."
                ).replace("<", "&lt;")
                return HTMLResponse(_CLOSED_HTML.format(message=msg), status_code=503)

            if status == STATUS_CATALOG_ONLY and _is_order_path(path):
                # meglévő rendelés megtekintés / számla OK
                if path.startswith("/order/") or path.startswith("/pay/webhook"):
                    return await call_next(request)
                if path.startswith("/pay/") and request.method == "GET":
                    # félbehagyott fizetés oldal — engedjük
                    return await call_next(request)
                if request.method in ("POST", "PUT", "PATCH", "DELETE") or path in ("/cart", "/checkout") or path.startswith("/cart"):
                    # UI: redirect haza; API-szerű: 403 szöveg
                    accept = (request.headers.get("accept") or "").lower()
                    if "text/html" in accept or request.method == "GET":
                        return RedirectResponse("/?orders_paused=1", status_code=303)
                    return HTMLResponse("Rendelésfogadás szünetel.", status_code=403)

            return await call_next(request)
        finally:
            db.close()
