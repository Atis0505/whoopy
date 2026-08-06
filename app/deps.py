from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import EU_SHIP_COUNTRIES, SUPPORTED_LANGS, normalize_lang, t
from app.models import CurrencyRate, User
from app.seed_auth import verify_password
from app.services.cart import get_or_create_cart
from app.services.currency import format_money


def get_session_key(request: Request) -> str:
    key = request.session.get("cart_key")
    if not key:
        key = secrets.token_hex(16)
        request.session["cart_key"] = key
    return key


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def try_login(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def cart_for_request(request: Request, db: Session):
    cart = get_or_create_cart(db, get_session_key(request))
    # sync prefs from session
    lang = normalize_lang(request.session.get("lang") or cart.lang)
    currency = (request.session.get("currency") or cart.currency or "HUF").upper()
    country = (request.session.get("country") or cart.country or "HU").upper()
    changed = False
    if cart.lang != lang:
        cart.lang = lang
        changed = True
    if cart.currency != currency:
        cart.currency = currency
        changed = True
    if cart.country != country:
        cart.country = country
        changed = True
    if changed:
        db.commit()
        db.refresh(cart)
    return cart


def require_admin_redirect(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not (user.role == "admin" or user.is_admin):
        return RedirectResponse("/login", status_code=303)
    return user


def require_staff_redirect(request: Request, db: Session) -> User | RedirectResponse:
    """Admin or worker."""
    user = get_current_user(request, db)
    if not user or not user.is_staff:
        return RedirectResponse("/login", status_code=303)
    return user


def post_login_redirect(user: User) -> str:
    if user.role == "admin" or user.is_admin:
        return "/admin"
    if user.role == "worker":
        return "/admin/orders"
    return "/account"


def store_context(request: Request, db: Session, **extra):
    from app.services.attribution import apply_attribution_to_cart, capture_attribution, session_attribution

    capture_attribution(request)
    cart = cart_for_request(request, db)
    before = {k: getattr(cart, k, "") for k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "affiliate_code")}
    apply_attribution_to_cart(cart, request.session)
    after = {k: getattr(cart, k, "") for k in before}
    if before != after:
        try:
            db.commit()
        except Exception:
            db.rollback()
    from app.models import Category
    from app.services.cart import quote_cart
    from app.config import settings

    quote = quote_cart(db, cart)
    lang = normalize_lang(cart.lang)
    currency = cart.currency or "HUF"
    currencies = db.query(CurrencyRate).filter(CurrencyRate.active.is_(True)).order_by(CurrencyRate.code).all()
    roots = db.query(Category).filter(Category.parent_id.is_(None)).order_by(Category.name).all()

    def money(amount_huf: float) -> str:
        return format_money(db, amount_huf, currency)

    store = None
    try:
        from app.services.store_settings import get_store_settings

        store = get_store_settings(db)
    except Exception:
        store = None

    announcement = None
    ticker_items = []
    free_ship = {"enabled": False}
    is_dev = True
    try:
        from app.config import settings as app_settings
        from app.services.storefront_ops import (
            announcement_active,
            free_shipping_progress,
            social_ticker_items,
        )

        if announcement_active(store):
            announcement = {
                "text": store.announcement_text,
                "link": store.announcement_link or "",
                "label": store.announcement_link_label or "Részletek",
                "bg": store.announcement_bg or "#0f766e",
            }
        if store and getattr(store, "ticker_enabled", True):
            ticker_items = social_ticker_items(db)
        free_ship = free_shipping_progress(store, quote.items_subtotal if quote else 0)
        is_dev = getattr(app_settings, "environment", "development") != "production"
    except Exception:
        pass

    orders_enabled = True
    storefront_status = "open"
    orders_paused_message = ""
    try:
        from app.services.storefront_ops import get_storefront_status, orders_enabled as _orders_on

        storefront_status = get_storefront_status(store)
        orders_enabled = _orders_on(store)
        orders_paused_message = (getattr(store, "orders_paused_message", "") or "") if store else ""
    except Exception:
        pass

    ctx = {
        "request": request,
        "user": get_current_user(request, db),
        "cart": cart,
        "quote": quote,
        "lang": lang,
        "currency": currency,
        "currencies": currencies,
        "countries": EU_SHIP_COUNTRIES,
        "langs": SUPPORTED_LANGS,
        "categories": roots,
        "t": lambda key: t(lang, key),
        "money": money,
        "app_name": settings.app_name,
        "app_domain": settings.app_domain,
        "chat_enabled": bool(getattr(store, "chat_enabled", True)) if store else True,
        "chat_widget_html": (getattr(store, "chat_widget_html", "") or "") if store else "",
        "store": store,
        "announcement": announcement,
        "ticker_items": ticker_items,
        "free_ship": free_ship,
        "demo_badge": is_dev,
        "business_hours": (getattr(store, "business_hours", "") or "") if store else "",
        "orders_enabled": orders_enabled,
        "storefront_status": storefront_status,
        "orders_paused_message": orders_paused_message,
    }
    ctx.update(extra)
    return ctx
