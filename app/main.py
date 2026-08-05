from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.bootstrap import ensure_fresh_schema
from app.config import BASE_DIR, settings
from app.database import SessionLocal
from app.routers import admin, api_v1, payments, store
from app.seed import seed_all
from app.services.media import ensure_upload_dirs

app = FastAPI(
    title=settings.app_name,
    description=(
        "Whoopy marketplace + Management API. "
        "ERP / automation: `/api/v1/*` headerrel `X-API-Key`. "
        "Interaktív docs: `/docs` és `/redoc`."
    ),
    version="1.0.0",
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
ensure_upload_dirs()
app.mount(
    "/media/products",
    StaticFiles(directory=str(BASE_DIR / "data" / "uploads" / "products")),
    name="media_products",
)
app.include_router(store.router)
app.include_router(admin.router)
app.include_router(api_v1.router)
app.include_router(payments.router)


@app.on_event("startup")
def on_startup():
    ensure_fresh_schema()
    ensure_upload_dirs()
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
