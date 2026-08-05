"""Online fizetés: demo / Stripe Checkout / OTP SimplePay."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Order

logger = logging.getLogger(__name__)


@dataclass
class PaymentStartResult:
    provider: str
    redirect_url: Optional[str] = None
    form_url: Optional[str] = None
    form_fields: Optional[dict[str, str]] = None
    error: Optional[str] = None


def resolve_provider() -> str:
    mode = (settings.payment_provider or "auto").lower().strip()
    if mode in ("demo", "stripe", "simplepay"):
        if mode == "stripe" and not settings.stripe_secret_key:
            return "demo"
        if mode == "simplepay" and not (settings.simplepay_merchant and settings.simplepay_secret_key):
            return "demo"
        return mode
    # auto
    if settings.stripe_secret_key:
        return "stripe"
    if settings.simplepay_merchant and settings.simplepay_secret_key:
        return "simplepay"
    return "demo"


def mark_order_paid(db: Session, order: Order, *, provider: str, payment_ref: str = "") -> Order:
    order.status = "paid"
    order.payment_status = "paid"
    order.payment_provider = provider
    if payment_ref:
        order.payment_ref = payment_ref
    order.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


def mark_order_failed(db: Session, order: Order, *, provider: str, payment_ref: str = "") -> Order:
    order.payment_status = "failed"
    order.payment_provider = provider
    if payment_ref:
        order.payment_ref = payment_ref
    db.commit()
    db.refresh(order)
    return order


def start_payment(db: Session, order: Order) -> PaymentStartResult:
    """Előre fizetés indítása — redirect URL vagy SimplePay form."""
    if order.payment_method != "prepaid":
        return PaymentStartResult(provider="none", error="Nem online fizetéses rendelés")
    if order.payment_status == "paid":
        return PaymentStartResult(
            provider=order.payment_provider or "none",
            redirect_url=f"{settings.public_base_url}/order/{order.order_number}",
        )

    provider = resolve_provider()
    order.payment_provider = provider
    order.payment_status = "awaiting"
    db.commit()

    if provider == "stripe":
        return _start_stripe(db, order)
    if provider == "simplepay":
        return _start_simplepay(db, order)
    return PaymentStartResult(
        provider="demo",
        redirect_url=f"{settings.public_base_url}/pay/{order.order_number}/demo",
    )


def _start_stripe(db: Session, order: Order) -> PaymentStartResult:
    amount = int(round(order.grand_total))
    if amount < 1:
        return PaymentStartResult(provider="stripe", error="Érvénytelen összeg")
    currency = (settings.stripe_currency or "huf").lower()
    # Stripe HUF: zero-decimal
    payload = {
        "mode": "payment",
        "success_url": f"{settings.public_base_url}/pay/return?provider=stripe&order={order.order_number}&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.public_base_url}/pay/return?provider=stripe&order={order.order_number}&cancelled=1",
        "client_reference_id": order.order_number,
        "customer_email": order.email,
        "line_items[0][price_data][currency]": currency,
        "line_items[0][price_data][product_data][name]": f"Whoopy rendelés {order.order_number}",
        "line_items[0][price_data][unit_amount]": str(amount),
        "line_items[0][quantity]": "1",
        "metadata[order_number]": order.order_number,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                data=payload,
                auth=(settings.stripe_secret_key, ""),
            )
            data = resp.json()
            if resp.status_code >= 400:
                logger.error("Stripe session error: %s", data)
                return PaymentStartResult(provider="stripe", error=str(data.get("error", data)))
            order.payment_ref = data.get("id") or ""
            db.commit()
            return PaymentStartResult(provider="stripe", redirect_url=data.get("url"))
    except Exception as exc:
        logger.exception("Stripe start failed")
        return PaymentStartResult(provider="stripe", error=str(exc))


def _simplepay_signature(payload_json: str) -> str:
    digest = hmac.new(
        settings.simplepay_secret_key.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha384,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _start_simplepay(db: Session, order: Order) -> PaymentStartResult:
    """OTP SimplePay v2 start — JSON + Signature header, majd paymentUrl."""
    amount = int(round(order.grand_total))
    base = (
        "https://sandbox.simplepay.hu/payment/v2/start"
        if settings.simplepay_sandbox
        else "https://secure.simplepay.hu/payment/v2/start"
    )
    body: dict[str, Any] = {
        "merchant": settings.simplepay_merchant,
        "orderRef": order.order_number,
        "currency": settings.simplepay_currency or "HUF",
        "customerEmail": order.email,
        "language": (order.lang or "hu")[:2].upper(),
        "total": str(amount),
        "methods": ["CARD"],
        "timeout": "600",
        "url": f"{settings.public_base_url}/pay/return?provider=simplepay&order={order.order_number}",
        "sdkVersion": "Whoopy:1.0",
        "invoice": {
            "name": order.full_name,
            "country": order.country or "HU",
            "city": order.city,
            "zip": order.zip_code or "0000",
            "address": order.address,
        },
    }
    payload_json = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    signature = _simplepay_signature(payload_json)
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                base,
                content=payload_json.encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Signature": signature,
                },
            )
            data = resp.json()
            if resp.status_code >= 400 or data.get("errorCodes"):
                logger.error("SimplePay start error: %s", data)
                # fejlesztői fallback
                return PaymentStartResult(
                    provider="demo",
                    redirect_url=f"{settings.public_base_url}/pay/{order.order_number}/demo",
                    error=str(data),
                )
            pay_url = data.get("paymentUrl") or data.get("redirectUrl")
            order.payment_ref = str(data.get("transactionId") or data.get("orderRef") or "")
            db.commit()
            if not pay_url:
                return PaymentStartResult(
                    provider="demo",
                    redirect_url=f"{settings.public_base_url}/pay/{order.order_number}/demo",
                )
            return PaymentStartResult(provider="simplepay", redirect_url=pay_url)
    except Exception as exc:
        logger.exception("SimplePay start failed")
        return PaymentStartResult(
            provider="demo",
            redirect_url=f"{settings.public_base_url}/pay/{order.order_number}/demo",
            error=str(exc),
        )


def complete_stripe_session(db: Session, order: Order, session_id: str) -> bool:
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
                auth=(settings.stripe_secret_key, ""),
            )
            data = resp.json()
            if resp.status_code >= 400:
                return False
            if data.get("payment_status") == "paid" or data.get("status") == "complete":
                mark_order_paid(db, order, provider="stripe", payment_ref=session_id)
                return True
    except Exception:
        logger.exception("Stripe session verify failed")
    return False


def verify_stripe_webhook(payload: bytes, sig_header: str) -> Optional[dict]:
    """Egyszerű Stripe signature ellenőrzés (v1)."""
    secret = settings.stripe_webhook_secret
    if not secret or not sig_header:
        return None
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
        timestamp = parts.get("t", "")
        v1 = parts.get("v1", "")
        signed = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, v1):
            return None
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None
