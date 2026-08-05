"""Whoopy Management API v1 — ERP / automation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api_auth import require_api_key
from app.config import settings
from app.database import get_db
from app.models import (
    Campaign,
    Category,
    Coupon,
    Offer,
    Order,
    OrderShipment,
    Product,
    Supplier,
)
from app.schemas import (
    BulkPriceRequest,
    BulkPriceResult,
    CampaignCreate,
    CampaignOut,
    CategoryOut,
    CouponCreate,
    CouponOut,
    HealthOut,
    OfferCreate,
    OfferOut,
    OfferUpdate,
    OrderOut,
    OrderStatusPatch,
    PricePatch,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    ProductUpsert,
    ShipmentTrackPatch,
    StockPatch,
    SupplierCreate,
    SupplierOut,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["API v1"],
    dependencies=[Depends(require_api_key)],
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _resolve_category(db: Session, category_id: int | None, google_taxonomy_id: int | None) -> int | None:
    if category_id:
        cat = db.get(Category, category_id)
        if not cat:
            raise HTTPException(404, f"category_id={category_id} nem található")
        return cat.id
    if google_taxonomy_id:
        cat = db.query(Category).filter(Category.google_id == google_taxonomy_id).first()
        if not cat:
            raise HTTPException(404, f"google_taxonomy_id={google_taxonomy_id} nem található")
        return cat.id
    return None


def _resolve_supplier(db: Session, supplier_id: int | None, supplier_code: str | None) -> Supplier:
    if supplier_id:
        s = db.get(Supplier, supplier_id)
        if not s:
            raise HTTPException(404, f"supplier_id={supplier_id} nem található")
        return s
    if supplier_code:
        s = db.query(Supplier).filter(Supplier.code == supplier_code).first()
        if not s:
            raise HTTPException(404, f"supplier_code={supplier_code} nem található")
        return s
    raise HTTPException(400, "supplier_id vagy supplier_code kötelező")


def _product_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        slug=p.slug,
        title=p.title,
        description=p.description,
        brand=p.brand,
        gtin=p.gtin,
        image_url=p.image_url,
        weight_kg=p.weight_kg,
        ship_mode=p.ship_mode,
        sold_count=p.sold_count,
        category_id=p.category_id,
        active=p.active,
        offers=[OfferOut.model_validate(o) for o in (p.offers or [])],
    )


def _order_out(o: Order) -> OrderOut:
    return OrderOut.model_validate(o)


def _apply_offers(db: Session, product: Product, offers: list[OfferCreate]) -> None:
    for oc in offers:
        supplier = _resolve_supplier(db, oc.supplier_id, oc.supplier_code)
        existing = (
            db.query(Offer)
            .filter(Offer.product_id == product.id, Offer.supplier_id == supplier.id)
            .first()
        )
        if existing:
            existing.sku = oc.sku or existing.sku
            existing.price = oc.price
            existing.currency = oc.currency
            existing.stock = oc.stock
            existing.lead_days = oc.lead_days
            existing.active = oc.active
        else:
            db.add(
                Offer(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    sku=oc.sku,
                    price=oc.price,
                    currency=oc.currency,
                    stock=oc.stock,
                    lead_days=oc.lead_days,
                    active=oc.active,
                )
            )


# ── Health (no extra deps beyond API key) ────────────────────────────────────

@router.get("/health", response_model=HealthOut, tags=["Meta"])
def api_health():
    return HealthOut(
        app=settings.app_name,
        domain=settings.app_domain,
        erp_enabled=settings.erp_enabled,
    )


# ── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryOut], tags=["Catalog"])
def list_categories(
    q: str | None = None,
    depth: int | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Category)
    if q:
        like = f"%{q}%"
        query = query.filter((Category.name.ilike(like)) | (Category.full_path.ilike(like)))
    if depth is not None:
        query = query.filter(Category.depth == depth)
    rows = query.order_by(Category.full_path).offset(offset).limit(limit).all()
    return [CategoryOut.model_validate(c) for c in rows]


@router.get("/categories/{category_id}", response_model=CategoryOut, tags=["Catalog"])
def get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Kategória nem található")
    return CategoryOut.model_validate(cat)


# ── Suppliers ────────────────────────────────────────────────────────────────

@router.get("/suppliers", response_model=list[SupplierOut], tags=["Catalog"])
def list_suppliers(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Supplier)
    if active_only:
        q = q.filter(Supplier.active.is_(True))
    return [SupplierOut.model_validate(s) for s in q.order_by(Supplier.code).all()]


@router.post("/suppliers", response_model=SupplierOut, status_code=201, tags=["Catalog"])
def create_supplier(body: SupplierCreate, db: Session = Depends(get_db)):
    if db.query(Supplier).filter(Supplier.code == body.code).first():
        raise HTTPException(409, f"supplier code={body.code} már létezik")
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return SupplierOut.model_validate(s)


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut, tags=["Catalog"])
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    s = db.get(Supplier, supplier_id)
    if not s:
        raise HTTPException(404, "Beszállító nem található")
    return SupplierOut.model_validate(s)


# ── Products ─────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductOut], tags=["Products"])
def list_products(
    q: str | None = None,
    active_only: bool = False,
    category_id: int | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Product).options(joinedload(Product.offers))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Product.title.ilike(like)) | (Product.slug.ilike(like)) | (Product.gtin.ilike(like))
        )
    if active_only:
        query = query.filter(Product.active.is_(True))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    rows = query.order_by(Product.id.desc()).offset(offset).limit(limit).all()
    return [_product_out(p) for p in rows]


@router.get("/products/by-slug/{slug}", response_model=ProductOut, tags=["Products"])
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    p = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.slug == slug)
        .first()
    )
    if not p:
        raise HTTPException(404, "Termék nem található")
    return _product_out(p)


@router.get("/products/{product_id}", response_model=ProductOut, tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.id == product_id)
        .first()
    )
    if not p:
        raise HTTPException(404, "Termék nem található")
    return _product_out(p)


@router.post("/products", response_model=ProductOut, status_code=201, tags=["Products"])
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.slug == body.slug).first():
        raise HTTPException(409, f"slug={body.slug} már létezik — használd PUT /products/upsert")
    cat_id = _resolve_category(db, body.category_id, body.google_taxonomy_id)
    if body.ship_mode not in ("combinable", "separate"):
        raise HTTPException(400, "ship_mode: combinable | separate")
    p = Product(
        slug=body.slug,
        title=body.title,
        description=body.description,
        brand=body.brand,
        gtin=body.gtin,
        image_url=body.image_url,
        weight_kg=body.weight_kg,
        ship_mode=body.ship_mode,
        category_id=cat_id,
        active=body.active,
    )
    db.add(p)
    db.flush()
    if body.offers:
        _apply_offers(db, p, body.offers)
    db.commit()
    p = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.id == p.id)
        .first()
    )
    return _product_out(p)


@router.put("/products/upsert", response_model=ProductOut, tags=["Products"])
def upsert_product(body: ProductUpsert, db: Session = Depends(get_db)):
    """Létrehoz vagy frissít slug / gtin alapján — ideális ERP szinkronhoz."""
    existing = None
    if body.match_by == "gtin" and body.gtin:
        existing = db.query(Product).filter(Product.gtin == body.gtin).first()
    if not existing:
        existing = db.query(Product).filter(Product.slug == body.slug).first()

    cat_id = _resolve_category(db, body.category_id, body.google_taxonomy_id)
    if body.ship_mode not in ("combinable", "separate"):
        raise HTTPException(400, "ship_mode: combinable | separate")

    if existing:
        existing.title = body.title
        existing.description = body.description
        existing.brand = body.brand
        existing.gtin = body.gtin or existing.gtin
        existing.image_url = body.image_url or existing.image_url
        existing.weight_kg = body.weight_kg
        existing.ship_mode = body.ship_mode
        existing.active = body.active
        if cat_id is not None:
            existing.category_id = cat_id
        p = existing
    else:
        p = Product(
            slug=body.slug,
            title=body.title,
            description=body.description,
            brand=body.brand,
            gtin=body.gtin,
            image_url=body.image_url,
            weight_kg=body.weight_kg,
            ship_mode=body.ship_mode,
            category_id=cat_id,
            active=body.active,
        )
        db.add(p)
        db.flush()

    if body.offers:
        _apply_offers(db, p, body.offers)
    db.commit()
    p = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.id == p.id)
        .first()
    )
    return _product_out(p)


@router.patch("/products/{product_id}", response_model=ProductOut, tags=["Products"])
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Termék nem található")
    data = body.model_dump(exclude_unset=True)
    google_id = data.pop("google_taxonomy_id", None)
    if "category_id" in data or google_id is not None:
        cat_id = _resolve_category(db, data.get("category_id"), google_id)
        if cat_id is not None:
            data["category_id"] = cat_id
    if "ship_mode" in data and data["ship_mode"] not in ("combinable", "separate"):
        raise HTTPException(400, "ship_mode: combinable | separate")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    p = (
        db.query(Product)
        .options(joinedload(Product.offers))
        .filter(Product.id == product_id)
        .first()
    )
    return _product_out(p)


@router.delete("/products/{product_id}", status_code=204, tags=["Products"])
def delete_product(product_id: int, hard: bool = False, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Termék nem található")
    if hard:
        db.delete(p)
    else:
        p.active = False
    db.commit()
    return None


# ── Offers / prices / stock ──────────────────────────────────────────────────

@router.get("/offers", response_model=list[OfferOut], tags=["Offers"])
def list_offers(
    product_id: int | None = None,
    supplier_id: int | None = None,
    sku: str | None = None,
    active_only: bool = False,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Offer)
    if product_id:
        q = q.filter(Offer.product_id == product_id)
    if supplier_id:
        q = q.filter(Offer.supplier_id == supplier_id)
    if sku:
        q = q.filter(Offer.sku == sku)
    if active_only:
        q = q.filter(Offer.active.is_(True))
    rows = q.order_by(Offer.id.desc()).offset(offset).limit(limit).all()
    return [OfferOut.model_validate(o) for o in rows]


@router.post(
    "/products/{product_id}/offers",
    response_model=OfferOut,
    status_code=201,
    tags=["Offers"],
)
def add_offer(product_id: int, body: OfferCreate, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Termék nem található")
    supplier = _resolve_supplier(db, body.supplier_id, body.supplier_code)
    existing = (
        db.query(Offer)
        .filter(Offer.product_id == product_id, Offer.supplier_id == supplier.id)
        .first()
    )
    if existing:
        raise HTTPException(409, "Ehhez a beszállítóhoz már van ajánlat — PATCH /offers/{id}")
    o = Offer(
        product_id=product_id,
        supplier_id=supplier.id,
        sku=body.sku,
        price=body.price,
        currency=body.currency,
        stock=body.stock,
        lead_days=body.lead_days,
        active=body.active,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return OfferOut.model_validate(o)


@router.patch("/offers/{offer_id}", response_model=OfferOut, tags=["Offers"])
def update_offer(offer_id: int, body: OfferUpdate, db: Session = Depends(get_db)):
    o = db.get(Offer, offer_id)
    if not o:
        raise HTTPException(404, "Ajánlat nem található")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return OfferOut.model_validate(o)


@router.patch("/offers/{offer_id}/price", response_model=OfferOut, tags=["Offers"])
def patch_offer_price(offer_id: int, body: PricePatch, db: Session = Depends(get_db)):
    """Gyors ármódosítás már meghirdetett terméknél."""
    o = db.get(Offer, offer_id)
    if not o:
        raise HTTPException(404, "Ajánlat nem található")
    o.price = body.price
    o.currency = body.currency
    db.commit()
    db.refresh(o)
    return OfferOut.model_validate(o)


@router.patch("/offers/{offer_id}/stock", response_model=OfferOut, tags=["Offers"])
def patch_offer_stock(offer_id: int, body: StockPatch, db: Session = Depends(get_db)):
    o = db.get(Offer, offer_id)
    if not o:
        raise HTTPException(404, "Ajánlat nem található")
    o.stock = body.stock
    db.commit()
    db.refresh(o)
    return OfferOut.model_validate(o)


@router.post("/offers/bulk-price", response_model=BulkPriceResult, tags=["Offers"])
def bulk_update_prices(body: BulkPriceRequest, db: Session = Depends(get_db)):
    """Tömeges ármódosítás — ERP árszinkronhoz."""
    updated = 0
    errors: list[str] = []
    for i, item in enumerate(body.items):
        offer = None
        try:
            if item.offer_id:
                offer = db.get(Offer, item.offer_id)
            elif item.sku:
                offer = db.query(Offer).filter(Offer.sku == item.sku).first()
            elif item.product_slug and item.supplier_code:
                product = db.query(Product).filter(Product.slug == item.product_slug).first()
                supplier = db.query(Supplier).filter(Supplier.code == item.supplier_code).first()
                if product and supplier:
                    offer = (
                        db.query(Offer)
                        .filter(Offer.product_id == product.id, Offer.supplier_id == supplier.id)
                        .first()
                    )
            if not offer:
                errors.append(f"[{i}] ajánlat nem található")
                continue
            offer.price = item.price
            if item.stock is not None:
                offer.stock = item.stock
            updated += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"[{i}] {exc}")
    db.commit()
    return BulkPriceResult(updated=updated, errors=errors)


@router.delete("/offers/{offer_id}", status_code=204, tags=["Offers"])
def delete_offer(offer_id: int, hard: bool = False, db: Session = Depends(get_db)):
    o = db.get(Offer, offer_id)
    if not o:
        raise HTTPException(404, "Ajánlat nem található")
    if hard:
        db.delete(o)
    else:
        o.active = False
    db.commit()
    return None


# ── Orders ───────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=list[OrderOut], tags=["Orders"])
def list_orders(
    status: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Order).options(
        joinedload(Order.lines),
        joinedload(Order.shipments),
    )
    if status:
        q = q.filter(Order.status == status)
    rows = q.order_by(Order.id.desc()).offset(offset).limit(limit).all()
    return [_order_out(o) for o in rows]


@router.get("/orders/by-number/{order_number}", response_model=OrderOut, tags=["Orders"])
def get_order_by_number(order_number: str, db: Session = Depends(get_db)):
    o = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.order_number == order_number)
        .first()
    )
    if not o:
        raise HTTPException(404, "Rendelés nem található")
    return _order_out(o)


@router.get("/orders/{order_id}", response_model=OrderOut, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.id == order_id)
        .first()
    )
    if not o:
        raise HTTPException(404, "Rendelés nem található")
    return _order_out(o)


@router.patch("/orders/{order_id}/status", response_model=OrderOut, tags=["Orders"])
def patch_order_status(order_id: int, body: OrderStatusPatch, db: Session = Depends(get_db)):
    allowed = {"pending", "paid", "fulfilled", "cancelled", "refunded"}
    if body.status not in allowed:
        raise HTTPException(400, f"status: {', '.join(sorted(allowed))}")
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Rendelés nem található")
    o.status = body.status
    db.commit()
    o = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.id == order_id)
        .first()
    )
    return _order_out(o)


@router.patch("/shipments/{shipment_id}", response_model=OrderOut, tags=["Orders"])
def patch_shipment(shipment_id: int, body: ShipmentTrackPatch, db: Session = Depends(get_db)):
    sh = db.get(OrderShipment, shipment_id)
    if not sh:
        raise HTTPException(404, "Szállítmány nem található")
    if body.status is not None:
        sh.status = body.status
    if body.tracking_code is not None:
        sh.tracking_code = body.tracking_code
    db.commit()
    o = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.id == sh.order_id)
        .first()
    )
    return _order_out(o)


# ── Campaigns / coupons ──────────────────────────────────────────────────────

@router.get("/campaigns", response_model=list[CampaignOut], tags=["Marketing"])
def list_campaigns(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Campaign)
    if active_only:
        q = q.filter(Campaign.active.is_(True))
    return [CampaignOut.model_validate(c) for c in q.order_by(Campaign.sort_order).all()]


@router.post("/campaigns", response_model=CampaignOut, status_code=201, tags=["Marketing"])
def create_campaign(body: CampaignCreate, db: Session = Depends(get_db)):
    c = Campaign(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return CampaignOut.model_validate(c)


@router.get("/coupons", response_model=list[CouponOut], tags=["Marketing"])
def list_coupons(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Coupon)
    if active_only:
        q = q.filter(Coupon.active.is_(True))
    return [CouponOut.model_validate(c) for c in q.order_by(Coupon.code).all()]


@router.post("/coupons", response_model=CouponOut, status_code=201, tags=["Marketing"])
def create_coupon(body: CouponCreate, db: Session = Depends(get_db)):
    if db.query(Coupon).filter(Coupon.code == body.code.upper()).first():
        raise HTTPException(409, "Kuponkód már létezik")
    data = body.model_dump()
    data["code"] = data["code"].upper()
    c = Coupon(**data)
    db.add(c)
    db.commit()
    db.refresh(c)
    return CouponOut.model_validate(c)
