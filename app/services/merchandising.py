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


def bestsellers(db: Session, limit: int = 8) -> list[Product]:
    return (
        db.query(Product)
        .filter(Product.active.is_(True), Product.sold_count > 0)
        .order_by(Product.sold_count.desc(), Product.id.desc())
        .limit(limit)
        .all()
    )
