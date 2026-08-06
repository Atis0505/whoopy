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
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    # standard | silver | gold
    loyalty_tier: Mapped[str] = mapped_column(String(16), default="standard")
    gdpr_anonymized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    # Belső beszerzés: a partner dropshipet kínál-e (nem kötelező használni)
    dropship_available: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offers: Mapped[list["Offer"]] = relationship(back_populates="supplier")
    shipping_rates: Mapped[list["ShippingRate"]] = relationship(back_populates="supplier")
    feed_sources: Mapped[list["FeedSource"]] = relationship(back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(128), default="", index=True)
    gtin: Mapped[str] = mapped_column(String(32), default="", index=True)
    image_url: Mapped[str] = mapped_column(String(512), default="")
    weight_kg: Mapped[float] = mapped_column(Float, default=0.5)
    # combinable = small items share one parcel; separate = each unit ships alone (e.g. wardrobe)
    ship_mode: Mapped[str] = mapped_column(String(16), default="combinable")
    sold_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # pl. "Szín,Méret" — UI tengelyek; értékek az Offer.variant_label-ben
    variant_axes: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped[Optional[Category]] = relationship(back_populates="products")
    offers: Mapped[list["Offer"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(512))  # public path e.g. /media/products/1/abc.jpg
    alt: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=10)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="images")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("product_id", "supplier_id", "variant_label", name="uq_product_supplier_variant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    sku: Mapped[str] = mapped_column(String(128), default="")
    price: Mapped[float] = mapped_column(Float)  # listaár HUF (bolt)
    cost_price: Mapped[float] = mapped_column(Float, default=0.0)  # beszerzési nettó HUF
    currency: Mapped[str] = mapped_column(String(3), default="HUF")
    stock: Mapped[int] = mapped_column(Integer, default=0, index=True)
    lead_days: Mapped[int] = mapped_column(Integer, default=2)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # buy-box: kézzel kiemelt forrás ehhez a termékhez
    preferred_source: Mapped[bool] = mapped_column(Boolean, default=False)
    # pl. "Piros / M" — üres = alapváltozat
    variant_label: Mapped[str] = mapped_column(String(128), default="")
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)

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
    gift_card_code: Mapped[str] = mapped_column(String(64), default="")
    loyalty_redeem_points: Mapped[int] = mapped_column(Integer, default=0)
    # courier | pickup
    delivery_mode: Mapped[str] = mapped_column(String(16), default="courier")
    pickup_provider: Mapped[str] = mapped_column(String(32), default="")  # foxpost|packeta|gls
    pickup_point_id: Mapped[str] = mapped_column(String(64), default="")
    pickup_point_label: Mapped[str] = mapped_column(String(255), default="")
    # JSON-ish: "supplier_id:rate_id,supplier_id:rate_id"
    shipping_choices: Mapped[str] = mapped_column(String(512), default="")
    payment_preference: Mapped[str] = mapped_column(String(16), default="prepaid")  # prepaid|cod|invoice
    abandoned_email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    utm_source: Mapped[str] = mapped_column(String(128), default="")
    utm_medium: Mapped[str] = mapped_column(String(128), default="")
    utm_campaign: Mapped[str] = mapped_column(String(128), default="")
    utm_content: Mapped[str] = mapped_column(String(128), default="")
    utm_term: Mapped[str] = mapped_column(String(128), default="")
    affiliate_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    is_b2b: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_vat_id: Mapped[str] = mapped_column(String(32), default="")
    reverse_charge: Mapped[bool] = mapped_column(Boolean, default=False)
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
    # hero | strip | tile | topbar (site-wide hirdetőszalag kampány)
    placement: Mapped[str] = mapped_column(String(16), default="strip")
    # "" | A | B — hero A/B teszt
    ab_group: Mapped[str] = mapped_column(String(8), default="")
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
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
    # open | catalog_only | closed  (maintenance_mode = closed legacy mirror)
    storefront_status: Mapped[str] = mapped_column(String(16), default="open")
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    maintenance_message: Mapped[str] = mapped_column(
        Text,
        default="Jelenleg a boltunk inaktív, nem üzemel — rendeléseket sem fogadunk. Hamarosan visszatérünk.",
    )
    orders_paused_message: Mapped[str] = mapped_column(
        Text,
        default="Átmenetileg nem fogadunk új rendeléseket. Böngészhetsz, de a kosár és a vásárlás szünetel.",
    )
    # Site-wide announcement / hirdetőszalag
    announcement_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    announcement_text: Mapped[str] = mapped_column(String(512), default="")
    announcement_link: Mapped[str] = mapped_column(String(512), default="")
    announcement_link_label: Mapped[str] = mapped_column(String(64), default="Részletek")
    announcement_bg: Mapped[str] = mapped_column(String(32), default="#0f766e")
    announcement_starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    announcement_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Social proof ticker + ops
    ticker_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    business_hours: Mapped[str] = mapped_column(String(255), default="H–P 9:00–17:00")
    free_shipping_threshold_huf: Mapped[float] = mapped_column(Float, default=25000.0)
    company_name: Mapped[str] = mapped_column(String(255), default="Whoopy Kft.")
    company_address: Mapped[str] = mapped_column(String(255), default="")
    company_tax_id: Mapped[str] = mapped_column(String(64), default="")  # adószám
    company_eu_vat: Mapped[str] = mapped_column(String(64), default="")  # HU12345678
    invoice_footer: Mapped[str] = mapped_column(Text, default="")
    chat_widget_html: Mapped[str] = mapped_column(Text, default="")  # Tawk/Intercom snippet
    chat_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    loyalty_earn_per_100: Mapped[float] = mapped_column(Float, default=1.0)  # pont / 100 Ft
    loyalty_point_value_huf: Mapped[float] = mapped_column(Float, default=1.0)
    pickup_fee_huf: Mapped[float] = mapped_column(Float, default=990.0)
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
    # Számlázási cím (ha üres / same → szállítási)
    billing_same: Mapped[bool] = mapped_column(Boolean, default=True)
    billing_full_name: Mapped[str] = mapped_column(String(255), default="")
    billing_country: Mapped[str] = mapped_column(String(2), default="")
    billing_city: Mapped[str] = mapped_column(String(128), default="")
    billing_address: Mapped[str] = mapped_column(String(255), default="")
    billing_zip: Mapped[str] = mapped_column(String(16), default="")
    billing_tax_id: Mapped[str] = mapped_column(String(64), default="")
    delivery_mode: Mapped[str] = mapped_column(String(16), default="courier")
    pickup_provider: Mapped[str] = mapped_column(String(32), default="")
    pickup_point_id: Mapped[str] = mapped_column(String(64), default="")
    pickup_point_label: Mapped[str] = mapped_column(String(255), default="")
    gift_card_code: Mapped[str] = mapped_column(String(64), default="")
    gift_card_amount: Mapped[float] = mapped_column(Float, default=0)
    loyalty_points_earned: Mapped[int] = mapped_column(Integer, default=0)
    loyalty_points_redeemed: Mapped[int] = mapped_column(Integer, default=0)
    loyalty_discount: Mapped[float] = mapped_column(Float, default=0)
    access_token: Mapped[str] = mapped_column(String(64), default="", index=True)
    utm_source: Mapped[str] = mapped_column(String(128), default="", index=True)
    utm_medium: Mapped[str] = mapped_column(String(128), default="")
    utm_campaign: Mapped[str] = mapped_column(String(128), default="", index=True)
    utm_content: Mapped[str] = mapped_column(String(128), default="")
    utm_term: Mapped[str] = mapped_column(String(128), default="")
    affiliate_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    is_b2b: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_vat_id: Mapped[str] = mapped_column(String(32), default="")
    reverse_charge: Mapped[bool] = mapped_column(Boolean, default=False)
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
    # ÁFA: árak bruttók; tax_total = bruttó * rate/(100+rate)
    tax_rate_percent: Mapped[float] = mapped_column(Float, default=27.0)
    tax_total: Mapped[float] = mapped_column(Float, default=0)
    net_total: Mapped[float] = mapped_column(Float, default=0)
    grand_total: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="HUF")
    coupon_code: Mapped[str] = mapped_column(String(64), default="")
    lang: Mapped[str] = mapped_column(String(5), default="hu")
    notes: Mapped[str] = mapped_column(Text, default="")
    # Számlázz.hu / HTML számla
    invoice_status: Mapped[str] = mapped_column(String(32), default="none", index=True)  # none|pending|issued|failed|skipped
    invoice_number: Mapped[str] = mapped_column(String(64), default="")
    invoice_provider: Mapped[str] = mapped_column(String(32), default="")  # html|szamlazz
    invoice_pdf_path: Mapped[str] = mapped_column(String(512), default="")
    invoice_error: Mapped[str] = mapped_column(String(512), default="")
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
    variant_label: Mapped[str] = mapped_column(String(128), default="")

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
    carrier: Mapped[str] = mapped_column(String(32), default="")  # gls|foxpost|packeta|manual
    label_ref: Mapped[str] = mapped_column(String(128), default="")
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    order: Mapped[Order] = relationship(back_populates="shipments")


class WebhookEndpoint(Base):
    """Outbound webhook cél (ERP / külső rendszer)."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="ERP")
    url: Mapped[str] = mapped_column(String(512))
    secret: Mapped[str] = mapped_column(String(255), default="")
    # comma-separated event names; empty = all
    events: Mapped[str] = mapped_column(String(512), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_id: Mapped[Optional[int]] = mapped_column(ForeignKey("webhook_endpoints.id"), nullable=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    target_url: Mapped[str] = mapped_column(String(512), default="")
    payload: Mapped[str] = mapped_column(Text, default="")
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    response_body: Mapped[str] = mapped_column(Text, default="")
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedSource(Base):
    """Partner katalógus forrás (mi húzzuk / töltjük — ők nem hirdetnek)."""

    __tablename__ = "feed_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), default="Feed")
    # csv | json | url_json | manual
    source_type: Mapped[str] = mapped_column(String(32), default="csv")
    url: Mapped[str] = mapped_column(String(512), default="")
    # JSON map: {"sku":"sku","gtin":"ean","title":"name","price":"price","stock":"qty","cost":"net"}
    field_map: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(64), default="")
    last_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supplier: Mapped[Supplier] = relationship(back_populates="feed_sources")
    runs: Mapped[list["FeedRun"]] = relationship(back_populates="feed_source", cascade="all, delete-orphan")


class FeedRun(Base):
    __tablename__ = "feed_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_source_id: Mapped[int] = mapped_column(ForeignKey("feed_sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    rows_ok: Mapped[int] = mapped_column(Integer, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")

    feed_source: Mapped[FeedSource] = relationship(back_populates="runs")


class StagingListing(Base):
    """Staging: review előtt — publish → Product+Offer."""

    __tablename__ = "staging_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    feed_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("feed_sources.id"), nullable=True)
    # pending | approved | rejected | published
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    gtin: Mapped[str] = mapped_column(String(32), default="", index=True)
    sku: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(128), default="")
    image_url: Mapped[str] = mapped_column(String(512), default="")
    cost_price: Mapped[float] = mapped_column(Float, default=0.0)
    list_price: Mapped[float] = mapped_column(Float, default=0.0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    lead_days: Mapped[int] = mapped_column(Integer, default=2)
    google_taxonomy_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ship_mode: Mapped[str] = mapped_column(String(16), default="combinable")
    reject_reason: Mapped[str] = mapped_column(String(512), default="")
    published_product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductReview(Base):
    __tablename__ = "product_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_name: Mapped[str] = mapped_column(String(128), default="")
    rating: Mapped[int] = mapped_column(Integer, default=5)
    title: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockAlert(Base):
    __tablename__ = "stock_alerts"
    __table_args__ = (UniqueConstraint("email", "product_id", name="uq_stock_alert_email_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="requested", index=True)
    admin_note: Mapped[str] = mapped_column(String(512), default="")
    # RMA
    label_code: Mapped[str] = mapped_column(String(128), default="")
    label_carrier: Mapped[str] = mapped_column(String(32), default="")
    label_path: Mapped[str] = mapped_column(String(512), default="")
    refund_status: Mapped[str] = mapped_column(String(32), default="none")  # none|pending|refunded|rejected
    refund_amount: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PricingRule(Base):
    """Listaár számítás / buy-box preferencia (belső)."""

    __tablename__ = "pricing_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    rule_type: Mapped[str] = mapped_column(String(32), default="margin_percent")
    value: Mapped[float] = mapped_column(Float, default=20.0)
    min_margin_percent: Mapped[float] = mapped_column(Float, default=0.0)
    buybox_mode: Mapped[str] = mapped_column(String(32), default="cheapest")
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GiftCard(Base):
    __tablename__ = "gift_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    initial_amount: Mapped[float] = mapped_column(Float, default=0)
    balance: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="HUF")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PickupPoint(Base):
    """Csomagpont stub (Foxpost / Packeta / GLS) — éles API később."""

    __tablename__ = "pickup_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)  # foxpost|packeta|gls
    external_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(128), default="", index=True)
    zip_code: Mapped[str] = mapped_column(String(16), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(2), default="HU")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AffiliatePartner(Base):
    """Partner / affiliate kód — UTM-mel vagy /go/aff/{code} linkkel."""

    __tablename__ = "affiliate_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    commission_percent: Mapped[float] = mapped_column(Float, default=5.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    revenue_total: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(2), default="HU")
    city: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class PriceHistory(Base):
    """Omnibus / 30 napos legalacsonyabb ár + NAV-szerű ártörténet."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    offer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("offers.id"), nullable=True)
    price: Mapped[float] = mapped_column(Float)
    previous_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="system")  # api|admin|staging|seed|snapshot
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Subscription(Base):
    """Vásárlói ismétlődő / automatikus újrarendelés."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), default="Ismétlődő rendelés")
    interval_days: Mapped[int] = mapped_column(Integer, default=30)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    email: Mapped[str] = mapped_column(String(255), default="")
    full_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    country: Mapped[str] = mapped_column(String(2), default="HU")
    city: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    zip_code: Mapped[str] = mapped_column(String(16), default="")
    payment_preference: Mapped[str] = mapped_column(String(16), default="cod")
    last_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    last_error: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lines: Mapped[list["SubscriptionLine"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    subscription: Mapped[Subscription] = relationship(back_populates="lines")
    offer: Mapped["Offer"] = relationship()


class CookieConsentLog(Base):
    __tablename__ = "cookie_consent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    choice: Mapped[str] = mapped_column(String(32), default="necessary")  # necessary|analytics|marketing|all
    analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    marketing: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
