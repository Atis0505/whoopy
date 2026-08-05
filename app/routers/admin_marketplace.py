"""Belső marketplace ops: partnerek, staging, feed, árazás, beszerzés, dedup, KPI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import FeedSource, Offer, PricingRule, Product, StagingListing, Supplier, User
from app.services.dedup import find_gtin_duplicates, merge_products_by_gtin
from app.services.feed_ingest import run_feed_source
from app.services.procurement import partner_catalog, partner_kpi, procurement_for_open_orders
from app.services.staging import publish_staging, reject_staging

router = APIRouter(prefix="/admin", tags=["admin-marketplace"])
templates = Jinja2Templates(directory="app/templates")


def _money(value: float) -> str:
    return f"{value:,.0f} Ft".replace(",", " ")


templates.env.filters["huf"] = _money


def _admin(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not (user.role == "admin" or user.is_admin):
        return RedirectResponse("/login", status_code=303)
    return user


def _staff(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not user.is_staff:
        return RedirectResponse("/login", status_code=303)
    return user


# ── Partners (belső böngésző) ────────────────────────────────────────────────

@router.get("/partners", response_class=HTMLResponse)
def partners_hub(request: Request, db: Session = Depends(get_db)):
    user = _staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    kpis = partner_kpi(db)
    return templates.TemplateResponse(
        "admin/partners.html",
        {"request": request, "user": user, "kpis": kpis, "app_name": settings.app_name},
    )


@router.get("/partners/{supplier_id}", response_class=HTMLResponse)
def partner_detail(supplier_id: int, request: Request, db: Session = Depends(get_db)):
    user = _staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        return RedirectResponse("/admin/partners", status_code=302)
    catalog = partner_catalog(db, supplier_id)
    return templates.TemplateResponse(
        "admin/partner_detail.html",
        {
            "request": request,
            "user": user,
            "supplier": supplier,
            "catalog": catalog,
            "app_name": settings.app_name,
        },
    )


@router.post("/partners/{supplier_id}")
def partner_update(
    supplier_id: int,
    request: Request,
    dropship_available: str = Form(""),
    preferred: str = Form(""),
    notes: str = Form(""),
    active: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    s = db.get(Supplier, supplier_id)
    if s:
        s.dropship_available = dropship_available == "1"
        s.preferred = preferred == "1"
        s.notes = notes
        s.active = active == "1"
        db.commit()
    return RedirectResponse(f"/admin/partners/{supplier_id}", status_code=303)


@router.post("/offers/{offer_id}/preferred")
def offer_set_preferred(offer_id: int, request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    offer = db.get(Offer, offer_id)
    if offer:
        for o in db.query(Offer).filter(Offer.product_id == offer.product_id).all():
            o.preferred_source = o.id == offer.id
        db.commit()
        return RedirectResponse(f"/admin/partners/{offer.supplier_id}", status_code=303)
    return RedirectResponse("/admin/partners", status_code=303)


# ── Staging ──────────────────────────────────────────────────────────────────

@router.get("/staging", response_class=HTMLResponse)
def staging_list(request: Request, status: str = "pending", db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    q = db.query(StagingListing).order_by(StagingListing.id.desc())
    if status and status != "all":
        q = q.filter(StagingListing.status == status)
    rows = q.limit(200).all()
    suppliers = {s.id: s for s in db.query(Supplier).all()}
    return templates.TemplateResponse(
        "admin/staging.html",
        {
            "request": request,
            "user": user,
            "rows": rows,
            "suppliers": suppliers,
            "status": status,
            "app_name": settings.app_name,
            "flash": request.session.pop("staging_flash", None),
        },
    )


@router.post("/staging/{row_id}/publish")
def staging_publish(row_id: int, request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    try:
        publish_staging(db, row_id)
        request.session["staging_flash"] = f"Publikálva #{row_id}"
    except Exception as exc:
        request.session["staging_flash"] = f"Hiba: {exc}"
    return RedirectResponse("/admin/staging", status_code=303)


@router.post("/staging/{row_id}/reject")
def staging_reject(
    row_id: int,
    request: Request,
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    try:
        reject_staging(db, row_id, reason)
        request.session["staging_flash"] = f"Elutasítva #{row_id}"
    except Exception as exc:
        request.session["staging_flash"] = f"Hiba: {exc}"
    return RedirectResponse("/admin/staging", status_code=303)


@router.post("/staging/publish-all-pending")
def staging_publish_all(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    pending = db.query(StagingListing).filter(StagingListing.status == "pending").limit(100).all()
    ok = 0
    err = 0
    for row in pending:
        try:
            publish_staging(db, row.id)
            ok += 1
        except Exception:
            err += 1
    request.session["staging_flash"] = f"Batch: {ok} ok, {err} hiba"
    return RedirectResponse("/admin/staging", status_code=303)


# ── Feeds ────────────────────────────────────────────────────────────────────

@router.get("/feeds", response_class=HTMLResponse)
def feeds_page(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    feeds = (
        db.query(FeedSource)
        .options(joinedload(FeedSource.supplier))
        .order_by(FeedSource.id.desc())
        .all()
    )
    suppliers = db.query(Supplier).filter(Supplier.active.is_(True)).order_by(Supplier.name).all()
    return templates.TemplateResponse(
        "admin/feeds.html",
        {
            "request": request,
            "user": user,
            "feeds": feeds,
            "suppliers": suppliers,
            "app_name": settings.app_name,
            "flash": request.session.pop("feed_flash", None),
        },
    )


@router.post("/feeds/create")
def feeds_create(
    request: Request,
    supplier_id: int = Form(...),
    name: str = Form("Feed"),
    source_type: str = Form("csv"),
    url: str = Form(""),
    field_map: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    db.add(
        FeedSource(
            supplier_id=supplier_id,
            name=name.strip() or "Feed",
            source_type=source_type if source_type in ("csv", "json", "url_json", "manual") else "csv",
            url=url.strip(),
            field_map=field_map.strip(),
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/feeds", status_code=303)


@router.post("/feeds/{feed_id}/run")
async def feeds_run(
    feed_id: int,
    request: Request,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    csv_text = None
    if file and file.filename:
        raw = await file.read()
        csv_text = raw.decode("utf-8-sig", errors="replace")
    try:
        run = run_feed_source(db, feed_id, csv_text=csv_text)
        request.session["feed_flash"] = f"Run #{run.id}: +{run.rows_ok} staging, fail={run.rows_failed}"
    except Exception as exc:
        request.session["feed_flash"] = f"Hiba: {exc}"
    return RedirectResponse("/admin/feeds", status_code=303)


# ── Pricing ──────────────────────────────────────────────────────────────────

@router.get("/pricing-rules", response_class=HTMLResponse)
def pricing_rules_page(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    rules = db.query(PricingRule).order_by(PricingRule.priority, PricingRule.id).all()
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse(
        "admin/pricing_rules.html",
        {
            "request": request,
            "user": user,
            "rules": rules,
            "suppliers": suppliers,
            "app_name": settings.app_name,
        },
    )


@router.post("/pricing-rules/create")
def pricing_rules_create(
    request: Request,
    name: str = Form(...),
    rule_type: str = Form("margin_percent"),
    value: float = Form(20),
    min_margin_percent: float = Form(0),
    buybox_mode: str = Form("cheapest"),
    supplier_id: int = Form(0),
    priority: int = Form(100),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    db.add(
        PricingRule(
            name=name.strip(),
            rule_type=rule_type,
            value=value,
            min_margin_percent=min_margin_percent,
            buybox_mode=buybox_mode,
            supplier_id=supplier_id or None,
            priority=priority,
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/pricing-rules", status_code=303)


# ── Procurement ──────────────────────────────────────────────────────────────

@router.get("/procurement", response_class=HTMLResponse)
def procurement_page(request: Request, db: Session = Depends(get_db)):
    user = _staff(request, db)
    if isinstance(user, RedirectResponse):
        return user
    blocks = procurement_for_open_orders(db)
    return templates.TemplateResponse(
        "admin/procurement.html",
        {"request": request, "user": user, "blocks": blocks, "app_name": settings.app_name},
    )


# ── Dedup ────────────────────────────────────────────────────────────────────

@router.get("/dedup", response_class=HTMLResponse)
def dedup_page(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    dupes = find_gtin_duplicates(db)
    return templates.TemplateResponse(
        "admin/dedup.html",
        {
            "request": request,
            "user": user,
            "dupes": dupes,
            "app_name": settings.app_name,
            "flash": request.session.pop("dedup_flash", None),
        },
    )


@router.post("/dedup/merge")
def dedup_merge(
    request: Request,
    gtin: str = Form(...),
    keep_product_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    try:
        keep = merge_products_by_gtin(db, gtin, keep_product_id=keep_product_id)
        request.session["dedup_flash"] = f"Összevonva → product #{keep.id} ({keep.slug})"
    except Exception as exc:
        request.session["dedup_flash"] = f"Hiba: {exc}"
    return RedirectResponse("/admin/dedup", status_code=303)


# ── Partner KPI ──────────────────────────────────────────────────────────────

@router.get("/partner-kpi", response_class=HTMLResponse)
def partner_kpi_page(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        "admin/partner_kpi.html",
        {"request": request, "user": user, "kpis": partner_kpi(db), "app_name": settings.app_name},
    )
