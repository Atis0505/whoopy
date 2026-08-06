"""Futár / címke stub — GLS, Foxpost, Packeta (outbox, nem éles API)."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.models import Order, OrderShipment

logger = logging.getLogger(__name__)
OUTBOX = BASE_DIR / "data" / "carrier_outbox"


def _write_outbox(name: str, payload: dict) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def create_shipping_label(db: Session, shipment: OrderShipment, *, carrier: str = "gls") -> dict:
    """Címke stub: tracking + outbox JSON."""
    carrier = (carrier or "gls").lower()
    if carrier not in ("gls", "foxpost", "packeta", "manual"):
        carrier = "gls"
    order = db.get(Order, shipment.order_id)
    tracking = f"{carrier.upper()}-{secrets.token_hex(4).upper()}"
    payload = {
        "carrier": carrier,
        "order_number": order.order_number if order else "",
        "shipment_id": shipment.id,
        "to": {
            "name": order.full_name if order else "",
            "city": order.city if order else "",
            "address": order.address if order else "",
            "zip": order.zip_code if order else "",
            "country": order.country if order else "HU",
        },
        "tracking": tracking,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    path = _write_outbox(f"label_{shipment.id}_{tracking}.json", payload)
    shipment.carrier = carrier
    shipment.tracking_code = tracking
    shipment.label_ref = path.name
    shipment.status = "labeled"
    db.commit()
    logger.info("Carrier label stub → %s", path)
    return {"ok": True, "tracking": tracking, "carrier": carrier, "path": str(path)}


def sync_tracking(db: Session, shipment: OrderShipment) -> dict:
    """Tracking sync stub — labeled → shipped → delivered."""
    flow = ["pending", "labeled", "shipped", "delivered"]
    cur = shipment.status or "pending"
    if cur not in flow:
        cur = "pending"
    idx = flow.index(cur)
    if idx < len(flow) - 1:
        shipment.status = flow[idx + 1]
        if shipment.status == "shipped" and not shipment.fulfilled_at:
            shipment.fulfilled_at = datetime.utcnow()
        db.commit()
    return {"ok": True, "status": shipment.status, "tracking": shipment.tracking_code}
