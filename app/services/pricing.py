from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Coupon, Product, Promotion


def _active_window(obj, now: datetime) -> bool:
    if obj.starts_at and now < obj.starts_at:
        return False
    if obj.ends_at and now > obj.ends_at:
        return False
    return True


def active_promotions(db: Session) -> list[Promotion]:
    now = datetime.utcnow()
    return [
        p
        for p in db.query(Promotion).filter(Promotion.active.is_(True)).all()
        if _active_window(p, now)
    ]


def promo_discount_for_product(db: Session, product: Product, unit_price: float) -> tuple[float, Promotion | None]:
    """Return (discounted_unit_price, promo). Best discount wins."""
    best_price = unit_price
    best_promo = None
    for promo in active_promotions(db):
        product_ids = {int(x) for x in promo.product_ids.split(",") if x.strip().isdigit()}
        category_ids = {int(x) for x in promo.category_ids.split(",") if x.strip().isdigit()}
        if product_ids and product.id not in product_ids:
            continue
        if category_ids and (product.category_id not in category_ids):
            continue
        if promo.promo_type == "percent":
            price = unit_price * (1 - promo.value / 100.0)
        else:
            price = max(0.0, unit_price - promo.value)
        if price < best_price:
            best_price = price
            best_promo = promo
    return round(best_price, 2), best_promo


def find_coupon(db: Session, code: str) -> Coupon | None:
    if not code:
        return None
    coupon = db.query(Coupon).filter(Coupon.code == code.strip().upper()).first()
    if not coupon or not coupon.active:
        return None
    now = datetime.utcnow()
    if not _active_window(coupon, now):
        return None
    if coupon.max_uses and coupon.used_count >= coupon.max_uses:
        return None
    return coupon


def apply_coupon(subtotal: float, coupon: Coupon | None) -> tuple[float, bool]:
    """Return (discount_amount, free_shipping_flag)."""
    if not coupon:
        return 0.0, False
    if subtotal < coupon.min_order:
        return 0.0, False
    if coupon.coupon_type == "percent":
        return round(subtotal * coupon.value / 100.0, 2), False
    if coupon.coupon_type == "fixed":
        return round(min(subtotal, coupon.value), 2), False
    if coupon.coupon_type == "free_shipping":
        return 0.0, True
    return 0.0, False
