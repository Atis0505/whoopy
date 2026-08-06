from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models import Cart, CartItem, Offer, ShippingRate
from app.services.pricing import apply_coupon, find_coupon, promo_discount_for_product


@dataclass
class ShippingOptionQuote:
    rate_id: int
    name: str
    method: str
    payment_method: str
    shipping_price: float
    cod_fee: float
    package_count: int
    free_shipping_applied: bool = False


@dataclass
class ShipmentQuote:
    supplier_id: int
    supplier_name: str
    weight_kg: float
    items_subtotal: float
    combinable_weight: float
    separate_units: int
    options: list[ShippingOptionQuote] = field(default_factory=list)
    selected: Optional[ShippingOptionQuote] = None


@dataclass
class CartQuote:
    items_subtotal: float = 0.0
    discount_total: float = 0.0
    shipping_total: float = 0.0
    cod_fee_total: float = 0.0
    grand_total: float = 0.0
    tax_rate_percent: float = 27.0
    tax_total: float = 0.0
    net_total: float = 0.0
    shipments: list[ShipmentQuote] = field(default_factory=list)
    item_count: int = 0
    currency: str = "HUF"
    coupon_code: str = ""
    free_shipping_coupon: bool = False
    payment_preference: str = "prepaid"


def get_or_create_cart(db: Session, session_key: str, country: str = "HU") -> Cart:
    cart = db.query(Cart).filter(Cart.session_key == session_key).first()
    if cart is None:
        cart = Cart(session_key=session_key, country=country)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def add_to_cart(db: Session, cart: Cart, offer_id: int, quantity: int = 1) -> CartItem:
    offer = db.query(Offer).filter(Offer.id == offer_id, Offer.active.is_(True)).first()
    if offer is None:
        raise ValueError("Offer not found or inactive")
    if quantity < 1:
        raise ValueError("Quantity must be >= 1")
    if offer.stock < quantity:
        raise ValueError("Not enough stock")

    item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.offer_id == offer_id)
        .first()
    )
    if item:
        new_qty = item.quantity + quantity
        if offer.stock < new_qty:
            raise ValueError("Not enough stock")
        item.quantity = new_qty
    else:
        item = CartItem(cart_id=cart.id, offer_id=offer_id, quantity=quantity)
        db.add(item)
    cart.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def update_cart_item(db: Session, cart: Cart, item_id: int, quantity: int) -> None:
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if item is None:
        raise ValueError("Cart item not found")
    if quantity <= 0:
        db.delete(item)
    else:
        if item.offer.stock < quantity:
            raise ValueError("Not enough stock")
        item.quantity = quantity
    cart.updated_at = datetime.utcnow()
    db.commit()


def clear_cart(db: Session, cart: Cart) -> None:
    for item in list(cart.items):
        db.delete(item)
    cart.coupon_code = ""
    cart.shipping_choices = ""
    db.commit()


def parse_shipping_choices(raw: str) -> dict[int, int]:
    """supplier_id -> rate_id"""
    out: dict[int, int] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        a, b = part.split(":", 1)
        if a.isdigit() and b.isdigit():
            out[int(a)] = int(b)
    return out


def serialize_shipping_choices(choices: dict[int, int]) -> str:
    return ",".join(f"{sid}:{rid}" for sid, rid in sorted(choices.items()))


def _calc_option_price(
    rate: ShippingRate,
    *,
    combinable_weight: float,
    separate_units: int,
    items_subtotal: float,
    free_shipping_coupon: bool,
) -> tuple[float, float, int, bool]:
    """Returns shipping_price, cod_fee, package_count, free_applied."""
    package_count = (1 if combinable_weight > 0 else 0) + separate_units

    # Combined parcel must fit weight band; separate units use per-unit fee regardless of band.
    if combinable_weight > 0 and not (rate.min_weight_kg <= combinable_weight <= rate.max_weight_kg):
        if separate_units == 0:
            return -1, 0, package_count, False
        # only charge separate part
        combinable_charge = 0.0
    elif combinable_weight > 0:
        combinable_charge = rate.price
    else:
        combinable_charge = 0.0

    per_sep = rate.price_per_separate_unit if rate.price_per_separate_unit > 0 else rate.price
    shipping = combinable_charge + per_sep * separate_units

    free_applied = False
    if free_shipping_coupon or (rate.free_above is not None and items_subtotal >= rate.free_above):
        shipping = 0.0
        free_applied = True

    cod_fee = 0.0
    if rate.payment_method == "cod" or (rate.payment_method == "any" and rate.cod_fee):
        cod_fee = rate.cod_fee

    return round(shipping, 2), round(cod_fee, 2), max(package_count, 1), free_applied


def _rate_matches_payment(rate: ShippingRate, payment_preference: str) -> bool:
    if rate.payment_method == "any":
        return True
    return rate.payment_method == payment_preference


def quote_cart(db: Session, cart: Cart, country: str | None = None) -> CartQuote:
    country = (country or cart.country or "HU").upper()
    payment_pref = cart.payment_preference or "prepaid"
    items = (
        db.query(CartItem)
        .options(
            joinedload(CartItem.offer).joinedload(Offer.product),
            joinedload(CartItem.offer).joinedload(Offer.supplier),
        )
        .filter(CartItem.cart_id == cart.id)
        .all()
    )

    quote = CartQuote(
        currency=cart.currency or "HUF",
        coupon_code=cart.coupon_code or "",
        payment_preference=payment_pref,
    )
    if not items:
        return quote

    coupon = find_coupon(db, cart.coupon_code)
    line_subtotal = 0.0
    groups: dict[int, list[CartItem]] = defaultdict(list)

    for item in items:
        unit, _promo = promo_discount_for_product(db, item.offer.product, item.offer.price)
        line_subtotal += unit * item.quantity
        quote.item_count += item.quantity
        groups[item.offer.supplier_id].append(item)

    discount, free_ship_coupon = apply_coupon(line_subtotal, coupon)
    quote.items_subtotal = round(line_subtotal, 2)
    quote.discount_total = discount
    quote.free_shipping_coupon = free_ship_coupon

    choices = parse_shipping_choices(cart.shipping_choices)
    after_discount_ratio = 1.0
    if line_subtotal > 0 and discount > 0:
        after_discount_ratio = max(0.0, (line_subtotal - discount) / line_subtotal)

    for supplier_id, group_items in groups.items():
        supplier = group_items[0].offer.supplier
        combinable_weight = 0.0
        separate_units = 0
        group_subtotal = 0.0
        for item in group_items:
            unit, _ = promo_discount_for_product(db, item.offer.product, item.offer.price)
            group_subtotal += unit * item.quantity
            mode = item.offer.product.ship_mode or "combinable"
            if mode == "separate":
                separate_units += item.quantity
            else:
                combinable_weight += item.offer.product.weight_kg * item.quantity

        group_subtotal_adj = round(group_subtotal * after_discount_ratio, 2)
        rates = (
            db.query(ShippingRate)
            .filter(
                ShippingRate.supplier_id == supplier_id,
                ShippingRate.country == country,
                ShippingRate.active.is_(True),
            )
            .order_by(ShippingRate.sort_order, ShippingRate.price)
            .all()
        )

        options: list[ShippingOptionQuote] = []
        for rate in rates:
            if not _rate_matches_payment(rate, payment_pref):
                # still show COD options when browsing prepaid? show all, filter softly
                pass
            ship_price, cod_fee, pkgs, free_applied = _calc_option_price(
                rate,
                combinable_weight=combinable_weight,
                separate_units=separate_units,
                items_subtotal=group_subtotal_adj,
                free_shipping_coupon=free_ship_coupon,
            )
            if ship_price < 0:
                continue
            # If payment preference is prepaid, hide pure COD options from default list but keep them visible
            options.append(
                ShippingOptionQuote(
                    rate_id=rate.id,
                    name=rate.name,
                    method=rate.method,
                    payment_method=rate.payment_method,
                    shipping_price=ship_price,
                    cod_fee=cod_fee if (payment_pref == "cod" or rate.payment_method == "cod") else (
                        cod_fee if rate.payment_method == "cod" else 0.0
                    ),
                    package_count=pkgs,
                    free_shipping_applied=free_applied,
                )
            )

        # Fallback option
        if not options:
            fallback_price = 1990.0 + separate_units * 4990.0
            if free_ship_coupon:
                fallback_price = 0.0
            options.append(
                ShippingOptionQuote(
                    rate_id=0,
                    name="Fallback",
                    method="courier",
                    payment_method="any",
                    shipping_price=fallback_price,
                    cod_fee=0.0,
                    package_count=1 + separate_units,
                )
            )

        selected = None
        if supplier_id in choices:
            selected = next((o for o in options if o.rate_id == choices[supplier_id]), None)
        if selected is None:
            # prefer matching payment method, else cheapest total
            matching = [o for o in options if o.payment_method in (payment_pref, "any")]
            pool = matching or options
            selected = min(pool, key=lambda o: o.shipping_price + o.cod_fee)

        shipment = ShipmentQuote(
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            weight_kg=round(combinable_weight, 3),
            items_subtotal=round(group_subtotal, 2),
            combinable_weight=round(combinable_weight, 3),
            separate_units=separate_units,
            options=options,
            selected=selected,
        )
        quote.shipments.append(shipment)
        if selected:
            quote.shipping_total += selected.shipping_price
            if payment_pref == "cod" or selected.payment_method == "cod":
                quote.cod_fee_total += selected.cod_fee

    quote.shipping_total = round(quote.shipping_total, 2)
    quote.cod_fee_total = round(quote.cod_fee_total, 2)
    quote.grand_total = round(
        quote.items_subtotal - quote.discount_total + quote.shipping_total + quote.cod_fee_total,
        2,
    )
    from app.services.store_settings import get_store_settings
    from app.services.vat import split_gross, vat_rate_for_country

    store = get_store_settings(db)
    quote.tax_rate_percent = vat_rate_for_country(country or cart.country, store.tax_rate_percent)
    quote.net_total, quote.tax_total, _ = split_gross(quote.grand_total, quote.tax_rate_percent)
    return quote
