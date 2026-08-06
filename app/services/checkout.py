from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models import Cart, CartItem, Offer, Order, OrderLine, OrderShipment, User
from app.services.cart import clear_cart, quote_cart
from app.services.customer_ux import (
    earn_loyalty_points,
    find_gift_card,
    loyalty_tier_for,
    new_access_token,
)
from app.services.pricing import find_coupon, promo_discount_for_product
from app.services.store_settings import get_store_settings


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
    billing_same: bool = True,
    billing_full_name: str = "",
    billing_country: str = "",
    billing_city: str = "",
    billing_address: str = "",
    billing_zip: str = "",
    billing_tax_id: str = "",
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

    if (getattr(cart, "delivery_mode", "") or "courier") == "pickup":
        if not (getattr(cart, "pickup_point_id", "") or "").strip():
            raise ValueError("Válassz csomagpontot a kosárban")

    cart.country = country.upper()
    db.commit()

    quote = quote_cart(db, cart, country=country)
    payment_method = cart.payment_preference or "prepaid"
    if payment_method == "prepaid":
        status = "pending"
        payment_status = "awaiting"
    else:
        status = "pending"
        payment_status = "pending"

    store = get_store_settings(db)
    access = new_access_token()

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
        billing_same=billing_same,
        billing_full_name=(billing_full_name or full_name).strip() if not billing_same else "",
        billing_country=(billing_country or country).upper() if not billing_same else "",
        billing_city=(billing_city or city).strip() if not billing_same else "",
        billing_address=(billing_address or address).strip() if not billing_same else "",
        billing_zip=(billing_zip or zip_code).strip() if not billing_same else "",
        billing_tax_id=billing_tax_id.strip(),
        delivery_mode=getattr(cart, "delivery_mode", "courier") or "courier",
        pickup_provider=getattr(cart, "pickup_provider", "") or "",
        pickup_point_id=getattr(cart, "pickup_point_id", "") or "",
        pickup_point_label=getattr(cart, "pickup_point_label", "") or "",
        gift_card_code=getattr(cart, "gift_card_code", "") or "",
        gift_card_amount=getattr(quote, "gift_discount", 0) or 0,
        loyalty_points_redeemed=getattr(quote, "loyalty_points_used", 0) or 0,
        loyalty_discount=getattr(quote, "loyalty_discount", 0) or 0,
        loyalty_points_earned=earn_loyalty_points(
            quote.grand_total, float(getattr(store, "loyalty_earn_per_100", 1) or 1)
        ),
        access_token=access,
        status=status,
        payment_method=payment_method,
        payment_status=payment_status,
        payment_provider="none",
        payment_ref="",
        subtotal=quote.items_subtotal,
        discount_total=quote.discount_total + quote.gift_discount + quote.loyalty_discount,
        shipping_total=quote.shipping_total,
        cod_fee_total=quote.cod_fee_total,
        tax_rate_percent=getattr(quote, "tax_rate_percent", 27.0),
        tax_total=getattr(quote, "tax_total", 0.0),
        net_total=getattr(quote, "net_total", 0.0),
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
        title = offer.product.title
        if offer.variant_label:
            title = f"{title} ({offer.variant_label})"
        db.add(
            OrderLine(
                order_id=order.id,
                offer_id=offer.id,
                supplier_id=offer.supplier_id,
                product_title=title,
                supplier_name=offer.supplier.name,
                sku=offer.sku,
                unit_price=unit,
                quantity=item.quantity,
                line_total=line_total,
                weight_kg=offer.product.weight_kg * item.quantity,
                ship_mode=offer.product.ship_mode or "combinable",
                variant_label=offer.variant_label or "",
            )
        )
        offer.stock -= item.quantity
        offer.product.sold_count = (offer.product.sold_count or 0) + item.quantity

    for shipment in quote.shipments:
        sel = shipment.selected
        method = "pickup" if order.delivery_mode == "pickup" else (sel.method if sel else "courier")
        rate_name = order.pickup_point_label if order.delivery_mode == "pickup" else (sel.name if sel else "")
        db.add(
            OrderShipment(
                order_id=order.id,
                supplier_id=shipment.supplier_id,
                supplier_name=shipment.supplier_name,
                method=method,
                payment_method=sel.payment_method if sel else cart.payment_preference,
                rate_name=rate_name,
                weight_kg=shipment.weight_kg,
                shipping_price=(quote.shipping_total / max(1, len(quote.shipments)))
                if order.delivery_mode == "pickup"
                else (sel.shipping_price if sel else 0),
                cod_fee=sel.cod_fee if sel and order.delivery_mode != "pickup" else 0,
                package_count=sel.package_count if sel else 1,
                status="pending",
            )
        )

    if cart.coupon_code:
        coupon = find_coupon(db, cart.coupon_code)
        if coupon:
            coupon.used_count += 1

    if order.gift_card_code and order.gift_card_amount > 0:
        card = find_gift_card(db, order.gift_card_code)
        if card:
            card.balance = round(max(0.0, float(card.balance) - float(order.gift_card_amount)), 2)

    if customer_id and order.loyalty_points_redeemed:
        user = db.get(User, customer_id)
        if user:
            user.loyalty_points = max(0, int(user.loyalty_points or 0) - int(order.loyalty_points_redeemed))
            user.loyalty_tier = loyalty_tier_for(user.loyalty_points)

    # COD / számla: pontok azonnal; prepaid: fizetéskor
    if customer_id and payment_method != "prepaid" and order.loyalty_points_earned:
        user = db.get(User, customer_id)
        if user:
            user.loyalty_points = int(user.loyalty_points or 0) + int(order.loyalty_points_earned)
            user.loyalty_tier = loyalty_tier_for(user.loyalty_points)

    db.commit()
    clear_cart(db, cart)
    db.refresh(order)
    from app.services.webhooks import emit_order_event, load_order

    full = load_order(db, order.id) or order
    emit_order_event(db, "order.created", full)
    try:
        from app.services.email import order_confirmation_email

        order_confirmation_email(full)
    except Exception:
        pass
    return order
