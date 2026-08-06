import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.bootstrap import ensure_fresh_schema
from app.config import BASE_DIR, settings
from app.database import SessionLocal
from app.middleware_security import ApiRateLimitMiddleware, SecurityHeadersMiddleware
from app.routers import admin, admin_extra, admin_marketplace, api_v1, eu_shop, payments, store
from app.seed import seed_all
from app.services.media import ensure_upload_dirs

logger = logging.getLogger("whoopy")

docs_url = "/docs" if settings.docs_enabled else None
redoc_url = "/redoc" if settings.docs_enabled else None

app = FastAPI(
    title=settings.app_name,
    description=(
        "Whoopy marketplace + Management API. "
        "ERP / automation: `/api/v1/*` headerrel `X-API-Key`. "
        "Interaktív docs: `/docs` és `/redoc`."
    ),
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# Middleware order: last added = outermost
app.add_middleware(SecurityHeadersMiddleware)
if settings.rate_limit_enabled:
    app.add_middleware(ApiRateLimitMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie,
    https_only=settings.session_https_only or settings.force_https,
    same_site=settings.session_same_site,
)
if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)
if settings.trusted_host_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")
ensure_upload_dirs()
app.mount(
    "/media/products",
    StaticFiles(directory=str(BASE_DIR / "data" / "uploads" / "products")),
    name="media_products",
)
app.include_router(store.router)
app.include_router(eu_shop.router)
app.include_router(admin.router)
app.include_router(admin_extra.router)
app.include_router(admin_marketplace.router)
app.include_router(api_v1.router)
app.include_router(payments.router)


@app.get("/healthz", tags=["Meta"])
def healthz():
    """Load balancer / uptime check — no auth."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.on_event("startup")
def on_startup():
    bad = settings.insecure_defaults()
    if settings.is_production and bad:
        logger.error(
            "PRODUCTION with insecure defaults: %s — change them in .env before going live!",
            ", ".join(bad),
        )
    elif bad:
        logger.warning("Dev defaults still in use: %s", ", ".join(bad))

    ensure_fresh_schema()
    ensure_upload_dirs()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()
    else:
        logger.info("seed_on_startup=false — skipping seed")
