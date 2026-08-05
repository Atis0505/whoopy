"""Rendelés → partnerenkénti beszerzési nézet + partner KPI."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Offer, Order, OrderLine, Product, Supplier


def procurement_for_open_orders(db: Session) -> list[dict]:
    """Nyitott rendelések tételei partnerenként csoportosítva."""
    orders = (
        db.query(Order)
        .options(joinedload(Order.lines))
        .filter(Order.status.in_(("pending", "paid")))
        .order_by(Order.id.desc())
        .limit(100)
        .all()
    )
    by_supplier: dict[int, dict] = {}
    for order in orders:
        for line in order.lines or []:
            sid = line.supplier_id
            if sid not in by_supplier:
                by_supplier[sid] = {
                    "supplier_id": sid,
                    "supplier_name": line.supplier_name,
                    "lines": [],
                    "order_ids": set(),
                }
            by_supplier[sid]["order_ids"].add(order.order_number)
            by_supplier[sid]["lines"].append(
                {
                    "order_number": order.order_number,
                    "order_id": order.id,
                    "order_status": order.status,
                    "sku": line.sku,
                    "title": line.product_title,
                    "qty": line.quantity,
                    "unit_price": line.unit_price,
                    "line_total": line.line_total,
                }
            )
    result = []
    for block in by_supplier.values():
        block["order_count"] = len(block["order_ids"])
        block["order_ids"] = sorted(block["order_ids"])
        block["line_count"] = len(block["lines"])
        block["qty_total"] = sum(x["qty"] for x in block["lines"])
        result.append(block)
    result.sort(key=lambda x: (-x["line_count"], x["supplier_name"]))
    return result


def alternative_sources(db: Session, product_id: int) -> list[Offer]:
    return (
        db.query(Offer)
        .options(joinedload(Offer.supplier))
        .filter(Offer.product_id == product_id, Offer.active.is_(True))
        .order_by(Offer.price.asc())
        .all()
    )


def partner_kpi(db: Session) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=30)
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    rows = []
    for s in suppliers:
        offers = db.query(Offer).filter(Offer.supplier_id == s.id).all()
        active_offers = [o for o in offers if o.active]
        low = [o for o in active_offers if o.stock <= 5]
        line_q = (
            db.query(func.count(OrderLine.id), func.coalesce(func.sum(OrderLine.line_total), 0.0))
            .join(Order, Order.id == OrderLine.order_id)
            .filter(OrderLine.supplier_id == s.id, Order.created_at >= since)
            .first()
        )
        lines_30, revenue_30 = line_q if line_q else (0, 0.0)
        rows.append(
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "active": s.active,
                "dropship_available": s.dropship_available,
                "preferred": s.preferred,
                "offers": len(offers),
                "active_offers": len(active_offers),
                "low_stock": len(low),
                "lines_30d": int(lines_30 or 0),
                "revenue_30d": float(revenue_30 or 0),
            }
        )
    return rows


def partner_catalog(db: Session, supplier_id: int) -> list[dict]:
    offers = (
        db.query(Offer)
        .options(joinedload(Offer.product))
        .filter(Offer.supplier_id == supplier_id)
        .order_by(Offer.id.desc())
        .limit(500)
        .all()
    )
    out = []
    for o in offers:
        p = o.product
        alts = 0
        if p:
            alts = (
                db.query(func.count(Offer.id))
                .filter(Offer.product_id == p.id, Offer.supplier_id != supplier_id, Offer.active.is_(True))
                .scalar()
                or 0
            )
        out.append(
            {
                "offer_id": o.id,
                "sku": o.sku,
                "price": o.price,
                "cost_price": o.cost_price,
                "stock": o.stock,
                "lead_days": o.lead_days,
                "active": o.active,
                "preferred_source": o.preferred_source,
                "product_id": p.id if p else None,
                "title": p.title if p else "—",
                "gtin": p.gtin if p else "",
                "alt_sources": alts,
            }
        )
    return out
