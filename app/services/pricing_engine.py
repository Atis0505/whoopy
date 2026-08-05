"""Árazás + buy-box: melyik partner-ajánlat a default forrás / listaár."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.models import Offer, PricingRule, Product, Supplier


def apply_margin(cost: float, rule: PricingRule) -> float:
    if cost <= 0:
        return 0.0
    if rule.rule_type == "fixed_markup":
        price = cost + float(rule.value)
    else:
        # margin_percent: lista = cost * (1 + value/100)
        price = cost * (1.0 + float(rule.value) / 100.0)
    if rule.min_margin_percent > 0:
        min_price = cost * (1.0 + float(rule.min_margin_percent) / 100.0)
        price = max(price, min_price)
    return round(price, 0)


def pick_pricing_rule(db: Session, product: Product | None = None, supplier_id: int | None = None) -> PricingRule | None:
    rules = (
        db.query(PricingRule)
        .filter(PricingRule.active.is_(True), PricingRule.rule_type.in_(("margin_percent", "fixed_markup")))
        .order_by(PricingRule.priority.asc(), PricingRule.id.asc())
        .all()
    )
    for rule in rules:
        if rule.supplier_id and supplier_id and rule.supplier_id != supplier_id:
            continue
        if rule.supplier_id and not supplier_id:
            continue
        if rule.category_id and product and product.category_id != rule.category_id:
            continue
        if rule.category_id and product is None:
            continue
        return rule
    # generic rule without supplier/category
    for rule in rules:
        if not rule.supplier_id and not rule.category_id:
            return rule
    return None


def compute_list_price(db: Session, cost: float, product: Product | None = None, supplier_id: int | None = None) -> float:
    rule = pick_pricing_rule(db, product=product, supplier_id=supplier_id)
    if rule and cost > 0:
        return apply_margin(cost, rule)
    if cost > 0:
        return round(cost * 1.25, 0)  # default 25%
    return 0.0


def buybox_mode(db: Session) -> str:
    rule = (
        db.query(PricingRule)
        .filter(PricingRule.active.is_(True), PricingRule.rule_type == "buybox")
        .order_by(PricingRule.priority.asc())
        .first()
    )
    return (rule.buybox_mode if rule else "cheapest") or "cheapest"


def select_buybox_offer(db: Session, product: Product) -> Offer | None:
    """Vevői default ajánlat: cheapest | fastest | preferred_supplier / preferred_source."""
    offers = [o for o in (product.offers or []) if o.active and o.stock > 0]
    if not offers:
        offers = [o for o in (product.offers or []) if o.active]
    if not offers:
        return None

    preferred = [o for o in offers if o.preferred_source]
    if preferred:
        return min(preferred, key=lambda o: (o.price, o.lead_days))

    mode = buybox_mode(db)
    if mode == "fastest":
        return min(offers, key=lambda o: (o.lead_days, o.price))
    if mode == "preferred_supplier":
        pref_sup = (
            db.query(Supplier)
            .filter(Supplier.preferred.is_(True), Supplier.active.is_(True))
            .all()
        )
        ids = {s.id for s in pref_sup}
        pool = [o for o in offers if o.supplier_id in ids] or offers
        return min(pool, key=lambda o: (o.price, o.lead_days))
    # cheapest
    return min(offers, key=lambda o: (o.price, o.lead_days))


def load_product_with_offers(db: Session, product_id: int) -> Product | None:
    return (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.supplier))
        .filter(Product.id == product_id)
        .first()
    )
