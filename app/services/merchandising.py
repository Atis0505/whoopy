from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Campaign, Product


def active_campaigns(db: Session, placement: str | None = None) -> list[Campaign]:
    now = datetime.utcnow()
    q = db.query(Campaign).filter(Campaign.active.is_(True))
    if placement:
        q = q.filter(Campaign.placement == placement)
    rows = q.order_by(Campaign.sort_order, Campaign.id).all()
    out = []
    for c in rows:
        if c.starts_at and now < c.starts_at:
            continue
        if c.ends_at and now > c.ends_at:
            continue
        out.append(c)
    return out


def hero_for_session(db: Session, session: dict) -> list[Campaign]:
    from app.services.attribution import bump_campaign_impression, pick_hero_campaigns

    heroes = active_campaigns(db, "hero")
    picked = pick_hero_campaigns(heroes, session)
    if picked:
        bump_campaign_impression(db, picked[0])
    return picked


def bestsellers(db: Session, limit: int = 8) -> list[Product]:
    return (
        db.query(Product)
        .filter(Product.active.is_(True), Product.sold_count > 0)
        .order_by(Product.sold_count.desc(), Product.id.desc())
        .limit(limit)
        .all()
    )


def showcase_products(db: Session, limit: int = 14) -> list[Product]:
    """Főoldali váltakozó termékképes sáv — képes, aktív termékek."""
    q = (
        db.query(Product)
        .filter(
            Product.active.is_(True),
            Product.image_url != "",
            Product.image_url.isnot(None),
        )
        .order_by(Product.sold_count.desc(), Product.created_at.desc())
        .limit(limit)
    )
    rows = q.all()
    if len(rows) < 6:
        # kevés bestseller → egészítsük fel bármilyen képes termékkel
        have = {p.id for p in rows}
        extra = (
            db.query(Product)
            .filter(
                Product.active.is_(True),
                Product.image_url != "",
                ~Product.id.in_(have or [-1]),
            )
            .order_by(Product.id.desc())
            .limit(max(0, limit - len(rows)))
            .all()
        )
        rows = rows + extra
    return rows
