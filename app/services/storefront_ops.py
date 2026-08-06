"""Storefront ops: announcement, social ticker, free-ship progress, pending orders."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Campaign, Offer, Order, OrderLine, Product, StoreSettings
from app.services.merchandising import active_campaigns
from app.services.store_settings import get_store_settings

STATUS_OPEN = "open"
STATUS_CATALOG_ONLY = "catalog_only"
STATUS_CLOSED = "closed"
VALID_STATUSES = (STATUS_OPEN, STATUS_CATALOG_ONLY, STATUS_CLOSED)


def get_storefront_status(store: StoreSettings | None) -> str:
    if not store:
        return STATUS_OPEN
    status = (getattr(store, "storefront_status", None) or "").strip()
    if status in VALID_STATUSES:
        return status
    # legacy: csak maintenance_mode flag
    if getattr(store, "maintenance_mode", False):
        return STATUS_CLOSED
    return STATUS_OPEN


def set_storefront_status(store: StoreSettings, status: str) -> None:
    if status not in VALID_STATUSES:
        status = STATUS_OPEN
    store.storefront_status = status
    store.maintenance_mode = status == STATUS_CLOSED


def orders_enabled(store: StoreSettings | None) -> bool:
    return get_storefront_status(store) == STATUS_OPEN


def storefront_is_closed(store: StoreSettings | None) -> bool:
    return get_storefront_status(store) == STATUS_CLOSED


def announcement_active(store: StoreSettings | None) -> bool:
    if not store or not store.announcement_enabled:
        return False
    text = (store.announcement_text or "").strip()
    if not text:
        return False
    now = datetime.utcnow()
    if store.announcement_starts_at and now < store.announcement_starts_at:
        return False
    if store.announcement_ends_at and now > store.announcement_ends_at:
        return False
    return True


def free_shipping_progress(store: StoreSettings | None, items_subtotal: float) -> dict:
    threshold = float(getattr(store, "free_shipping_threshold_huf", 25000) or 25000)
    sub = float(items_subtotal or 0)
    if threshold <= 0:
        return {"enabled": False, "threshold": 0, "remaining": 0, "percent": 100, "unlocked": True}
    remaining = max(0.0, threshold - sub)
    percent = min(100.0, round(100.0 * sub / threshold, 1)) if threshold else 100.0
    return {
        "enabled": True,
        "threshold": threshold,
        "remaining": remaining,
        "percent": percent,
        "unlocked": remaining <= 0,
    }


def pending_order_count(db: Session) -> int:
    return (
        db.query(Order)
        .filter(Order.status.in_(("pending", "paid", "partial")))
        .count()
    )


def _product_href(db: Session, *, offer_id: int | None = None, title: str = "", sku: str = "") -> str:
    """Resolve /p/{slug} from offer or title/sku fallback."""
    from urllib.parse import quote

    if offer_id:
        row = (
            db.query(Product.slug)
            .join(Offer, Offer.product_id == Product.id)
            .filter(Offer.id == offer_id, Product.active.is_(True))
            .first()
        )
        if row and row[0]:
            return f"/p/{row[0]}"
    if sku:
        row = (
            db.query(Product.slug)
            .join(Offer, Offer.product_id == Product.id)
            .filter(Offer.sku == sku, Product.active.is_(True))
            .first()
        )
        if row and row[0]:
            return f"/p/{row[0]}"
    title = (title or "").strip()
    if title:
        p = db.query(Product).filter(Product.active.is_(True), Product.title == title).first()
        if p:
            return f"/p/{p.slug}"
        p = (
            db.query(Product)
            .filter(Product.active.is_(True), Product.title.ilike(f"{title[:40]}%"))
            .order_by(Product.sold_count.desc())
            .first()
        )
        if p:
            return f"/p/{p.slug}"
        return f"/search?q={quote(title[:60])}"
    return "/taxonomy"


def _campaign_href(c: Campaign) -> str:
    url = (c.link_url or "").strip()
    if url:
        return url
    return f"/go/c/{c.id}"


def social_ticker_items(db: Session, *, limit: int = 12) -> list[dict]:
    """Futó szalag: friss vásárlások + havi bestseller + topbar kampányok (linkelve)."""
    items: list[dict] = []

    recent = (
        db.query(Order)
        .options(joinedload(Order.lines))
        .filter(Order.status.notin_(("cancelled",)))
        .order_by(Order.created_at.desc())
        .limit(8)
        .all()
    )
    for o in recent:
        if not o.lines:
            continue
        line = o.lines[0]
        title = line.product_title or "termék"
        city = (o.city or "Magyarország").split(",")[0][:32]
        href = _product_href(db, offer_id=line.offer_id, title=title, sku=line.sku or "")
        items.append(
            {
                "kind": "purchase",
                "text": f"{city} · valaki megvette: {title[:48]}",
                "href": href or "/taxonomy",
            }
        )

    since = datetime.utcnow() - timedelta(days=30)
    top = (
        db.query(
            OrderLine.product_title,
            func.sum(OrderLine.quantity).label("qty"),
            func.max(OrderLine.offer_id).label("offer_id"),
            func.max(OrderLine.sku).label("sku"),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .filter(Order.created_at >= since, Order.status.notin_(("cancelled",)))
        .group_by(OrderLine.product_title)
        .order_by(func.sum(OrderLine.quantity).desc())
        .limit(5)
        .all()
    )
    for title, qty, offer_id, sku in top:
        href = _product_href(db, offer_id=offer_id, title=title or "", sku=sku or "")
        items.append(
            {
                "kind": "bestseller",
                "text": f"Havi kedvenc · {(title or '')[:48]} ({int(qty)} db)",
                "href": href or "/taxonomy",
            }
        )

    if not top:
        for p in (
            db.query(Product)
            .filter(Product.active.is_(True), Product.sold_count > 0)
            .order_by(Product.sold_count.desc())
            .limit(3)
            .all()
        ):
            items.append(
                {
                    "kind": "bestseller",
                    "text": f"Kedvelt · {p.title[:48]}",
                    "href": f"/p/{p.slug}",
                }
            )

    for c in active_campaigns(db, "topbar")[:4]:
        label = c.badge or "Ajánlat"
        items.append(
            {
                "kind": "promo",
                "text": f"{label}: {c.title}" + (f" — {c.subtitle}" if c.subtitle else ""),
                "href": _campaign_href(c),
            }
        )

    # Always linkable fallback bestsellers if still thin
    if len(items) < 4:
        for p in (
            db.query(Product)
            .filter(Product.active.is_(True))
            .order_by(Product.sold_count.desc(), Product.id.desc())
            .limit(4)
            .all()
        ):
            items.append(
                {
                    "kind": "bestseller",
                    "text": f"Népszerű · {p.title[:48]}",
                    "href": f"/p/{p.slug}",
                }
            )

    return items[:limit]


def feeds_should_serve(db: Session) -> bool:
    store = get_store_settings(db)
    if storefront_is_closed(store):
        return False
    return bool(store.google_feed_enabled)
