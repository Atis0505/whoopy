from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    # customer | worker | admin
    role: Mapped[str] = mapped_column(String(16), default="customer", index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # legacy mirror of role==admin
    newsletter_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_lang: Mapped[str] = mapped_column(String(5), default="hu")
    preferred_currency: Mapped[str] = mapped_column(String(3), default="HUF")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

    @property
    def is_staff(self) -> bool:
        return self.role in ("admin", "worker") or self.is_admin


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    google_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    full_path: Mapped[str] = mapped_column(String(1024), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)

    parent: Mapped[Optional["Category"]] = relationship(remote_side=[id], backref="children")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    country: Mapped[str] = mapped_column(String(2), default="HU")
    city: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offers: Mapped[list["Offer"]] = relationship(back_populates="supplier")
    shipping_rates: Mapped[list["ShippingRate"]] = relationship(back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(128), default="")
    gtin: Mapped[str] = mapped_column(String(32), default="")
    image_url: Mapped[str] = mapped_column(String(512), default="")
    weight_kg: Mapped[float] = mapped_column(Float, default=0.5)
    # combinable = small items share one parcel; separate = each unit ships alone (e.g. wardrobe)
    ship_mode: Mapped[str] = mapped_column(String(16), default="combinable")
    sold_count: Mapped[int] = mapped_column(Integer, default=0)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped[Optional[Category]] = relationship(back_populates="products")
    offers: Mapped[list["Offer"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    sku: Mapped[str] = mapped_column(String(128), default="")
    price: Mapped[float] = mapped_column(Float)  # always stored in HUF
    currency: Mapped[str] = mapped_column(String(3), default="HUF")
    stock: Mapped[int] = mapped_column(Integer, default=0)
    lead_days: Mapped[int] = mapped_column(Integer, default=2)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped[Product] = relationship(back_populates="offers")
    supplier: Mapped[Supplier] = relationship(back_populates="offers")


class ShippingRate(Base):
    """Shipping option per supplier / country / payment style."""

    __tablename__ = "shipping_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), default="Standard")
    country: Mapped[str] = mapped_column(String(2), default="HU", index=True)
    method: Mapped[str] = mapped_column(String(64), default="courier")  # courier|pickup|express|parcel
    # any | prepaid | cod | invoice
    payment_method: Mapped[str] = mapped_column(String(16), default="any")
    min_weight_kg: Mapped[float] = mapped_column(Float, default=0.0)
    max_weight_kg: Mapped[float] = mapped_column(Float, default=999.0)
    price: Mapped[float] = mapped_column(Float)  # base / combined parcel price (HUF)
    # For ship_mode=separate: charged once per unit (cabinet)
    price_per_separate_unit: Mapped[float] = mapped_column(Float, default=0.0)
    cod_fee: Mapped[float] = mapped_column(Float, default=0.0)  # added when payment=cod
    free_above: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    supplier: Mapped[Supplier] = relationship(back_populates="shipping_rates")


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(2), default="HU")
    currency: Mapped[str] = mapped_column(String(3), default="HUF")
    lang: Mapped[str] = mapped_column(String(5), default="hu")
    coupon_code: Mapped[str] = mapped_column(String(64), default="")
    # JSON-ish: "supplier_id:rate_id,supplier_id:rate_id"
    shipping_choices: Mapped[str] = mapped_column(String(512), default="")
    payment_preference: Mapped[str] = mapped_column(String(16), default="prepaid")  # prepaid|cod|invoice
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "offer_id", name="uq_cart_offer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    cart: Mapped[Cart] = relationship(back_populates="items")
    offer: Mapped[Offer] = relationship()


class Campaign(Base):
    """Homepage / category promo campaigns (banner strips)."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str] = mapped_column(String(512), default="")
    badge: Mapped[str] = mapped_column(String(64), default="")  # pl. Kampány, Heti ajánlat
    image_url: Mapped[str] = mapped_column(String(512), default="")
    link_url: Mapped[str] = mapped_column(String(512), default="/")
    # hero | strip | tile
    placement: Mapped[str] = mapped_column(String(16), default="strip")
    sort_order: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class StoreSettings(Base):
    """Singleton-ish store configuration (Shopify Settings analogue)."""

    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_name: Mapped[str] = mapped_column(String(128), default="Whoopy")
    domain: Mapped[str] = mapped_column(String(128), default="whoopy.hu")
    support_email: Mapped[str] = mapped_column(String(255), default="info@whoopy.hu")
    support_phone: Mapped[str] = mapped_column(String(64), default="")
    default_currency: Mapped[str] = mapped_column(String(3), default="HUF")
    default_country: Mapped[str] = mapped_column(String(2), default="HU")
    default_lang: Mapped[str] = mapped_column(String(5), default="hu")
    tax_rate_percent: Mapped[float] = mapped_column(Float, default=27.0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    order_prefix: Mapped[str] = mapped_column(String(16), default="TM")
    erp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    erp_api_base: Mapped[str] = mapped_column(String(255), default="http://127.0.0.1:8010/api/v1")
    google_feed_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CmsPage(Base):
    __tablename__ = "cms_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # percent | fixed | free_shipping
    coupon_type: Mapped[str] = mapped_column(String(32), default="percent")
    value: Mapped[float] = mapped_column(Float, default=0)  # % or HUF
    min_order: Mapped[float] = mapped_column(Float, default=0)
    max_uses: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class Promotion(Base):
    """Bulk product discount campaign."""

    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    # percent | fixed
    promo_type: Mapped[str] = mapped_column(String(16), default="percent")
    value: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # comma-separated product ids, empty = all products
    product_ids: Mapped[str] = mapped_column(Text, default="")
    category_ids: Mapped[str] = mapped_column(Text, default="")


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    lang: Mapped[str] = mapped_column(String(5), default="hu")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(64), default="footer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    # 1 unit of currency = rate_to_huf HUF
    rate_to_huf: Mapped[float] = mapped_column(Float)
    symbol: Mapped[str] = mapped_column(String(8), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(64), default="")
    country: Mapped[str] = mapped_column(String(2), default="HU")
    city: Mapped[str] = mapped_column(String(128))
    address: Mapped[str] = mapped_column(String(255))
    zip_code: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    payment_method: Mapped[str] = mapped_column(String(16), default="prepaid")
    # pending | awaiting | paid | failed | cancelled | refunded
    payment_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # none | demo | stripe | simplepay
    payment_provider: Mapped[str] = mapped_column(String(32), default="none")
    payment_ref: Mapped[str] = mapped_column(String(255), default="")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    discount_total: Mapped[float] = mapped_column(Float, default=0)
    shipping_total: Mapped[float] = mapped_column(Float, default=0)
    cod_fee_total: Mapped[float] = mapped_column(Float, default=0)
    grand_total: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="HUF")
    coupon_code: Mapped[str] = mapped_column(String(64), default="")
    lang: Mapped[str] = mapped_column(String(5), default="hu")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped[Optional[User]] = relationship(back_populates="orders")
    lines: Mapped[list["OrderLine"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    shipments: Mapped[list["OrderShipment"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    offer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("offers.id"), nullable=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    product_title: Mapped[str] = mapped_column(String(255))
    supplier_name: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(128), default="")
    unit_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    ship_mode: Mapped[str] = mapped_column(String(16), default="combinable")

    order: Mapped[Order] = relationship(back_populates="lines")


class OrderShipment(Base):
    __tablename__ = "order_shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    supplier_name: Mapped[str] = mapped_column(String(255))
    method: Mapped[str] = mapped_column(String(64), default="courier")
    payment_method: Mapped[str] = mapped_column(String(16), default="prepaid")
    rate_name: Mapped[str] = mapped_column(String(128), default="")
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    shipping_price: Mapped[float] = mapped_column(Float, default=0)
    cod_fee: Mapped[float] = mapped_column(Float, default=0)
    package_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    tracking_code: Mapped[str] = mapped_column(String(128), default="")

    order: Mapped[Order] = relationship(back_populates="shipments")
