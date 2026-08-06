"""Omnibus árarchívum + GDPR export/anonymize."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models import (
    NewsletterSubscriber,
    Order,
    PriceHistory,
    Product,
    ReturnRequest,
    StockAlert,
    User,
    WishlistItem,
)


def record_offer_price(db: Session, *, product_id: int, offer_id: int | None, price: float) -> None:
    db.add(
        PriceHistory(
            product_id=product_id,
            offer_id=offer_id,
            price=float(price),
            recorded_at=datetime.utcnow(),
        )
    )


def lowest_price_30d(db: Session, product_id: int) -> float | None:
    since = datetime.utcnow() - timedelta(days=30)
    row = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id, PriceHistory.recorded_at >= since)
        .order_by(PriceHistory.price.asc())
        .first()
    )
    return float(row.price) if row else None


def snapshot_active_prices(db: Session) -> int:
    """Napi/seed snapshot az aktív ajánlatokról."""
    from app.models import Offer

    n = 0
    offers = db.query(Offer).filter(Offer.active.is_(True)).all()
    for o in offers:
        record_offer_price(db, product_id=o.product_id, offer_id=o.id, price=o.price)
        n += 1
    db.commit()
    return n


def export_user_data(db: Session, user: User) -> dict:
    orders = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.customer_id == user.id)
        .all()
    )
    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "loyalty_points": user.loyalty_points,
            "loyalty_tier": user.loyalty_tier,
            "newsletter_opt_in": user.newsletter_opt_in,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "orders": [
            {
                "order_number": o.order_number,
                "status": o.status,
                "grand_total": o.grand_total,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "lines": [{"title": ln.product_title, "qty": ln.quantity, "total": ln.line_total} for ln in o.lines],
            }
            for o in orders
        ],
        "wishlist_product_ids": [
            w.product_id for w in db.query(WishlistItem).filter(WishlistItem.user_id == user.id).all()
        ],
    }


def anonymize_user(db: Session, user: User) -> None:
    uid = user.id
    email_old = user.email
    user.email = f"deleted+{uid}@anonymized.local"
    user.full_name = "Törölt felhasználó"
    user.phone = ""
    user.password_hash = "!"
    user.newsletter_opt_in = False
    user.loyalty_points = 0
    user.gdpr_anonymized_at = datetime.utcnow()
    for s in db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email_old).all():
        s.active = False
        s.email = f"deleted+{uid}@anonymized.local"
    for a in db.query(StockAlert).filter(StockAlert.email == email_old).all():
        a.email = f"deleted+{uid}@anonymized.local"
    db.query(WishlistItem).filter(WishlistItem.user_id == uid).delete()
    db.commit()
