"""Omnibus árarchívum + GDPR export/anonymize."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models import (
    NewsletterSubscriber,
    Offer,
    Order,
    PriceHistory,
    Product,
    StockAlert,
    User,
    WishlistItem,
)


def record_offer_price(
    db: Session,
    *,
    product_id: int,
    offer_id: int | None,
    price: float,
    previous_price: float | None = None,
    source: str = "system",
) -> None:
    db.add(
        PriceHistory(
            product_id=product_id,
            offer_id=offer_id,
            price=float(price),
            previous_price=float(previous_price) if previous_price is not None else None,
            source=(source or "system")[:64],
            recorded_at=datetime.utcnow(),
        )
    )


def set_offer_price(
    db: Session,
    offer: Offer,
    new_price: float,
    *,
    source: str = "api",
    commit: bool = False,
) -> bool:
    """Ár módosítás + PriceHistory csak ha tényleg változott. True = változott."""
    new_price = float(new_price)
    old = float(offer.price or 0)
    if abs(old - new_price) < 0.0001:
        return False
    offer.price = new_price
    record_offer_price(
        db,
        product_id=offer.product_id,
        offer_id=offer.id,
        price=new_price,
        previous_price=old,
        source=source,
    )
    if commit:
        db.commit()
    return True


def lowest_price_30d(db: Session, product_id: int) -> float | None:
    since = datetime.utcnow() - timedelta(days=30)
    row = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id, PriceHistory.recorded_at >= since)
        .order_by(PriceHistory.price.asc())
        .first()
    )
    return float(row.price) if row else None


def price_history_rows(db: Session, *, product_id: int | None = None, limit: int = 100) -> list[PriceHistory]:
    q = db.query(PriceHistory)
    if product_id:
        q = q.filter(PriceHistory.product_id == product_id)
    return q.order_by(PriceHistory.recorded_at.desc(), PriceHistory.id.desc()).limit(limit).all()


def omnibus_discount_ok(db: Session, product_id: int, promo_price: float) -> dict:
    """
    Omnibus ellenőrzés a *jelenlegi* 30 napos archív alapján (még a promo mentése előtt hívd).
    Valódi kedvezmény: promo < 30 napos legalacsonyabb.
    """
    lowest = lowest_price_30d(db, product_id)
    promo_price = float(promo_price)
    if lowest is None:
        return {"ok": True, "lowest_30d": None, "promo_price": promo_price, "note": "nincs 30 napos archiv"}
    ok = promo_price < lowest
    return {
        "ok": ok,
        "lowest_30d": lowest,
        "promo_price": promo_price,
        "note": (
            "OK — akciós ár a 30 napos minimum alatt"
            if ok
            else "Figyelem: az akciós ár nem alacsonyabb a 30 napos legalacsonyabbnál (Omnibus)"
        ),
    }


def snapshot_active_prices(db: Session) -> int:
    """Napi/seed snapshot az aktív ajánlatokról."""
    n = 0
    offers = db.query(Offer).filter(Offer.active.is_(True)).all()
    for o in offers:
        # ne duplázzuk ha az utolsó bejegyzés ugyanaz
        last = (
            db.query(PriceHistory)
            .filter(PriceHistory.offer_id == o.id)
            .order_by(PriceHistory.id.desc())
            .first()
        )
        if last and abs(float(last.price) - float(o.price)) < 0.0001:
            continue
        record_offer_price(
            db,
            product_id=o.product_id,
            offer_id=o.id,
            price=o.price,
            previous_price=float(last.price) if last else None,
            source="snapshot",
        )
        n += 1
    db.commit()
    return n


def export_user_data(db: Session, user: User) -> dict:
    from datetime import datetime as dt

    orders = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.customer_id == user.id)
        .all()
    )
    return {
        "exported_at": dt.utcnow().isoformat() + "Z",
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
    from datetime import datetime as dt

    from app.models import Subscription

    uid = user.id
    email_old = user.email
    user.email = f"deleted+{uid}@anonymized.local"
    user.full_name = "Törölt felhasználó"
    user.phone = ""
    user.password_hash = "!"
    user.newsletter_opt_in = False
    user.loyalty_points = 0
    user.gdpr_anonymized_at = dt.utcnow()
    for s in db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email_old).all():
        s.active = False
        s.email = f"deleted+{uid}@anonymized.local"
    for a in db.query(StockAlert).filter(StockAlert.email == email_old).all():
        a.email = f"deleted+{uid}@anonymized.local"
    for sub in db.query(Subscription).filter(Subscription.user_id == uid).all():
        sub.active = False
        sub.paused = True
    db.query(WishlistItem).filter(WishlistItem.user_id == uid).delete()
    db.commit()
