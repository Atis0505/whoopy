from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth / meta ──────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str = "ok"
    app: str
    domain: str
    erp_enabled: bool
    version: str = "v1"


# ── Categories ───────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: int
    google_id: int
    name: str
    full_path: str
    parent_id: Optional[int] = None
    depth: int = 0

    model_config = {"from_attributes": True}


# ── Suppliers ────────────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    code: str
    name: str
    email: str = ""
    phone: str = ""
    country: str = "HU"
    city: str = ""
    address: str = ""
    notes: str = ""
    active: bool = True


class SupplierOut(SupplierCreate):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Offers / prices ──────────────────────────────────────────────────────────

class OfferCreate(BaseModel):
    supplier_id: Optional[int] = None
    supplier_code: Optional[str] = None
    sku: str = ""
    price: float = Field(..., gt=0, description="Ár HUF-ban")
    currency: str = "HUF"
    stock: int = Field(0, ge=0)
    lead_days: int = 2
    active: bool = True


class OfferUpdate(BaseModel):
    sku: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)
    lead_days: Optional[int] = None
    active: Optional[bool] = None


class OfferOut(BaseModel):
    id: int
    product_id: int
    supplier_id: int
    sku: str
    price: float
    currency: str
    stock: int
    lead_days: int
    active: bool

    model_config = {"from_attributes": True}


class PricePatch(BaseModel):
    """Gyors ármódosítás meghirdetett ajánlatra."""
    price: float = Field(..., gt=0)
    currency: str = "HUF"


class StockPatch(BaseModel):
    stock: int = Field(..., ge=0)


class BulkPriceItem(BaseModel):
    offer_id: Optional[int] = None
    sku: Optional[str] = None
    product_slug: Optional[str] = None
    supplier_code: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: Optional[int] = Field(None, ge=0)


class BulkPriceRequest(BaseModel):
    items: list[BulkPriceItem]


class BulkPriceResult(BaseModel):
    updated: int
    errors: list[str] = []


# ── Products ─────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    slug: str
    title: str
    description: str = ""
    brand: str = ""
    gtin: str = ""
    image_url: str = ""
    weight_kg: float = 0.5
    ship_mode: str = "combinable"  # combinable | separate
    category_id: Optional[int] = None
    google_taxonomy_id: Optional[int] = None
    active: bool = True
    offers: list[OfferCreate] = []


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    gtin: Optional[str] = None
    image_url: Optional[str] = None
    weight_kg: Optional[float] = None
    ship_mode: Optional[str] = None
    category_id: Optional[int] = None
    google_taxonomy_id: Optional[int] = None
    active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    brand: str
    gtin: str
    image_url: str
    weight_kg: float
    ship_mode: str
    sold_count: int
    category_id: Optional[int] = None
    active: bool
    offers: list[OfferOut] = []

    model_config = {"from_attributes": True}


class ProductUpsert(ProductCreate):
    """Létrehoz vagy frissít slug / gtin alapján."""
    match_by: str = "slug"  # slug | gtin


# ── Orders ───────────────────────────────────────────────────────────────────

class OrderLineOut(BaseModel):
    id: int
    product_title: str
    supplier_name: str
    sku: str
    unit_price: float
    quantity: int
    line_total: float
    ship_mode: str

    model_config = {"from_attributes": True}


class OrderShipmentOut(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str
    method: str
    payment_method: str
    rate_name: str
    weight_kg: float
    shipping_price: float
    cod_fee: float
    package_count: int
    status: str
    tracking_code: str

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    order_number: str
    email: str
    full_name: str
    phone: str
    country: str
    city: str
    address: str
    zip_code: str
    status: str
    payment_method: str
    payment_status: str = "pending"
    payment_provider: str = "none"
    payment_ref: str = ""
    paid_at: Optional[datetime] = None
    subtotal: float
    discount_total: float
    shipping_total: float
    cod_fee_total: float
    grand_total: float
    currency: str
    coupon_code: str
    lang: str
    created_at: Optional[datetime] = None
    lines: list[OrderLineOut] = []
    shipments: list[OrderShipmentOut] = []

    model_config = {"from_attributes": True}


class OrderStatusPatch(BaseModel):
    status: str  # pending|paid|fulfilled|cancelled|refunded


class ShipmentTrackPatch(BaseModel):
    status: Optional[str] = None
    tracking_code: Optional[str] = None


# ── Campaigns / coupons ──────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    title: str
    subtitle: str = ""
    badge: str = "Kampány"
    image_url: str = ""
    link_url: str = "/"
    placement: str = "strip"
    sort_order: int = 10
    active: bool = True


class CampaignOut(CampaignCreate):
    id: int

    model_config = {"from_attributes": True}


class CouponCreate(BaseModel):
    code: str
    coupon_type: str = "percent"  # percent|fixed|free_shipping
    value: float = 0
    min_order: float = 0
    max_uses: int = 0
    description: str = ""
    active: bool = True


class CouponOut(CouponCreate):
    id: int
    used_count: int = 0

    model_config = {"from_attributes": True}
