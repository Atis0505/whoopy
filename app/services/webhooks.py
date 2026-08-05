"""Outbound webhooks: Whoopy → ERP / külső rendszerek."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Order, OrderShipment, WebhookDelivery, WebhookEndpoint

logger = logging.getLogger(__name__)

ALL_EVENTS = (
    "order.created",
    "order.paid",
    "order.payment_failed",
    "order.status_changed",
    "shipment.updated",
)


def order_payload(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_status": getattr(order, "payment_status", None),
        "payment_provider": getattr(order, "payment_provider", None),
        "payment_ref": getattr(order, "payment_ref", None),
        "email": order.email,
        "full_name": order.full_name,
        "phone": order.phone,
        "country": order.country,
        "city": order.city,
        "address": order.address,
        "zip_code": order.zip_code,
        "subtotal": order.subtotal,
        "discount_total": order.discount_total,
        "shipping_total": order.shipping_total,
        "cod_fee_total": order.cod_fee_total,
        "grand_total": order.grand_total,
        "currency": order.currency,
        "coupon_code": order.coupon_code,
        "lang": order.lang,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if getattr(order, "paid_at", None) else None,
        "lines": [
            {
                "id": ln.id,
                "sku": ln.sku,
                "product_title": ln.product_title,
                "supplier_name": ln.supplier_name,
                "unit_price": ln.unit_price,
                "quantity": ln.quantity,
                "line_total": ln.line_total,
                "ship_mode": ln.ship_mode,
            }
            for ln in (order.lines or [])
        ],
        "shipments": [
            {
                "id": sh.id,
                "supplier_id": sh.supplier_id,
                "supplier_name": sh.supplier_name,
                "method": sh.method,
                "status": sh.status,
                "tracking_code": sh.tracking_code,
                "shipping_price": sh.shipping_price,
                "cod_fee": sh.cod_fee,
                "package_count": sh.package_count,
            }
            for sh in (order.shipments or [])
        ],
    }


def load_order(db: Session, order_id: int) -> Optional[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.id == order_id)
        .first()
    )


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _endpoint_wants(endpoint: WebhookEndpoint, event: str) -> bool:
    raw = (endpoint.events or "").strip()
    if not raw:
        return True
    allowed = {e.strip() for e in raw.split(",") if e.strip()}
    return event in allowed


def _targets(db: Session, event: str) -> list[tuple[Optional[int], str, str]]:
    """[(endpoint_id|None, url, secret), ...]"""
    targets: list[tuple[Optional[int], str, str]] = []
    if settings.webhook_enabled and settings.webhook_url:
        targets.append((None, settings.webhook_url.strip(), settings.webhook_secret or ""))
    for ep in db.query(WebhookEndpoint).filter(WebhookEndpoint.active.is_(True)).all():
        if not _endpoint_wants(ep, event):
            continue
        if not ep.url:
            continue
        # avoid duplicate of config URL
        if any(t[1] == ep.url for t in targets):
            continue
        targets.append((ep.id, ep.url.strip(), ep.secret or settings.webhook_secret or ""))
    return targets


def dispatch_event(db: Session, event: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Szinkron HTTP POST minden aktív célra. Hiba nem dob kivételt a hívónak —
    delivery logba ír.
    """
    envelope = {
        "event": event,
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "source": "whoopy",
        "data": data,
    }
    body = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    results: list[dict[str, Any]] = []
    targets = _targets(db, event)
    if not targets:
        logger.debug("No webhook targets for %s", event)
        return results

    timeout = settings.webhook_timeout_sec or 8.0
    for endpoint_id, url, secret in targets:
        headers = {
            "Content-Type": "application/json",
            "X-Whoopy-Event": event,
            "User-Agent": "Whoopy-Webhook/1.0",
        }
        if secret:
            headers["X-Whoopy-Signature"] = _sign(secret, body)
        status_code = 0
        response_body = ""
        success = False
        error = ""
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, content=body, headers=headers)
                status_code = resp.status_code
                response_body = (resp.text or "")[:2000]
                success = 200 <= resp.status_code < 300
                if not success:
                    error = f"HTTP {resp.status_code}"
        except Exception as exc:
            error = str(exc)[:500]
            logger.warning("Webhook %s → %s failed: %s", event, url, exc)

        delivery = WebhookDelivery(
            endpoint_id=endpoint_id,
            event=event,
            target_url=url,
            payload=body.decode("utf-8"),
            status_code=status_code,
            response_body=response_body,
            success=success,
            error=error,
        )
        db.add(delivery)
        results.append({"url": url, "success": success, "status_code": status_code, "error": error})
    db.commit()
    return results


def emit_order_event(db: Session, event: str, order: Order, extra: Optional[dict] = None) -> None:
    if not order.lines:
        order = load_order(db, order.id) or order
    data = order_payload(order)
    if extra:
        data.update(extra)
    try:
        dispatch_event(db, event, data)
    except Exception:
        logger.exception("emit_order_event %s failed", event)


def emit_shipment_updated(db: Session, shipment: OrderShipment) -> None:
    order = load_order(db, shipment.order_id)
    if not order:
        return
    emit_order_event(
        db,
        "shipment.updated",
        order,
        extra={
            "shipment_id": shipment.id,
            "tracking_code": shipment.tracking_code,
            "shipment_status": shipment.status,
        },
    )


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not secret or not signature:
        return False
    expected = _sign(secret, body)
    return hmac.compare_digest(expected, signature)
