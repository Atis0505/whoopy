"""Online fizetés route-ok (demo / Stripe / SimplePay)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import store_context
from app.models import Order
from app.services.payments import (
    complete_stripe_session,
    mark_order_failed,
    mark_order_paid,
    resolve_provider,
    start_payment,
    verify_simplepay_ipn,
    verify_stripe_webhook,
)

router = APIRouter(tags=["payments"])
templates = Jinja2Templates(directory="app/templates")


def _load_order(db: Session, order_number: str) -> Order | None:
    return (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.order_number == order_number)
        .first()
    )


@router.get("/pay/{order_number}")
def pay_start(order_number: str, request: Request, db: Session = Depends(get_db)):
    order = _load_order(db, order_number)
    if not order:
        return RedirectResponse("/", status_code=302)
    if order.payment_method != "prepaid":
        return RedirectResponse(f"/order/{order.order_number}", status_code=302)
    if order.payment_status == "paid":
        return RedirectResponse(f"/order/{order.order_number}", status_code=302)

    result = start_payment(db, order)
    if result.redirect_url:
        return RedirectResponse(result.redirect_url, status_code=303)
    return templates.TemplateResponse(
        "store/pay_error.html",
        store_context(request, db, order=order, error=result.error or "Fizetés indítása sikertelen"),
        status_code=400,
    )


@router.get("/pay/{order_number}/demo", response_class=HTMLResponse)
def pay_demo_page(order_number: str, request: Request, db: Session = Depends(get_db)):
    order = _load_order(db, order_number)
    if not order:
        return RedirectResponse("/", status_code=302)
    if order.payment_status == "paid":
        return RedirectResponse(f"/order/{order.order_number}", status_code=302)
    return templates.TemplateResponse(
        "store/pay_demo.html",
        store_context(
            request,
            db,
            order=order,
            provider=resolve_provider(),
        ),
    )


@router.post("/pay/{order_number}/demo")
def pay_demo_confirm(
    order_number: str,
    action: str = Form("pay"),
    db: Session = Depends(get_db),
):
    order = _load_order(db, order_number)
    if not order:
        return RedirectResponse("/", status_code=302)
    if action == "fail":
        mark_order_failed(db, order, provider="demo", payment_ref="demo-fail")
        return RedirectResponse(f"/order/{order.order_number}?pay=failed", status_code=303)
    mark_order_paid(db, order, provider="demo", payment_ref="demo-ok")
    return RedirectResponse(f"/order/{order.order_number}?pay=ok", status_code=303)


@router.get("/pay/return")
def pay_return(
    request: Request,
    provider: str = "demo",
    order: str = "",
    session_id: str = "",
    cancelled: str = "",
    db: Session = Depends(get_db),
):
    order_number = order or request.query_params.get("order", "")
    ord_obj = _load_order(db, order_number) if order_number else None
    if not ord_obj:
        return RedirectResponse("/", status_code=302)

    if cancelled == "1":
        if ord_obj.payment_status != "paid":
            mark_order_failed(db, ord_obj, provider=provider or "stripe", payment_ref=session_id)
        return RedirectResponse(f"/order/{ord_obj.order_number}?pay=cancelled", status_code=303)

    if provider == "stripe" and session_id:
        ok = complete_stripe_session(db, ord_obj, session_id)
        return RedirectResponse(
            f"/order/{ord_obj.order_number}?pay={'ok' if ok else 'pending'}",
            status_code=303,
        )

    # SimplePay return — IPN erősíti meg; itt várakozó / újratöltés
    if provider == "simplepay":
        # sandbox / manuális: ha r=OK query (OTP néha küldi)
        r = request.query_params.get("r") or request.query_params.get("event")
        if r and str(r).upper() in ("OK", "SUCCESS", "FINISHED"):
            mark_order_paid(db, ord_obj, provider="simplepay", payment_ref=ord_obj.payment_ref)
            return RedirectResponse(f"/order/{ord_obj.order_number}?pay=ok", status_code=303)
        return RedirectResponse(f"/order/{ord_obj.order_number}?pay=pending", status_code=303)

    return RedirectResponse(f"/order/{ord_obj.order_number}", status_code=303)


@router.post("/pay/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    event = verify_stripe_webhook(payload, sig)
    if not event:
        # fejlesztés: secret nélkül fogadjuk a session.completed-et ha van body
        try:
            import json

            event = json.loads(payload.decode("utf-8"))
        except Exception:
            return HTMLResponse("invalid", status_code=400)

    etype = event.get("type")
    data_obj = (event.get("data") or {}).get("object") or {}
    if etype == "checkout.session.completed":
        order_number = data_obj.get("client_reference_id") or (data_obj.get("metadata") or {}).get(
            "order_number"
        )
        if order_number:
            ord_obj = _load_order(db, order_number)
            if ord_obj and ord_obj.payment_status != "paid":
                mark_order_paid(
                    db,
                    ord_obj,
                    provider="stripe",
                    payment_ref=data_obj.get("id") or "",
                )
    return HTMLResponse("ok")


@router.post("/pay/webhook/simplepay")
async def simplepay_ipn(request: Request, db: Session = Depends(get_db)):
    """OTP SimplePay IPN — JSON body + Signature header."""
    raw = await request.body()
    sig = request.headers.get("Signature", "")
    body = verify_simplepay_ipn(raw, sig)
    if body is None:
        return HTMLResponse("invalid signature", status_code=401)
    order_ref = body.get("orderRef") or body.get("o")
    status = str(body.get("status") or body.get("e") or "").upper()
    if not order_ref:
        return HTMLResponse("missing", status_code=400)
    ord_obj = _load_order(db, order_ref)
    if not ord_obj:
        return HTMLResponse("unknown", status_code=404)
    if status in ("FINISHED", "SUCCESS", "PAID", "COMPLETE"):
        mark_order_paid(
            db,
            ord_obj,
            provider="simplepay",
            payment_ref=str(body.get("transactionId") or body.get("t") or ""),
        )
    elif status in ("CANCELLED", "TIMEOUT", "FAIL", "FAILED"):
        mark_order_failed(db, ord_obj, provider="simplepay")
    return HTMLResponse("OK")
