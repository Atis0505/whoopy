from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models import Cart, CartItem, Coupon, Offer, Order, OrderLine, OrderShipment
from app.services.cart import clear_cart, quote_cart
from app.services.pricing import find_coupon, promo_discount_for_product


def _next_order_number(db: Session) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    count = db.query(Order).count() + 1
    return f"TM-{stamp}-{count:04d}"


def create_order_from_cart(
    db: Session,
    cart: Cart,
    *,
    email: str,
    full_name: str,
    phone: str,
    country: str,
    city: str,
    address: str,
    zip_code: str,
    notes: str = "",
    customer_id: int | None = None,
) -> Order:
    items = (
        db.query(CartItem)
        .options(
            joinedload(CartItem.offer).joinedload(Offer.product),
            joinedload(CartItem.offer).joinedload(Offer.supplier),
        )
        .filter(CartItem.cart_id == cart.id)
        .all()
    )
    if not items:
        raise ValueError("Cart is empty")

    for item in items:
        if not item.offer.active or item.offer.stock < item.quantity:
            raise ValueError(f"Insufficient stock for {item.offer.product.title}")

    cart.country = country.upper()
    db.commit()

    quote = quote_cart(db, cart, country=country)
    payment_method = cart.payment_preference or "prepaid"
    if payment_method == "prepaid":
        status = "pending"
        payment_status = "awaiting"
    else:
        # COD / számla — online fizetés nélkül
        status = "pending"
        payment_status = "pending"

    order = Order(
        order_number=_next_order_number(db),
        customer_id=customer_id,
        email=email.strip(),
        full_name=full_name.strip(),
        phone=phone.strip(),
        country=country.upper(),
        city=city.strip(),
        address=address.strip(),
        zip_code=zip_code.strip(),
        status=status,
        payment_method=payment_method,
        payment_status=payment_status,
        payment_provider="none",
        payment_ref="",
        subtotal=quote.items_subtotal,
        discount_total=quote.discount_total,
        shipping_total=quote.shipping_total,
        cod_fee_total=quote.cod_fee_total,
        grand_total=quote.grand_total,
        currency=cart.currency or "HUF",
        coupon_code=cart.coupon_code or "",
        lang=cart.lang or "hu",
        notes=notes.strip(),
    )
    db.add(order)
    db.flush()

    for item in items:
        offer = item.offer
        unit, _ = promo_discount_for_product(db, offer.product, offer.price)
        line_total = unit * item.quantity
        db.add(
            OrderLine(
                order_id=order.id,
                offer_id=offer.id,
                supplier_id=offer.supplier_id,
                product_title=offer.product.title,
                supplier_name=offer.supplier.name,
                sku=offer.sku,
                unit_price=unit,
                quantity=item.quantity,
                line_total=line_total,
                weight_kg=offer.product.weight_kg * item.quantity,
                ship_mode=offer.product.ship_mode or "combinable",
            )
        )
        offer.stock -= item.quantity
        offer.product.sold_count = (offer.product.sold_count or 0) + item.quantity

    for shipment in quote.shipments:
        sel = shipment.selected
        db.add(
            OrderShipment(
                order_id=order.id,
                supplier_id=shipment.supplier_id,
                supplier_name=shipment.supplier_name,
                method=sel.method if sel else "courier",
                payment_method=sel.payment_method if sel else cart.payment_preference,
                rate_name=sel.name if sel else "",
                weight_kg=shipment.weight_kg,
                shipping_price=sel.shipping_price if sel else 0,
                cod_fee=sel.cod_fee if sel else 0,
                package_count=sel.package_count if sel else 1,
                status="pending",
            )
        )

    if cart.coupon_code:
        coupon = find_coupon(db, cart.coupon_code)
        if coupon:
            coupon.used_count += 1

    db.commit()
    clear_cart(db, cart)
    db.refresh(order)
    return order
