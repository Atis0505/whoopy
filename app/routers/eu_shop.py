"""EU webshop extra: SEO, kontakt, tracking, wishlist, returns, reviews, alerts."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_session_key, store_context
from app.models import (
    ContactMessage,
    Order,
    Product,
    ProductReview,
    ReturnRequest,
    StockAlert,
    WishlistItem,
)
from app.services.email import send_mail
from app.services.store_settings import get_store_settings

router = APIRouter(tags=["eu-shop"])
templates = Jinja2Templates(directory="app/templates")


# ── SEO ──────────────────────────────────────────────────────────────────────

@router.get("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {settings.public_base_url.rstrip('/')}/sitemap.xml\n"
    )
    return PlainTextResponse(body)


@router.get("/sitemap.xml")
def sitemap_xml(db: Session = Depends(get_db)):
    base = settings.public_base_url.rstrip("/")
    urls = [f"{base}/", f"{base}/taxonomy", f"{base}/contact", f"{base}/faq", f"{base}/track"]
    for slug in ("aszf", "adatvedelem", "impressum", "szallitas", "visszakuldes", "rolunk"):
        urls.append(f"{base}/pages/{slug}")
    products = db.query(Product).filter(Product.active.is_(True)).order_by(Product.id.desc()).limit(5000).all()
    for p in products:
        urls.append(f"{base}/p/{p.slug}")
    items = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{items}</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


# ── Cookie consent ───────────────────────────────────────────────────────────

@router.post("/cookies/consent")
def cookie_consent(request: Request, choice: str = Form("necessary")):
    request.session["cookie_consent"] = choice if choice in ("necessary", "all") else "necessary"
    next_url = request.headers.get("referer") or "/"
    return RedirectResponse(next_url, status_code=303)


# ── Contact ──────────────────────────────────────────────────────────────────

@router.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "store/contact.html",
        store_context(request, db, ok=request.query_params.get("ok")),
    )


@router.post("/contact")
def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(""),
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    db.add(
        ContactMessage(
            name=name.strip()[:255],
            email=email.strip()[:255],
            subject=(subject or "Kapcsolat").strip()[:255],
            body=body.strip()[:8000],
        )
    )
    db.commit()
    store = get_store_settings(db)
    send_mail(
        to=store.support_email or settings.admin_email,
        subject=f"[Whoopy kontakt] {subject or name}",
        body=f"From: {name} <{email}>\n\n{body}",
    )
    return RedirectResponse("/contact?ok=1", status_code=303)


# ── FAQ ──────────────────────────────────────────────────────────────────────

@router.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("store/faq.html", store_context(request, db))


# ── Order tracking (guest) ───────────────────────────────────────────────────

@router.get("/track", response_class=HTMLResponse)
def track_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "store/track.html",
        store_context(request, db, error=request.query_params.get("error")),
    )


@router.post("/track")
def track_lookup(
    request: Request,
    order_number: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    order = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.order_number == order_number.strip())
        .first()
    )
    if not order or order.email.lower() != email.strip().lower():
        return RedirectResponse("/track?error=1", status_code=303)
    return RedirectResponse(f"/order/{order.order_number}", status_code=303)


# ── Invoice ──────────────────────────────────────────────────────────────────

@router.get("/order/{order_number}/invoice", response_class=HTMLResponse)
def order_invoice(order_number: str, request: Request, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.order_number == order_number)
        .first()
    )
    if not order:
        return RedirectResponse("/", status_code=302)
    user = get_current_user(request, db)
    # guest: csak ha sessionban van recent order, vagy user sajátja
    if user and user.id == order.customer_id:
        pass
    elif request.session.get("last_order") == order.order_number:
        pass
    elif user and (user.is_admin or user.role in ("admin", "worker")):
        pass
    else:
        # email query token egyszerű: ?email=
        email = request.query_params.get("email", "")
        if email.lower() != order.email.lower():
            return RedirectResponse(f"/track?error=1", status_code=303)
    store = get_store_settings(db)
    return templates.TemplateResponse(
        "store/invoice.html",
        store_context(request, db, order=order, store=store),
    )


# ── Wishlist ─────────────────────────────────────────────────────────────────

@router.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    sk = get_session_key(request)
    if user:
        items = db.query(WishlistItem).filter(WishlistItem.user_id == user.id).all()
    else:
        items = (
            db.query(WishlistItem)
            .filter(WishlistItem.session_key == sk, WishlistItem.user_id.is_(None))
            .all()
        )
    products = []
    for it in items:
        p = db.get(Product, it.product_id)
        if p and p.active:
            products.append(p)
    return templates.TemplateResponse(
        "store/wishlist.html",
        store_context(request, db, products=products),
    )


@router.post("/wishlist/add")
def wishlist_add(request: Request, product_id: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    sk = get_session_key(request)
    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse("/", status_code=303)
    existing = None
    if user:
        existing = (
            db.query(WishlistItem)
            .filter(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id)
            .first()
        )
    else:
        existing = (
            db.query(WishlistItem)
            .filter(
                WishlistItem.session_key == sk,
                WishlistItem.user_id.is_(None),
                WishlistItem.product_id == product_id,
            )
            .first()
        )
    if not existing:
        db.add(
            WishlistItem(
                user_id=user.id if user else None,
                session_key=sk if not user else "",
                product_id=product_id,
            )
        )
        db.commit()
    return RedirectResponse(request.headers.get("referer") or "/wishlist", status_code=303)


@router.post("/wishlist/remove")
def wishlist_remove(request: Request, product_id: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    sk = get_session_key(request)
    q = db.query(WishlistItem).filter(WishlistItem.product_id == product_id)
    if user:
        q = q.filter(WishlistItem.user_id == user.id)
    else:
        q = q.filter(WishlistItem.session_key == sk)
    for row in q.all():
        db.delete(row)
    db.commit()
    return RedirectResponse("/wishlist", status_code=303)


# ── Returns ──────────────────────────────────────────────────────────────────

@router.get("/returns", response_class=HTMLResponse)
def returns_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "store/returns.html",
        store_context(request, db, ok=request.query_params.get("ok"), error=request.query_params.get("error")),
    )


@router.post("/returns")
def returns_submit(
    request: Request,
    order_number: str = Form(...),
    email: str = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.order_number == order_number.strip()).first()
    if not order or order.email.lower() != email.strip().lower():
        return RedirectResponse("/returns?error=1", status_code=303)
    db.add(
        ReturnRequest(
            order_id=order.id,
            email=email.strip(),
            reason=reason.strip()[:4000],
            status="requested",
        )
    )
    db.commit()
    return RedirectResponse("/returns?ok=1", status_code=303)


# ── Reviews ──────────────────────────────────────────────────────────────────

@router.post("/p/{slug}/review")
def product_review(
    slug: str,
    request: Request,
    rating: int = Form(5),
    title: str = Form(""),
    body: str = Form(""),
    author_name: str = Form(""),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.slug == slug, Product.active.is_(True)).first()
    if not product:
        return RedirectResponse("/", status_code=303)
    user = get_current_user(request, db)
    rating = max(1, min(5, int(rating)))
    db.add(
        ProductReview(
            product_id=product.id,
            user_id=user.id if user else None,
            author_name=(author_name or (user.full_name if user else "Vásárló")).strip()[:128],
            rating=rating,
            title=title.strip()[:255],
            body=body.strip()[:4000],
            approved=True,
        )
    )
    db.commit()
    return RedirectResponse(f"/p/{slug}#reviews", status_code=303)


# ── Stock alert ──────────────────────────────────────────────────────────────

@router.post("/p/{slug}/stock-alert")
def stock_alert(
    slug: str,
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        return RedirectResponse("/", status_code=303)
    email = email.strip().lower()
    existing = (
        db.query(StockAlert)
        .filter(StockAlert.product_id == product.id, StockAlert.email == email)
        .first()
    )
    if not existing:
        db.add(StockAlert(product_id=product.id, email=email))
        db.commit()
    return RedirectResponse(f"/p/{slug}?alert=1", status_code=303)
