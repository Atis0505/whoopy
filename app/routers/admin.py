from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, try_login
from app.models import (
    AffiliatePartner,
    Campaign,
    Category,
    Coupon,
    NewsletterSubscriber,
    Offer,
    Order,
    Product,
    ProductImage,
    Promotion,
    ShippingRate,
    Supplier,
    User,
    WebhookDelivery,
    WebhookEndpoint,
)
from app.services.media import delete_product_image, save_product_image, set_primary_image
from app.services.webhooks import dispatch_event

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _money(value: float) -> str:
    return f"{value:,.0f} Ft".replace(",", " ")


templates.env.filters["huf"] = _money


def _require_admin_html(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not (user.role == "admin" or user.is_admin):
        return RedirectResponse("/login", status_code=303)
    return user


def _require_staff_html(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if not user or not user.is_staff:
        return RedirectResponse("/login", status_code=303)
    return user


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": None, "app_name": settings.app_name},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = try_login(db, email, password)
    if not user or not user.is_staff:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Csak admin vagy dolgozó léphet be ide", "app_name": settings.app_name},
            status_code=401,
        )
    request.session["user_id"] = user.id
    if user.role == "worker":
        return RedirectResponse("/admin/orders", status_code=303)
    return RedirectResponse("/admin", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.store_settings import get_store_settings
    from app.services.storefront_ops import pending_order_count

    store = get_store_settings(db)
    stats = {
        "products": db.query(Product).count(),
        "suppliers": db.query(Supplier).count(),
        "offers": db.query(Offer).count(),
        "orders": db.query(Order).count(),
        "pending": pending_order_count(db),
        "categories": db.query(Category).count(),
        "coupons": db.query(Coupon).count(),
        "subscribers": db.query(NewsletterSubscriber).filter(NewsletterSubscriber.active.is_(True)).count(),
    }
    recent = db.query(Order).order_by(Order.created_at.desc()).limit(8).all()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "recent": recent,
            "store": store,
            "app_name": settings.app_name,
        },
    )


@router.post("/maintenance/toggle")
def maintenance_toggle(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.store_settings import get_store_settings, touch_settings

    store = get_store_settings(db)
    store.maintenance_mode = not bool(store.maintenance_mode)
    touch_settings(store)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.get("/suppliers", response_class=HTMLResponse)
def suppliers_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse(
        "admin/suppliers.html",
        {"request": request, "user": user, "suppliers": suppliers, "app_name": settings.app_name},
    )


@router.post("/suppliers/create")
def suppliers_create(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    email: str = Form(""),
    country: str = Form("HU"),
    city: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    db.add(Supplier(code=code.strip(), name=name.strip(), email=email.strip(), country=country.upper(), city=city.strip()))
    db.commit()
    return RedirectResponse("/admin/suppliers", status_code=303)


@router.get("/products", response_class=HTMLResponse)
def products_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    products = (
        db.query(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.offers).joinedload(Offer.supplier),
            joinedload(Product.images),
        )
        .order_by(Product.title)
        .all()
    )
    categories = db.query(Category).order_by(Category.full_path).all()
    suppliers = db.query(Supplier).filter(Supplier.active.is_(True)).order_by(Supplier.name).all()
    from app.services.store_settings import get_store_settings

    store = get_store_settings(db)
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "user": user,
            "products": products,
            "categories": categories,
            "suppliers": suppliers,
            "low_stock": store.low_stock_threshold,
            "app_name": settings.app_name,
        },
    )


@router.post("/products/create")
def products_create(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    brand: str = Form(""),
    description: str = Form(""),
    weight_kg: float = Form(0.5),
    ship_mode: str = Form("combinable"),
    category_id: int = Form(0),
    image_url: str = Form(""),
    supplier_id: int = Form(...),
    price: float = Form(...),
    cost_price: float = Form(0),
    stock: int = Form(10),
    sku: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    product = Product(
        title=title.strip(),
        slug=slug.strip().lower().replace(" ", "-"),
        brand=brand.strip(),
        description=description.strip(),
        weight_kg=weight_kg,
        ship_mode=ship_mode if ship_mode in ("combinable", "separate") else "combinable",
        category_id=category_id or None,
        image_url=image_url.strip(),
        active=True,
    )
    db.add(product)
    db.flush()
    db.add(
        Offer(
            product_id=product.id,
            supplier_id=supplier_id,
            sku=sku.strip() or f"SKU-{product.id}",
            price=price,
            cost_price=cost_price,
            stock=stock,
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/images")
async def admin_upload_image(
    product_id: int,
    request: Request,
    file: UploadFile = File(...),
    alt: str = Form(""),
    set_primary: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse("/admin/products", status_code=303)
    await save_product_image(
        db,
        product,
        file,
        alt=alt,
        set_primary=set_primary == "1",
    )
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/images/{image_id}/primary")
def admin_primary_image(
    product_id: int,
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    product = db.get(Product, product_id)
    image = db.get(ProductImage, image_id)
    if product and image and image.product_id == product_id:
        set_primary_image(db, product, image)
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/images/{image_id}/delete")
def admin_delete_image(
    product_id: int,
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    product = db.get(Product, product_id)
    image = db.get(ProductImage, image_id)
    if product and image and image.product_id == product_id:
        delete_product_image(db, product, image)
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/shipping", response_class=HTMLResponse)
def shipping_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    rates = (
        db.query(ShippingRate)
        .options(joinedload(ShippingRate.supplier))
        .order_by(ShippingRate.supplier_id, ShippingRate.min_weight_kg)
        .all()
    )
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return templates.TemplateResponse(
        "admin/shipping.html",
        {"request": request, "user": user, "rates": rates, "suppliers": suppliers, "app_name": settings.app_name},
    )


@router.post("/shipping/create")
def shipping_create(
    request: Request,
    supplier_id: int = Form(...),
    name: str = Form(...),
    country: str = Form("HU"),
    method: str = Form("courier"),
    payment_method: str = Form("any"),
    min_weight_kg: float = Form(0),
    max_weight_kg: float = Form(30),
    price: float = Form(...),
    price_per_separate_unit: float = Form(0),
    cod_fee: float = Form(0),
    free_above: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    free_val = float(free_above) if free_above.strip() else None
    db.add(
        ShippingRate(
            supplier_id=supplier_id,
            name=name.strip(),
            country=country.upper(),
            method=method,
            payment_method=payment_method,
            min_weight_kg=min_weight_kg,
            max_weight_kg=max_weight_kg,
            price=price,
            price_per_separate_unit=price_per_separate_unit,
            cod_fee=cod_fee,
            free_above=free_val,
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/shipping", status_code=303)


@router.get("/coupons", response_class=HTMLResponse)
def coupons_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    coupons = db.query(Coupon).order_by(Coupon.code).all()
    return templates.TemplateResponse(
        "admin/coupons.html",
        {"request": request, "user": user, "coupons": coupons, "app_name": settings.app_name},
    )


@router.post("/coupons/create")
def coupons_create(
    request: Request,
    code: str = Form(...),
    coupon_type: str = Form("percent"),
    value: float = Form(0),
    min_order: float = Form(0),
    max_uses: int = Form(0),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    db.add(
        Coupon(
            code=code.strip().upper(),
            coupon_type=coupon_type,
            value=value,
            min_order=min_order,
            max_uses=max_uses,
            description=description.strip(),
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/coupons", status_code=303)


@router.get("/promotions", response_class=HTMLResponse)
def promotions_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    promos = db.query(Promotion).order_by(Promotion.id.desc()).all()
    products = db.query(Product).order_by(Product.title).all()
    return templates.TemplateResponse(
        "admin/promotions.html",
        {"request": request, "user": user, "promos": promos, "products": products, "app_name": settings.app_name},
    )


@router.post("/promotions/create")
async def promotions_create(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    form = await request.form()
    name = str(form.get("name") or "").strip()
    promo_type = str(form.get("promo_type") or "percent")
    value = float(form.get("value") or 0)
    product_ids = form.getlist("product_ids")
    ids = ",".join(str(x) for x in product_ids if str(x).isdigit())
    db.add(
        Promotion(
            name=name or "Bulk promo",
            promo_type=promo_type,
            value=value,
            product_ids=ids,
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/promotions", status_code=303)


@router.get("/newsletter", response_class=HTMLResponse)
def newsletter_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    subs = db.query(NewsletterSubscriber).order_by(NewsletterSubscriber.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/newsletter.html",
        {
            "request": request,
            "user": user,
            "subs": subs,
            "app_name": settings.app_name,
            "sent": request.query_params.get("sent"),
        },
    )


@router.post("/newsletter/send")
def newsletter_send(
    request: Request,
    subject: str = Form(...),
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.email import send_mail

    subs = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.active.is_(True)).all()
    n = 0
    for s in subs:
        if send_mail(to=s.email, subject=subject.strip(), body=body.strip()):
            n += 1
    return RedirectResponse(f"/admin/newsletter?sent={n}", status_code=303)


@router.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request, db: Session = Depends(get_db)):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    orders = (
        db.query(Order)
        .options(joinedload(Order.shipments), joinedload(Order.lines))
        .order_by(Order.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "admin/orders.html",
        {"request": request, "user": user, "orders": orders, "app_name": settings.app_name},
    )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    order = (
        db.query(Order)
        .options(joinedload(Order.shipments), joinedload(Order.lines))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        return RedirectResponse("/admin/orders", status_code=302)
    return templates.TemplateResponse(
        "admin/order_detail.html",
        {"request": request, "user": user, "order": order, "app_name": settings.app_name},
    )


@router.post("/orders/{order_id}/status")
def order_status(
    order_id: int,
    request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        old = order.status
        order.status = status
        db.commit()
        from app.services.webhooks import emit_order_event, load_order

        full = load_order(db, order.id)
        if full:
            emit_order_event(db, "order.status_changed", full, extra={"previous_status": old})
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=303)


@router.post("/orders/{order_id}/szamlazz")
def order_szamlazz_issue(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        from app.services.szamlazz import issue_invoice

        issue_invoice(db, order, force=True)
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=303)


@router.post("/orders/{order_id}/shipment/{shipment_id}")
def order_shipment_update(
    order_id: int,
    shipment_id: int,
    request: Request,
    tracking_code: str = Form(""),
    shipment_status: str = Form("pending"),
    db: Session = Depends(get_db),
):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.models import OrderShipment
    from app.services.webhooks import emit_order_event, load_order

    sh = db.query(OrderShipment).filter(OrderShipment.id == shipment_id, OrderShipment.order_id == order_id).first()
    if sh:
        sh.tracking_code = tracking_code.strip()
        sh.status = shipment_status.strip() or sh.status
        db.commit()
        full = load_order(db, order_id)
        if full:
            emit_order_event(db, "shipment.updated", full)
        _sync_order_fulfillment(db, order_id)
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=303)


@router.post("/orders/{order_id}/shipment/{shipment_id}/label")
def order_shipment_label(
    order_id: int,
    shipment_id: int,
    request: Request,
    carrier: str = Form("gls"),
    db: Session = Depends(get_db),
):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.models import OrderShipment
    from app.services.carriers import create_shipping_label

    sh = db.query(OrderShipment).filter(OrderShipment.id == shipment_id, OrderShipment.order_id == order_id).first()
    if sh:
        create_shipping_label(db, sh, carrier=carrier)
        _sync_order_fulfillment(db, order_id)
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=303)


@router.post("/orders/{order_id}/shipment/{shipment_id}/sync")
def order_shipment_sync(
    order_id: int,
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_staff_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.models import OrderShipment
    from app.services.carriers import sync_tracking

    sh = db.query(OrderShipment).filter(OrderShipment.id == shipment_id, OrderShipment.order_id == order_id).first()
    if sh:
        sync_tracking(db, sh)
        _sync_order_fulfillment(db, order_id)
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=303)


def _sync_order_fulfillment(db: Session, order_id: int) -> None:
    """Partial fulfill: ha minden shipment shipped/delivered → order fulfilled."""
    from app.models import OrderShipment

    order = db.get(Order, order_id)
    if not order or not order.shipments:
        return
    statuses = {(s.status or "pending") for s in order.shipments}
    done = {"shipped", "delivered"}
    if statuses and statuses.issubset(done):
        if order.status not in ("cancelled", "refunded"):
            order.status = "fulfilled"
            db.commit()
    elif statuses & done and order.status not in ("cancelled", "refunded", "fulfilled"):
        # részben teljesítve — status mezőben partial jelzés a UI-nak (paid/pending mellett)
        if order.status in ("pending", "paid"):
            order.status = "partial"
            db.commit()


@router.get("/warehouses", response_class=HTMLResponse)
def warehouses_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.models import Warehouse

    rows = db.query(Warehouse).order_by(Warehouse.is_default.desc(), Warehouse.code).all()
    return templates.TemplateResponse(
        "admin/warehouses.html",
        {"request": request, "user": user, "warehouses": rows, "app_name": settings.app_name},
    )


@router.post("/warehouses/create")
def warehouses_create(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    country: str = Form("HU"),
    city: str = Form(""),
    address: str = Form(""),
    is_default: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.models import Warehouse

    code_n = code.strip().upper()[:32]
    if code_n and not db.query(Warehouse).filter(Warehouse.code == code_n).first():
        if is_default == "1":
            for w in db.query(Warehouse).filter(Warehouse.is_default.is_(True)).all():
                w.is_default = False
        db.add(
            Warehouse(
                code=code_n,
                name=name.strip()[:255],
                country=(country or "HU").upper()[:2],
                city=city.strip()[:128],
                address=address.strip()[:255],
                active=True,
                is_default=is_default == "1",
            )
        )
        db.commit()
    return RedirectResponse("/admin/warehouses", status_code=303)


@router.get("/campaigns", response_class=HTMLResponse)
def campaigns_list(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    campaigns = db.query(Campaign).order_by(Campaign.sort_order, Campaign.id.desc()).all()
    return templates.TemplateResponse(
        "admin/campaigns.html",
        {"request": request, "user": user, "campaigns": campaigns, "app_name": settings.app_name},
    )


@router.post("/campaigns/create")
def campaigns_create(
    request: Request,
    title: str = Form(...),
    subtitle: str = Form(""),
    badge: str = Form("Kampány"),
    link_url: str = Form("/"),
    placement: str = Form("strip"),
    ab_group: str = Form(""),
    sort_order: int = Form(10),
    image_url: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    ab = (ab_group or "").strip().upper()
    if ab not in ("", "A", "B"):
        ab = ""
    db.add(
        Campaign(
            title=title.strip(),
            subtitle=subtitle.strip(),
            badge=badge.strip(),
            link_url=link_url.strip() or "/",
            placement=placement if placement in ("hero", "strip", "tile", "topbar") else "strip",
            ab_group=ab,
            sort_order=sort_order,
            image_url=image_url.strip(),
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/campaigns", status_code=303)


@router.post("/campaigns/{campaign_id}/toggle")
def campaigns_toggle(campaign_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    c = db.get(Campaign, campaign_id)
    if c:
        c.active = not bool(c.active)
        db.commit()
    return RedirectResponse("/admin/campaigns", status_code=303)


@router.get("/marketing", response_class=HTMLResponse)
def marketing_page(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    from app.services.attribution import utm_report

    base = settings.public_base_url.rstrip("/")
    return templates.TemplateResponse(
        "admin/marketing.html",
        {
            "request": request,
            "user": user,
            "app_name": settings.app_name,
            "utm_rows": utm_report(db),
            "affiliates": db.query(AffiliatePartner).order_by(AffiliatePartner.id).all(),
            "campaigns": db.query(Campaign).order_by(Campaign.placement, Campaign.id).all(),
            "feeds": {
                "google": f"{base}/feeds/google-merchant.xml",
                "meta": f"{base}/feeds/meta-catalog.xml",
                "arukereso": f"{base}/feeds/arukereso.xml",
            },
            "ok": request.query_params.get("ok"),
        },
    )


@router.post("/marketing/affiliates")
def marketing_affiliate_create(
    request: Request,
    code: str = Form(...),
    name: str = Form(""),
    commission_percent: float = Form(5.0),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    code_n = code.strip().upper()
    if code_n and not db.query(AffiliatePartner).filter(AffiliatePartner.code == code_n).first():
        db.add(
            AffiliatePartner(
                code=code_n,
                name=name.strip() or code_n,
                commission_percent=commission_percent,
                active=True,
            )
        )
        db.commit()
    return RedirectResponse("/admin/marketing?ok=1", status_code=303)


@router.get("/webhooks", response_class=HTMLResponse)
def webhooks_admin(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    endpoints = db.query(WebhookEndpoint).order_by(WebhookEndpoint.id).all()
    deliveries = db.query(WebhookDelivery).order_by(WebhookDelivery.id.desc()).limit(30).all()
    return templates.TemplateResponse(
        "admin/webhooks.html",
        {
            "request": request,
            "user": user,
            "app_name": settings.app_name,
            "webhook_enabled": settings.webhook_enabled,
            "webhook_url": settings.webhook_url,
            "endpoints": endpoints,
            "deliveries": deliveries,
            "test_result": request.session.pop("webhook_test_result", None),
        },
    )


@router.post("/webhooks/create")
def webhooks_create(
    request: Request,
    name: str = Form("ERP"),
    url: str = Form(...),
    secret: str = Form(""),
    events: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    db.add(
        WebhookEndpoint(
            name=name.strip() or "ERP",
            url=url.strip(),
            secret=secret.strip(),
            events=events.strip(),
            active=True,
        )
    )
    db.commit()
    return RedirectResponse("/admin/webhooks", status_code=303)


@router.post("/webhooks/{endpoint_id}/delete")
def webhooks_delete(endpoint_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    ep = db.get(WebhookEndpoint, endpoint_id)
    if ep:
        db.delete(ep)
        db.commit()
    return RedirectResponse("/admin/webhooks", status_code=303)


@router.post("/webhooks/test")
def webhooks_test(request: Request, db: Session = Depends(get_db)):
    user = _require_admin_html(request, db)
    if isinstance(user, RedirectResponse):
        return user
    import json

    results = dispatch_event(
        db,
        "order.created",
        {
            "id": 0,
            "order_number": "TEST-ADMIN",
            "status": "pending",
            "email": "test@whoopy.local",
            "grand_total": 1000,
            "currency": "HUF",
            "lines": [],
            "shipments": [],
        },
    )
    request.session["webhook_test_result"] = json.dumps(
        {"config_enabled": settings.webhook_enabled, "results": results},
        ensure_ascii=False,
        indent=2,
    )
    return RedirectResponse("/admin/webhooks", status_code=303)
