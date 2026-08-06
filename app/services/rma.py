"""RMA: visszaküldési címke + refund stub."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.models import Order, ReturnRequest

logger = logging.getLogger(__name__)
OUTBOX = BASE_DIR / "data" / "rma_outbox"


def generate_return_label(db: Session, ret: ReturnRequest, *, carrier: str = "gls") -> dict:
    order = db.get(Order, ret.order_id)
    code = f"RMA-{secrets.token_hex(3).upper()}"
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / f"{code}.json"
    payload = {
        "rma": code,
        "carrier": carrier,
        "order_number": order.order_number if order else "",
        "email": ret.email,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ret.label_code = code
    ret.label_carrier = carrier
    ret.label_path = str(path)
    ret.status = "label_sent"
    ret.updated_at = datetime.utcnow()
    db.commit()
    logger.info("RMA label → %s", path)
    return {"ok": True, "label_code": code, "path": str(path)}


def mark_refund(db: Session, ret: ReturnRequest, *, amount: float | None = None) -> dict:
    order = db.get(Order, ret.order_id)
    amt = float(amount if amount is not None else (order.grand_total if order else 0))
    ret.refund_amount = amt
    ret.refund_status = "refunded"
    ret.status = "refunded"
    ret.updated_at = datetime.utcnow()
    if order:
        order.payment_status = "refunded"
        order.status = "refunded"
    db.commit()
    return {"ok": True, "refund_amount": amt}
