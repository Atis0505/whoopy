"""Vásárlói élmény route-ok: keresés, compare, pickup, gift/loyalty, newsletter send hooks."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import store_context
from app.models import NewsletterSubscriber, Product
from app.services.customer_ux import (
    list_pickup_points,
    search_products,
    session_list_ids,
    suggest_products,
    toggle_compare,
)
from app.services.email import send_mail

router = APIRouter(tags=["customer-ux"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/search", response_class=HTMLResponse)
def search_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    from app.routers.store import _enrich_products

    products = search_products(db, q, limit=60)
    _enrich_products(db, products)
    return templates.TemplateResponse(
        "store/search.html",
        store_context(request, db, products=products, q=q),
    )


@router.get("/api/suggest")
def api_suggest(q: str = "", db: Session = Depends(get_db)):
    return JSONResponse({"items": suggest_products(db, q, limit=8)})


@router.get("/compare", response_class=HTMLResponse)
def compare_page(request: Request, db: Session = Depends(get_db)):
    from app.routers.store import _enrich_products

    ids = session_list_ids(request.session, "compare_ids")
    products = []
    if ids:
        products = (
            db.query(Product)
            .options(joinedload(Product.offers), joinedload(Product.category))
            .filter(Product.id.in_(ids), Product.active.is_(True))
            .all()
        )
        # preserve order
        by_id = {p.id: p for p in products}
        products = [by_id[i] for i in ids if i in by_id]
        _enrich_products(db, products)
    return templates.TemplateResponse(
        "store/compare.html",
        store_context(request, db, products=products),
    )


@router.post("/compare/toggle")
def compare_toggle(request: Request, product_id: int = Form(...)):
    toggle_compare(request.session, product_id)
    return RedirectResponse(request.headers.get("referer", "/compare"), status_code=303)


@router.get("/recent", response_class=HTMLResponse)
def recent_page(request: Request, db: Session = Depends(get_db)):
    from app.routers.store import _enrich_products

    ids = session_list_ids(request.session, "recent_products")
    products = []
    if ids:
        found = (
            db.query(Product)
            .options(joinedload(Product.offers))
            .filter(Product.id.in_(ids), Product.active.is_(True))
            .all()
        )
        by_id = {p.id: p for p in found}
        products = [by_id[i] for i in ids if i in by_id]
        _enrich_products(db, products)
    return templates.TemplateResponse(
        "store/recent.html",
        store_context(request, db, products=products),
    )


@router.get("/api/pickup-points")
def api_pickup_points(provider: str = "", city: str = "", q: str = "", db: Session = Depends(get_db)):
    points = list_pickup_points(db, provider=provider, city=city, q=q, limit=50)
    return JSONResponse(
        {
            "items": [
                {
                    "id": p.external_id,
                    "provider": p.provider,
                    "name": p.name,
                    "city": p.city,
                    "zip": p.zip_code,
                    "address": p.address,
                    "label": f"{p.name} — {p.zip_code} {p.city}, {p.address}",
                }
                for p in points
            ]
        }
    )
