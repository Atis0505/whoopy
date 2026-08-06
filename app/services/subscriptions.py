"""Ismétlődő / automatikus újrarendelés."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models import (
    Offer,
    Order,
    OrderLine,
    OrderShipment,
    Subscription,
    SubscriptionLine,
    User,
    Warehouse,
)
from app.services.customer_ux import new_access_token
from app.services.store_settings import get_store_settings
from app.services.vat import effective_vat_rate, split_gross

logger = logging.getLogger(__name__)

ALLOWED_INTERVALS = (7, 14, 30, 60, 90)


def create_subscription(
    db: Session,
    user: User,
    *,
    lines: list[tuple[int, int]],
    interval_days: int = 30,
    name: str = "Ismétlődő rendelés",
    email: str = "",
    full_name: str = "",
    phone: str = "",
    country: str = "HU",
    city: str = "",
    address: str = "",
    zip_code: str = "",
    payment_preference: str = "cod",
    start_in_days: int | None = None,
) -> Subscription:
    interval_days = int(interval_days)
    if interval_days not in ALLOWED_INTERVALS:
        interval_days = 30
    clean: list[tuple[int, int]] = []
    for offer_id, qty in lines:
        qty = max(1, int(qty))
        offer = db.get(Offer, offer_id)
        if not offer or not offer.active:
            continue
        clean.append((offer_id, qty))
    if not clean:
        raise ValueError("Nincs érvényes tétel az ismétléshez")

    start = datetime.utcnow() + timedelta(days=start_in_days if start_in_days is not None else interval_days)
    sub = Subscription(
        user_id=user.id,
        name=(name or "Ismétlődő rendelés")[:128],
        interval_days=interval_days,
        next_run_at=start,
        active=True,
        paused=False,
        email=(email or user.email)[:255],
        full_name=(full_name or user.full_name or "")[:255],
        phone=(phone or user.phone or "")[:64],
        country=(country or "HU").upper()[:2],
        city=city[:128],
        address=address[:255],
        zip_code=zip_code[:16],
        payment_preference=payment_preference if payment_preference in ("cod", "invoice", "prepaid") else "cod",
    )
    db.add(sub)
    db.flush()
    for offer_id, qty in clean:
        db.add(SubscriptionLine(subscription_id=sub.id, offer_id=offer_id, quantity=qty))
    db.commit()
    db.refresh(sub)
    return sub


def create_from_order(db: Session, user: User, order: Order, *, interval_days: int = 30) -> Subscription:
    lines: list[tuple[int, int]] = []
    for ln in order.lines:
        if ln.offer_id:
            lines.append((ln.offer_id, ln.quantity))
    return create_subscription(
        db,
        user,
        lines=lines,
        interval_days=interval_days,
        name=f"Ismétlés · {order.order_number}",
        email=order.email,
        full_name=order.full_name,
        phone=order.phone,
        country=order.country,
        city=order.city,
        address=order.address,
        zip_code=order.zip_code,
        payment_preference=order.payment_method if order.payment_method in ("cod", "invoice", "prepaid") else "cod",
    )


def _next_order_number(db: Session) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    count = db.query(Order).count() + 1
    return f"TM-SUB-{stamp}-{count:04d}"


def fulfill_subscription(db: Session, sub: Subscription) -> Order:
    """Létrehoz egy rendelést a sablonból, előrébb lépteti a next_run_at-et."""
    sub = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.lines)
            .joinedload(SubscriptionLine.offer)
            .joinedload(Offer.product),
            joinedload(Subscription.lines).joinedload(SubscriptionLine.offer).joinedload(Offer.supplier),
        )
        .filter(Subscription.id == sub.id)
        .first()
    )
    if not sub or not sub.active or sub.paused:
        raise ValueError("Az ismétlés nem aktív")
    if not sub.lines:
        raise ValueError("Üres ismétlés")

    store = get_store_settings(db)
    items_subtotal = 0.0
    prepared: list[tuple[Offer, int, float]] = []
    for line in sub.lines:
        offer = line.offer
        if not offer or not offer.active:
            raise ValueError(f"Ajánlat nem elérhető (#{line.offer_id})")
        if offer.stock < line.quantity:
            raise ValueError(f"Nincs készlet: {offer.product.title if offer.product else offer.sku}")
        prepared.append((offer, line.quantity, float(offer.price)))
        items_subtotal += float(offer.price) * line.quantity

    shipping = float(getattr(store, "pickup_fee_huf", 990) or 990)
    grand = round(items_subtotal + shipping, 2)
    rate, reverse = effective_vat_rate(
        country=sub.country or "HU",
        fallback=store.tax_rate_percent,
        is_b2b=False,
        buyer_vat_id="",
        seller_country=store.default_country or "HU",
    )
    if reverse:
        net, tax = grand, 0.0
    else:
        net, tax, _ = split_gross(grand, rate)

    wh = db.query(Warehouse).filter(Warehouse.is_default.is_(True), Warehouse.active.is_(True)).first()
    order = Order(
        order_number=_next_order_number(db),
        customer_id=sub.user_id,
        email=sub.email,
        full_name=sub.full_name,
        phone=sub.phone,
        country=sub.country or "HU",
        city=sub.city,
        address=sub.address,
        zip_code=sub.zip_code,
        status="pending",
        payment_method=sub.payment_preference or "cod",
        payment_status="pending",
        subtotal=items_subtotal,
        shipping_total=shipping,
        tax_rate_percent=rate,
        tax_total=tax,
        net_total=net,
        grand_total=grand,
        currency="HUF",
        lang="hu",
        notes=f"Automatikus újrarendelés #{sub.id}",
        access_token=new_access_token(),
    )
    db.add(order)
    db.flush()

    supplier_ids: set[int] = set()
    for offer, qty, unit in prepared:
        title = offer.product.title if offer.product else offer.sku
        supplier_name = offer.supplier.name if offer.supplier else str(offer.supplier_id)
        db.add(
            OrderLine(
                order_id=order.id,
                offer_id=offer.id,
                supplier_id=offer.supplier_id,
                product_title=title,
                supplier_name=supplier_name,
                sku=offer.sku,
                unit_price=unit,
                quantity=qty,
                line_total=round(unit * qty, 2),
                weight_kg=float(offer.product.weight_kg) if offer.product else 0,
                ship_mode=offer.product.ship_mode if offer.product else "combinable",
                variant_label=offer.variant_label or "",
            )
        )
        offer.stock -= qty
        if offer.product:
            offer.product.sold_count = (offer.product.sold_count or 0) + qty
        supplier_ids.add(offer.supplier_id)

    # egy szállítmány / első beszállító
    first = prepared[0][0]
    db.add(
        OrderShipment(
            order_id=order.id,
            supplier_id=first.supplier_id,
            supplier_name=first.supplier.name if first.supplier else "Whoopy",
            method="courier",
            payment_method=sub.payment_preference or "cod",
            rate_name="Ismétlődő rendelés",
            shipping_price=shipping,
            status="pending",
            warehouse_id=wh.id if wh else None,
        )
    )

    sub.last_order_id = order.id
    sub.last_error = ""
    sub.next_run_at = datetime.utcnow() + timedelta(days=max(1, sub.interval_days))
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    try:
        from app.services.webhooks import emit_order_event, load_order

        full = load_order(db, order.id)
        if full:
            emit_order_event(db, "order.created", full, extra={"subscription_id": sub.id})
    except Exception:
        logger.exception("subscription webhook failed")

    return order


def process_due_subscriptions(db: Session, *, limit: int = 50) -> dict:
    now = datetime.utcnow()
    due = (
        db.query(Subscription)
        .filter(
            Subscription.active.is_(True),
            Subscription.paused.is_(False),
            Subscription.next_run_at <= now,
        )
        .order_by(Subscription.next_run_at.asc())
        .limit(limit)
        .all()
    )
    ok = 0
    errors: list[str] = []
    for sub in due:
        try:
            fulfill_subscription(db, sub)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            sub.last_error = str(exc)[:512]
            # ne spamelje azonnal: +1 nap retry
            sub.next_run_at = now + timedelta(days=1)
            sub.updated_at = now
            db.commit()
            errors.append(f"#{sub.id}: {exc}")
            logger.warning("subscription %s failed: %s", sub.id, exc)
    return {"processed": ok, "failed": len(errors), "errors": errors}
