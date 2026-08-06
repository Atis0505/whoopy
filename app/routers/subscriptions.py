"""Vásárlói ismétlődő rendelések + fiók műveletek."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import cart_for_request, get_current_user, store_context
from app.models import CartItem, Offer, Order, Subscription
from app.services.subscriptions import ALLOWED_INTERVALS, create_from_order, create_subscription

router = APIRouter(tags=["subscriptions"])
templates = Jinja2Templates(directory="app/templates")


def _require_customer(request: Request, db: Session):
    user = get_current_user(request, db)
    if not user:
        return None
    return user


@router.post("/account/subscriptions/from-order/{order_id}")
def sub_from_order(
    order_id: int,
    request: Request,
    interval_days: int = Form(30),
    db: Session = Depends(get_db),
):
    user = _require_customer(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    order = (
        db.query(Order)
        .options(joinedload(Order.lines))
        .filter(Order.id == order_id, Order.customer_id == user.id)
        .first()
    )
    if not order:
        # allow by email match for guest→registered
        order = (
            db.query(Order)
            .options(joinedload(Order.lines))
            .filter(Order.id == order_id, Order.email == user.email)
            .first()
        )
    if not order:
        return RedirectResponse("/account?sub_error=1", status_code=303)
    try:
        create_from_order(db, user, order, interval_days=interval_days)
    except ValueError:
        return RedirectResponse("/account?sub_error=1", status_code=303)
    return RedirectResponse("/account?sub_ok=1", status_code=303)


@router.post("/account/subscriptions/from-cart")
def sub_from_cart(
    request: Request,
    interval_days: int = Form(30),
    name: str = Form("Kosár ismétlés"),
    db: Session = Depends(get_db),
):
    user = _require_customer(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    cart = cart_for_request(request, db)
    items = (
        db.query(CartItem)
        .options(joinedload(CartItem.offer))
        .filter(CartItem.cart_id == cart.id)
        .all()
    )
    lines = [(it.offer_id, it.quantity) for it in items if it.offer_id]
    last = (
        db.query(Order)
        .filter(Order.customer_id == user.id)
        .order_by(Order.id.desc())
        .first()
    )
    try:
        create_subscription(
            db,
            user,
            lines=lines,
            interval_days=interval_days,
            name=name.strip() or "Kosár ismétlés",
            email=user.email,
            full_name=(user.full_name or (last.full_name if last else "")) or "",
            phone=(user.phone or (last.phone if last else "")) or "",
            country=(cart.country or (last.country if last else None) or "HU"),
            city=(last.city if last else "") or "",
            address=(last.address if last else "") or "",
            zip_code=(last.zip_code if last else "") or "",
            payment_preference=cart.payment_preference or "cod",
        )
    except ValueError:
        return RedirectResponse("/cart?sub_error=1", status_code=303)
    return RedirectResponse("/account?sub_ok=1", status_code=303)


@router.post("/account/subscriptions/{sub_id}/pause")
def sub_pause(sub_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_customer(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if sub:
        sub.paused = True
        db.commit()
    return RedirectResponse("/account", status_code=303)


@router.post("/account/subscriptions/{sub_id}/resume")
def sub_resume(sub_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_customer(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if sub:
        sub.paused = False
        sub.active = True
        db.commit()
    return RedirectResponse("/account", status_code=303)


@router.post("/account/subscriptions/{sub_id}/cancel")
def sub_cancel(sub_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_customer(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if sub:
        sub.active = False
        sub.paused = True
        db.commit()
    return RedirectResponse("/account", status_code=303)


@router.post("/account/subscriptions/{sub_id}/interval")
def sub_interval(
    sub_id: int,
    request: Request,
    interval_days: int = Form(30),
    db: Session = Depends(get_db),
):
    user = _require_customer(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if sub and int(interval_days) in ALLOWED_INTERVALS:
        sub.interval_days = int(interval_days)
        db.commit()
    return RedirectResponse("/account", status_code=303)
