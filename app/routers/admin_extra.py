"""Shopify-szerű admin bővítések: settings, customers, staff, analytics, CMS, inventory."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Cart,
    CartItem,
    Category,
    CmsPage,
    ContactMessage,
    Offer,
    Order,
    Product,
    ReturnRequest,
    User,
)
from app.seed_auth import hash_password
from app.services.store_settings import get_store_settings, touch_settings

router = APIRouter(prefix="/admin", tags=["admin-extra"])
templates = Jinja2Templates(directory="app/templates")


def _money(value: float) -> str:
    return f"{value:,.0f} Ft".replace(",", " ")


templates.env.filters["huf"] = _money


def _require_admin(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not (user.role == "admin" or user.is_admin):
        return RedirectResponse("/login", status_code=303)
    return user


def _require_staff(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not user.is_staff:
        return RedirectResponse("/login", status_code=303)
    return user


# ── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    store = get_store_settings(db)
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": user,
            "store": store,
            "app_name": settings.app_name,
            "cfg": settings,
        },
    )


@router.post("/settings")
def settings_save(
    request: Request,
    store_name: str = Form(...),
    domain: str = Form(""),
    support_email: str = Form(""),
    support_phone: str = Form(""),
    default_currency: str = Form("HUF"),
    default_country: str = Form("HU"),
    default_lang: str = Form("hu"),
    tax_rate_percent: float = Form(27.0),
    low_stock_threshold: int = Form(5),
    order_prefix: str = Form("TM"),
    company_name: str = Form(""),
    company_address: str = Form(""),
    company_tax_id: str = Form(""),
    company_eu_vat: str = Form(""),
    invoice_footer: str = Form(""),
    chat_enabled: str = Form(""),
    chat_widget_html: str = Form(""),
    loyalty_earn_per_100: float = Form(1.0),
    loyalty_point_value_huf: float = Form(1.0),
    pickup_fee_huf: float = Form(990.0),
    erp_enabled: str = Form(""),
    erp_api_base: str = Form(""),
    google_feed_enabled: str = Form(""),
    maintenance_mode: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    store = get_store_settings(db)
    store.store_name = store_name.strip() or "Whoopy"
    store.domain = domain.strip() or "whoopy.hu"
    store.support_email = support_email.strip()
    store.support_phone = support_phone.strip()
    store.default_currency = default_currency.strip().upper()[:3]
    store.default_country = default_country.strip().upper()[:2]
    store.default_lang = default_lang.strip().lower()[:5]
    store.tax_rate_percent = tax_rate_percent
    store.low_stock_threshold = max(0, low_stock_threshold)
    store.order_prefix = order_prefix.strip() or "TM"
    store.company_name = company_name.strip() or store.company_name
    store.company_address = company_address.strip()
    store.company_tax_id = company_tax_id.strip()
    store.company_eu_vat = company_eu_vat.strip()
    store.invoice_footer = invoice_footer.strip()
    store.chat_enabled = chat_enabled == "1"
    store.chat_widget_html = chat_widget_html.strip()
    store.loyalty_earn_per_100 = loyalty_earn_per_100
    store.loyalty_point_value_huf = loyalty_point_value_huf
    store.pickup_fee_huf = pickup_fee_huf
    store.erp_enabled = erp_enabled == "1"
    store.erp_api_base = erp_api_base.strip() or store.erp_api_base
    store.google_feed_enabled = google_feed_enabled == "1"
    store.maintenance_mode = maintenance_mode == "1"
    touch_settings(store)
    db.commit()
    return RedirectResponse("/admin/settings?saved=1", status_code=303)


# ── Customers / staff ────────────────────────────────────────────────────────

@router.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    customers = (
        db.query(User)
        .filter(User.role == "customer")
        .order_by(User.created_at.desc())
        .all()
    )
    order_counts = dict(
        db.query(Order.customer_id, func.count(Order.id))
        .filter(Order.customer_id.isnot(None))
        .group_by(Order.customer_id)
        .all()
    )
    return templates.TemplateResponse(
        "admin/customers.html",
        {
            "request": request,
            "user": user,
            "customers": customers,
            "order_counts": order_counts,
            "app_name": settings.app_name,
        },
    )


@router.get("/staff", response_class=HTMLResponse)
def staff_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    staff = (
        db.query(User)
        .filter(User.role.in_(("admin", "worker")))
        .order_by(User.role, User.email)
        .all()
    )
    return templates.TemplateResponse(
        "admin/staff.html",
        {"request": request, "user": user, "staff": staff, "app_name": settings.app_name},
    )


@router.post("/staff/create")
def staff_create(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(""),
    password: str = Form(...),
    role: str = Form("worker"),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    role = role if role in ("admin", "worker") else "worker"
    email_n = email.strip().lower()
    if db.query(User).filter(User.email == email_n).first():
        return RedirectResponse("/admin/staff?error=exists", status_code=303)
    db.add(
        User(
            email=email_n,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=role,
            is_admin=(role == "admin"),
        )
    )
    db.commit()
    return RedirectResponse("/admin/staff?ok=1", status_code=303)


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    since = datetime.utcnow() - timedelta(days=30)
    revenue = (
        db.query(func.coalesce(func.sum(Order.grand_total), 0.0))
        .filter(Order.created_at >= since, Order.status.in_(("paid", "fulfilled", "pending")))
        .scalar()
        or 0.0
    )
    paid_revenue = (
        db.query(func.coalesce(func.sum(Order.grand_total), 0.0))
        .filter(Order.payment_status == "paid")
        .scalar()
        or 0.0
    )
    by_status = dict(db.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    top_products = (
        db.query(Product)
        .filter(Product.sold_count > 0)
        .order_by(Product.sold_count.desc())
        .limit(10)
        .all()
    )
    recent_days = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
        cnt = (
            db.query(func.count(Order.id))
            .filter(Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0
        )
        total = (
            db.query(func.coalesce(func.sum(Order.grand_total), 0.0))
            .filter(Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0.0
        )
        recent_days.append({"day": day.isoformat(), "orders": cnt, "revenue": total})
    max_orders = max((d["orders"] for d in recent_days), default=1) or 1
    return templates.TemplateResponse(
        "admin/analytics.html",
        {
            "request": request,
            "user": user,
            "app_name": settings.app_name,
            "revenue_30d": revenue,
            "paid_revenue": paid_revenue,
            "by_status": by_status,
            "top_products": top_products,
            "recent_days": recent_days,
            "max_orders": max_orders,
            "order_count": db.query(Order).count(),
        },
    )


# ── Inventory ────────────────────────────────────────────────────────────────

@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    store = get_store_settings(db)
    threshold = store.low_stock_threshold
    offers = (
        db.query(Offer)
        .options(joinedload(Offer.product), joinedload(Offer.supplier))
        .order_by(Offer.stock.asc(), Offer.id.desc())
        .limit(200)
        .all()
    )
    low = [o for o in offers if o.stock <= threshold]
    return templates.TemplateResponse(
        "admin/inventory.html",
        {
            "request": request,
            "user": user,
            "offers": offers,
            "low": low,
            "threshold": threshold,
            "app_name": settings.app_name,
        },
    )


@router.post("/inventory/{offer_id}")
def inventory_update(
    offer_id: int,
    request: Request,
    stock: int = Form(...),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    offer = db.get(Offer, offer_id)
    if offer:
        offer.stock = max(0, stock)
        db.commit()
    return RedirectResponse("/admin/inventory", status_code=303)


# ── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories", response_class=HTMLResponse)
def categories_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    query = db.query(Category)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter((Category.name.ilike(like)) | (Category.full_path.ilike(like)))
    cats = query.order_by(Category.full_path).limit(200).all()
    counts = dict(
        db.query(Product.category_id, func.count(Product.id))
        .filter(Product.category_id.isnot(None))
        .group_by(Product.category_id)
        .all()
    )
    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "user": user,
            "categories": cats,
            "counts": counts,
            "q": q,
            "app_name": settings.app_name,
        },
    )


# ── CMS pages ────────────────────────────────────────────────────────────────

@router.get("/pages", response_class=HTMLResponse)
def pages_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    pages = db.query(CmsPage).order_by(CmsPage.slug).all()
    return templates.TemplateResponse(
        "admin/pages.html",
        {"request": request, "user": user, "pages": pages, "app_name": settings.app_name},
    )


@router.post("/pages/create")
def pages_create(
    request: Request,
    slug: str = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    published: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    slug_n = slug.strip().lower().replace(" ", "-")
    if db.query(CmsPage).filter(CmsPage.slug == slug_n).first():
        return RedirectResponse("/admin/pages?error=exists", status_code=303)
    db.add(
        CmsPage(
            slug=slug_n,
            title=title.strip(),
            body=body,
            published=published == "1",
        )
    )
    db.commit()
    return RedirectResponse("/admin/pages", status_code=303)


@router.post("/pages/{page_id}")
def pages_update(
    page_id: int,
    request: Request,
    title: str = Form(...),
    body: str = Form(""),
    published: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    page = db.get(CmsPage, page_id)
    if page:
        page.title = title.strip()
        page.body = body
        page.published = published == "1"
        page.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse("/admin/pages", status_code=303)


# ── Abandoned carts ──────────────────────────────────────────────────────────

@router.get("/abandoned-carts", response_class=HTMLResponse)
def abandoned_carts(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    cutoff = datetime.utcnow() - timedelta(hours=2)
    carts = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.offer).joinedload(Offer.product))
        .filter(Cart.updated_at < cutoff)
        .order_by(Cart.updated_at.desc())
        .limit(50)
        .all()
    )
    carts = [c for c in carts if c.items]
    return templates.TemplateResponse(
        "admin/abandoned_carts.html",
        {
            "request": request,
            "user": user,
            "carts": carts,
            "app_name": settings.app_name,
            "sent": request.query_params.get("sent"),
        },
    )


@router.post("/abandoned-carts/send")
def abandoned_carts_send(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.email import send_mail

    cutoff = datetime.utcnow() - timedelta(hours=2)
    carts = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.offer).joinedload(Offer.product))
        .filter(Cart.updated_at < cutoff, Cart.abandoned_email_sent_at.is_(None))
        .order_by(Cart.updated_at.desc())
        .limit(50)
        .all()
    )
    n = 0
    for c in carts:
        if not c.items:
            continue
        # Nincs e-mail a kosáron — session guest: skip, hacsak nincs user a sessionben
        # Demo: küldjük a support címre logként + outbox stub címzettként cart id
        lines = "\n".join(
            f"- {it.quantity}× {it.offer.product.title if it.offer and it.offer.product else it.offer_id}"
            for it in c.items
        )
        to = settings.admin_email
        ok = send_mail(
            to=to,
            subject=f"[Whoopy] Elhagyott kosár #{c.id}",
            body=f"Kosár #{c.id} ({c.country}/{c.currency}) elhagyva.\n\n{lines}\n\nSession: {c.session_key}\n",
        )
        if ok:
            c.abandoned_email_sent_at = datetime.utcnow()
            n += 1
    db.commit()
    return RedirectResponse(f"/admin/abandoned-carts?sent={n}", status_code=303)


# ── Integrations (honest) ────────────────────────────────────────────────────

@router.get("/integrations", response_class=HTMLResponse)
async def integrations_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    store = get_store_settings(db)
    from app.services.erp_bridge import erp_status, ping_erp
    from app.services.payments import resolve_provider

    erp = erp_status()
    erp_ping = await ping_erp() if settings.erp_enabled else {"ok": False, "reason": "disabled"}
    return templates.TemplateResponse(
        "admin/integrations.html",
        {
            "request": request,
            "user": user,
            "store": store,
            "cfg": settings,
            "erp": erp,
            "erp_ping": erp_ping,
            "resolved_payment": resolve_provider(),
            "media_base": settings.media_base,
            "app_name": settings.app_name,
            "flash": request.session.pop("integrations_flash", None),
        },
    )


@router.post("/integrations/erp-autosync")
async def integrations_erp_autosync(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.erp_bridge import trigger_erp_autosync

    result = await trigger_erp_autosync()
    request.session["integrations_flash"] = str(result)
    return RedirectResponse("/admin/integrations", status_code=303)


# ── Google Merchant Center ───────────────────────────────────────────────────

@router.get("/merchant", response_class=HTMLResponse)
def merchant_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.models import Category
    from app.services.google_feed import validate_and_collect
    from app.services.taxonomy import TAXONOMY_FILE

    store = get_store_settings(db)
    _items, report = validate_and_collect(db)
    return templates.TemplateResponse(
        "admin/merchant.html",
        {
            "request": request,
            "user": user,
            "store": store,
            "report": report,
            "category_count": db.query(Category).count(),
            "taxonomy_file_exists": TAXONOMY_FILE.exists(),
            "taxonomy_file": str(TAXONOMY_FILE),
            "feed_url": f"{settings.public_base_url.rstrip('/')}/feeds/google-merchant.xml",
            "app_name": settings.app_name,
            "import_result": request.session.pop("taxonomy_import_result", None),
        },
    )


@router.post("/merchant/import-taxonomy")
def merchant_import_taxonomy(
    request: Request,
    download: str = Form("1"),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    import json

    from app.services.taxonomy import import_official_taxonomy

    try:
        result = import_official_taxonomy(db, download=download == "1")
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    request.session["taxonomy_import_result"] = json.dumps(result, ensure_ascii=False, indent=2)
    return RedirectResponse("/admin/merchant", status_code=303)


@router.get("/contact-messages", response_class=HTMLResponse)
def contact_messages_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    messages = db.query(ContactMessage).order_by(ContactMessage.id.desc()).limit(200).all()
    return templates.TemplateResponse(
        "admin/contact_messages.html",
        {"request": request, "user": user, "messages": messages, "app_name": settings.app_name},
    )


@router.post("/contact-messages/{msg_id}/status")
def contact_message_status(
    msg_id: int,
    request: Request,
    status: str = Form("read"),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    msg = db.get(ContactMessage, msg_id)
    if msg:
        msg.status = status.strip()[:32] or "read"
        db.commit()
    return RedirectResponse("/admin/contact-messages", status_code=303)


@router.get("/returns", response_class=HTMLResponse)
def returns_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    returns = db.query(ReturnRequest).order_by(ReturnRequest.id.desc()).limit(200).all()
    order_ids = {r.order_id for r in returns}
    orders = {o.id: o for o in db.query(Order).filter(Order.id.in_(order_ids)).all()} if order_ids else {}
    return templates.TemplateResponse(
        "admin/returns.html",
        {
            "request": request,
            "user": user,
            "returns": returns,
            "orders": orders,
            "app_name": settings.app_name,
        },
    )


@router.post("/returns/{ret_id}/status")
def return_status(
    ret_id: int,
    request: Request,
    status: str = Form("approved"),
    admin_note: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    ret = db.get(ReturnRequest, ret_id)
    if ret:
        ret.status = status.strip()[:32] or ret.status
        ret.admin_note = admin_note.strip()[:512]
        ret.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse("/admin/returns", status_code=303)


@router.post("/returns/{ret_id}/label")
def return_label(
    ret_id: int,
    request: Request,
    carrier: str = Form("gls"),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.rma import generate_return_label

    ret = db.get(ReturnRequest, ret_id)
    if ret:
        generate_return_label(db, ret, carrier=carrier)
    return RedirectResponse("/admin/returns", status_code=303)


@router.post("/returns/{ret_id}/refund")
def return_refund(
    ret_id: int,
    request: Request,
    amount: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.rma import mark_refund

    ret = db.get(ReturnRequest, ret_id)
    if ret:
        amt = None
        if amount.strip():
            try:
                amt = float(amount.replace(",", "."))
            except ValueError:
                amt = None
        mark_refund(db, ret, amount=amt)
    return RedirectResponse("/admin/returns", status_code=303)
