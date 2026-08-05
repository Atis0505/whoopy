"""GTIN alapú master deduplikáció — ajánlatok összevonása egy termékre."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.models import Offer, Product


def find_gtin_duplicates(db: Session) -> list[dict]:
    products = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.gtin != "", Product.gtin.isnot(None))
        .all()
    )
    by_gtin: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        g = (p.gtin or "").strip()
        if g:
            by_gtin[g].append(p)
    dupes = []
    for gtin, group in by_gtin.items():
        if len(group) < 2:
            continue
        dupes.append(
            {
                "gtin": gtin,
                "products": [
                    {
                        "id": p.id,
                        "slug": p.slug,
                        "title": p.title,
                        "offers": len(p.offers or []),
                        "active": p.active,
                    }
                    for p in group
                ],
            }
        )
    return dupes


def merge_products_by_gtin(db: Session, gtin: str, keep_product_id: int | None = None) -> Product:
    """Összes ugyanarra a GTIN-re mutató termék offerjeit a keep termékre rakja, többit deaktiválja."""
    gtin = (gtin or "").strip()
    group = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.gtin == gtin)
        .order_by(Product.id.asc())
        .all()
    )
    if len(group) < 2:
        raise ValueError("Nincs elég duplikátum ehhez a GTIN-hez")
    keep = next((p for p in group if p.id == keep_product_id), None) or group[0]
    for other in group:
        if other.id == keep.id:
            continue
        for offer in list(other.offers or []):
            existing = (
                db.query(Offer)
                .filter(Offer.product_id == keep.id, Offer.supplier_id == offer.supplier_id)
                .first()
            )
            if existing:
                # tartsuk a jobb (olcsóbb aktív) árat / nagyobb stockot
                if offer.active and offer.price < existing.price:
                    existing.price = offer.price
                    existing.cost_price = offer.cost_price
                existing.stock = max(existing.stock, offer.stock)
                existing.sku = existing.sku or offer.sku
                db.delete(offer)
            else:
                offer.product_id = keep.id
        other.active = False
        other.gtin = ""  # ne ütközzön újra
        other.slug = f"{other.slug}-merged-{other.id}"
    db.commit()
    db.refresh(keep)
    return keep
