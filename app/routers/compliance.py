"""GDPR + B2B cart helpers."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import cart_for_request, get_current_user
from app.services.compliance import anonymize_user, export_user_data
from app.services.vat import validate_eu_vat_format

router = APIRouter(tags=["compliance"])


@router.get("/account/export")
def account_export(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    data = export_user_data(db, user)
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="whoopy-data-{user.id}.json"'},
    )


@router.post("/account/delete")
def account_delete(request: Request, confirm: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if confirm.strip().upper() != "TORLES":
        return RedirectResponse("/account?gdpr_error=1", status_code=303)
    if user.is_staff:
        return RedirectResponse("/account?gdpr_error=staff", status_code=303)
    anonymize_user(db, user)
    request.session.clear()
    return RedirectResponse("/?gdpr=deleted", status_code=303)


@router.post("/cart/b2b")
def cart_b2b(
    request: Request,
    is_b2b: str = Form(""),
    buyer_vat_id: str = Form(""),
    db: Session = Depends(get_db),
):
    cart = cart_for_request(request, db)
    want = is_b2b == "1"
    vat = buyer_vat_id.strip().upper()
    if want and vat and not validate_eu_vat_format(vat):
        return RedirectResponse("/cart?vat_error=1", status_code=303)
    cart.is_b2b = want
    cart.buyer_vat_id = vat if want else ""
    db.commit()
    return RedirectResponse("/cart", status_code=303)
