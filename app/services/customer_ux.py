"""Vásárlói élmény segédek: keresés, compare, recently viewed, gift, loyalty, pickup, token."""

from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import GiftCard, PickupPoint, Product


def new_access_token() -> str:
    return secrets.token_urlsafe(24)


def search_products(db: Session, q: str, *, limit: int = 48) -> list[Product]:
    q = (q or "").strip()
    query = (
        db.query(Product)
        .options(joinedload(Product.offers), joinedload(Product.category))
        .filter(Product.active.is_(True))
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Product.title.ilike(like),
                Product.brand.ilike(like),
                Product.description.ilike(like),
                Product.gtin.ilike(like),
                Product.slug.ilike(like),
            )
        )
    return query.order_by(Product.sold_count.desc(), Product.title.asc()).limit(limit).all()


def suggest_products(db: Session, q: str, *, limit: int = 8) -> list[dict]:
    products = search_products(db, q, limit=limit)
    out = []
    for p in products:
        offers = [o for o in (p.offers or []) if o.active and o.stock > 0]
        price = min((o.price for o in offers), default=None)
        out.append(
            {
                "id": p.id,
                "slug": p.slug,
                "title": p.title,
                "brand": p.brand,
                "image_url": p.image_url,
                "price": price,
                "url": f"/p/{p.slug}",
            }
        )
    return out


def find_gift_card(db: Session, code: str) -> GiftCard | None:
    if not code:
        return None
    card = db.query(GiftCard).filter(GiftCard.code == code.strip().upper()).first()
    if not card or not card.active or card.balance <= 0:
        return None
    if card.expires_at and card.expires_at < datetime.utcnow():
        return None
    return card


def gift_discount(card: GiftCard | None, payable: float) -> float:
    if not card or payable <= 0:
        return 0.0
    return round(min(float(card.balance), payable), 2)


def loyalty_discount_amount(*, points: int, point_value: float, max_amount: float) -> tuple[int, float]:
    """Vissza: (felhasznált pont, kedvezmény HUF). Max a max_amount."""
    points = max(0, int(points or 0))
    if points <= 0 or point_value <= 0 or max_amount <= 0:
        return 0, 0.0
    value = points * float(point_value)
    if value > max_amount:
        points = int(max_amount / point_value)
        value = points * float(point_value)
    return points, round(value, 2)


def earn_loyalty_points(grand_total: float, earn_per_100: float) -> int:
    if grand_total <= 0 or earn_per_100 <= 0:
        return 0
    return int((grand_total / 100.0) * earn_per_100)


def loyalty_tier_for(points: int) -> str:
    if points >= 5000:
        return "gold"
    if points >= 1500:
        return "silver"
    return "standard"


def list_pickup_points(db: Session, *, provider: str = "", city: str = "", q: str = "", limit: int = 40) -> list[PickupPoint]:
    query = db.query(PickupPoint).filter(PickupPoint.active.is_(True))
    if provider:
        query = query.filter(PickupPoint.provider == provider.lower())
    if city:
        query = query.filter(PickupPoint.city.ilike(f"%{city.strip()}%"))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                PickupPoint.name.ilike(like),
                PickupPoint.address.ilike(like),
                PickupPoint.city.ilike(like),
                PickupPoint.zip_code.ilike(like),
                PickupPoint.external_id.ilike(like),
            )
        )
    return query.order_by(PickupPoint.city, PickupPoint.name).limit(limit).all()


def seed_pickup_and_gifts(db: Session) -> None:
    if db.query(PickupPoint).count() == 0:
        samples = [
            ("foxpost", "FP-BP-01", "Foxpost Automat – Nyugati", "Budapest", "1062", "Teréz krt. 55."),
            ("foxpost", "FP-BP-02", "Foxpost Automat – Corvin", "Budapest", "1082", "Futó u. 37."),
            ("foxpost", "FP-DEB-01", "Foxpost Automat – Debrecen Plaza", "Debrecen", "4026", "Csapó u. 30."),
            ("packeta", "PK-BP-11", "Packeta – Allee", "Budapest", "1117", "Október huszonharmadika u. 8."),
            ("packeta", "PK-SZE-01", "Packeta – Szeged", "Szeged", "6720", "Kárász u. 1."),
            ("gls", "GLS-BP-21", "GLS Csomagpont – Mammut", "Budapest", "1024", "Lövőház u. 2."),
            ("gls", "GLS-PEC-01", "GLS Csomagpont – Pécs", "Pécs", "7621", "Király u. 10."),
            ("gls", "GLS-GYOR-01", "GLS ParcelShop – Győr", "Győr", "9021", "Árpád út 5."),
        ]
        for provider, eid, name, city, zip_c, addr in samples:
            db.add(
                PickupPoint(
                    provider=provider,
                    external_id=eid,
                    name=name,
                    city=city,
                    zip_code=zip_c,
                    address=addr,
                    country="HU",
                )
            )
    if db.query(GiftCard).count() == 0:
        db.add(GiftCard(code="WHOOPY5K", initial_amount=5000, balance=5000))
        db.add(GiftCard(code="AJANDEK10K", initial_amount=10000, balance=10000))
    db.commit()


# Session helpers (compare / recently viewed)

def session_list_ids(session: dict, key: str) -> list[int]:
    raw = session.get(key) or []
    out: list[int] = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def push_recent_product(session: dict, product_id: int, *, max_n: int = 12) -> None:
    ids = [product_id] + [i for i in session_list_ids(session, "recent_products") if i != product_id]
    session["recent_products"] = ids[:max_n]


def toggle_compare(session: dict, product_id: int, *, max_n: int = 4) -> list[int]:
    ids = session_list_ids(session, "compare_ids")
    if product_id in ids:
        ids = [i for i in ids if i != product_id]
    else:
        if len(ids) >= max_n:
            ids = ids[1:] + [product_id]
        else:
            ids.append(product_id)
    session["compare_ids"] = ids
    return ids
