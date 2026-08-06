"""Storefront ops: announcement, social ticker, free-ship progress, pending orders."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Campaign, Order, OrderLine, Product, StoreSettings
from app.services.merchandising import active_campaigns
from app.services.store_settings import get_store_settings


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


def social_ticker_items(db: Session, *, limit: int = 12) -> list[dict]:
    """Futó szalag: friss vásárlások + havi bestseller + topbar kampányok."""
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
        title = o.lines[0].product_title if o.lines else "termék"
        city = (o.city or "Magyarország").split(",")[0][:32]
        items.append(
            {
                "kind": "purchase",
                "text": f"{city} · valaki megvette: {title[:48]}",
            }
        )

    since = datetime.utcnow() - timedelta(days=30)
    top = (
        db.query(OrderLine.product_title, func.sum(OrderLine.quantity).label("qty"))
        .join(Order, Order.id == OrderLine.order_id)
        .filter(Order.created_at >= since, Order.status.notin_(("cancelled",)))
        .group_by(OrderLine.product_title)
        .order_by(func.sum(OrderLine.quantity).desc())
        .limit(5)
        .all()
    )
    for title, qty in top:
        items.append(
            {
                "kind": "bestseller",
                "text": f"Havi kedvenc · {title[:48]} ({int(qty)} db)",
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
                }
            )

    for c in active_campaigns(db, "topbar")[:4]:
        label = c.badge or "Ajánlat"
        items.append(
            {
                "kind": "promo",
                "text": f"{label}: {c.title}" + (f" — {c.subtitle}" if c.subtitle else ""),
                "href": c.link_url or f"/go/c/{c.id}",
            }
        )

    return items[:limit]


def feeds_should_serve(db: Session) -> bool:
    store = get_store_settings(db)
    if store.maintenance_mode:
        return False
    return bool(store.google_feed_enabled)
