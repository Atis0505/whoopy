"""Staging → publish: belső review után Product+Offer."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Category, Offer, Product, StagingListing, Supplier
from app.services.pricing_engine import compute_list_price


def _slugify(text: str, fallback: str = "termek") -> str:
    raw = (text or "").strip().lower()
    for a, b in (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ö", "o"),
        ("ő", "o"),
        ("ú", "u"),
        ("ü", "u"),
        ("ű", "u"),
    ):
        raw = raw.replace(a, b)
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")[:180]
    return slug or fallback


def find_or_create_product(db: Session, row: StagingListing) -> Product:
    product = None
    if row.gtin:
        product = db.query(Product).filter(Product.gtin == row.gtin).first()
    if product is None:
        base_slug = _slugify(row.title, fallback=row.sku or row.gtin or "termek")
        slug = base_slug
        i = 2
        while db.query(Product).filter(Product.slug == slug).first():
            slug = f"{base_slug}-{i}"
            i += 1
        cat_id = None
        if row.google_taxonomy_id:
            cat = db.query(Category).filter(Category.google_id == row.google_taxonomy_id).first()
            cat_id = cat.id if cat else None
        product = Product(
            slug=slug,
            title=row.title,
            description=row.description,
            brand=row.brand,
            gtin=row.gtin,
            image_url=row.image_url,
            ship_mode=row.ship_mode if row.ship_mode in ("combinable", "separate") else "combinable",
            category_id=cat_id,
            active=True,
        )
        db.add(product)
        db.flush()
    else:
        # frissítsük a master mezőket ha üresek
        if row.title and not product.title:
            product.title = row.title
        if row.image_url and not product.image_url:
            product.image_url = row.image_url
        if row.brand and not product.brand:
            product.brand = row.brand
    return product


def publish_staging(db: Session, staging_id: int) -> StagingListing:
    row = db.get(StagingListing, staging_id)
    if not row:
        raise ValueError("Staging sor nem található")
    if row.status == "published":
        return row
    supplier = db.get(Supplier, row.supplier_id)
    if not supplier:
        raise ValueError("Partner hiányzik")

    product = find_or_create_product(db, row)
    list_price = row.list_price
    if list_price <= 0 and row.cost_price > 0:
        list_price = compute_list_price(db, row.cost_price, product=product, supplier_id=row.supplier_id)
    if list_price <= 0:
        raise ValueError("Nincs érvényes listaár (állíts cost/list_price-t vagy pricing rule-t)")

    offer = (
        db.query(Offer)
        .filter(Offer.product_id == product.id, Offer.supplier_id == row.supplier_id)
        .first()
    )
    if offer:
        offer.sku = row.sku or offer.sku
        offer.price = list_price
        offer.cost_price = row.cost_price
        offer.stock = row.stock
        offer.lead_days = row.lead_days
        offer.active = True
    else:
        db.add(
            Offer(
                product_id=product.id,
                supplier_id=row.supplier_id,
                sku=row.sku,
                price=list_price,
                cost_price=row.cost_price,
                stock=row.stock,
                lead_days=row.lead_days,
                active=True,
            )
        )

    row.status = "published"
    row.published_product_id = product.id
    row.list_price = list_price
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def reject_staging(db: Session, staging_id: int, reason: str = "") -> StagingListing:
    row = db.get(StagingListing, staging_id)
    if not row:
        raise ValueError("Staging sor nem található")
    row.status = "rejected"
    row.reject_reason = reason.strip()
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
