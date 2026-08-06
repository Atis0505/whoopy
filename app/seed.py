from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Campaign,
    Category,
    Coupon,
    FeedSource,
    NewsletterSubscriber,
    Offer,
    PricingRule,
    Product,
    Promotion,
    ShippingRate,
    Supplier,
    User,
)
from app.services.currency import ensure_currency_rates
from app.services.taxonomy import load_taxonomy_into_db
from app.services.store_settings import ensure_default_cms_pages, get_store_settings
from app.seed_auth import hash_password


def seed_all(db: Session) -> None:
    ensure_currency_rates(db)
    _seed_users(db)
    get_store_settings(db)
    ensure_default_cms_pages(db)
    from app.services.customer_ux import seed_pickup_and_gifts

    seed_pickup_and_gifts(db)

    if db.query(Category).count() == 0:
        load_taxonomy_into_db(db)

    if db.query(Supplier).count() > 0:
        _seed_marketing(db)
        _seed_marketplace_ops(db)
        _seed_ux_demos(db)
        return

    suppliers = [
        Supplier(
            code="HU-BUD-01",
            name="Budapest Supply Kft.",
            email="orders@budapest-supply.hu",
            phone="+36 1 555 0101",
            country="HU",
            city="Budapest",
            address="Váci út 12.",
            notes="Gyors hazai feltöltés, 1–2 nap.",
            dropship_available=True,
            preferred=True,
        ),
        Supplier(
            code="EU-DE-02",
            name="EuroWare GmbH",
            email="b2b@euroware.de",
            phone="+49 30 555 0202",
            country="DE",
            city="Berlin",
            address="Alexanderplatz 1",
            notes="EU raktár, 3–5 nap.",
            dropship_available=True,
        ),
        Supplier(
            code="ASIA-CN-03",
            name="Pacific Direct Trading",
            email="sales@pacificdirect.cn",
            phone="+86 21 555 0303",
            country="CN",
            city="Shanghai",
            address="Pudong Ave 88",
            notes="Olcsó nagyker, hosszabb átfutás.",
            dropship_available=False,
        ),
    ]
    db.add_all(suppliers)
    db.commit()
    for s in suppliers:
        db.refresh(s)

    # Multi-country + payment-method shipping options
    eu_countries = ["HU", "AT", "DE", "SK", "RO", "PL", "CZ"]
    rates: list[ShippingRate] = []
    for country in eu_countries:
        # Budapest
        rates += [
            ShippingRate(
                supplier_id=suppliers[0].id, name=f"GLS Standard ({country})", country=country,
                method="courier", payment_method="prepaid", min_weight_kg=0, max_weight_kg=30,
                price=990 if country == "HU" else 2990, price_per_separate_unit=12990 if country == "HU" else 18990,
                cod_fee=0, free_above=25000 if country == "HU" else 80000, sort_order=10,
            ),
            ShippingRate(
                supplier_id=suppliers[0].id, name=f"GLS Utánvét ({country})", country=country,
                method="courier", payment_method="cod", min_weight_kg=0, max_weight_kg=30,
                price=1490 if country == "HU" else 3490, price_per_separate_unit=13990 if country == "HU" else 19990,
                cod_fee=590 if country == "HU" else 990, free_above=None, sort_order=20,
            ),
            ShippingRate(
                supplier_id=suppliers[0].id, name=f"Személyes átvétel ({country})", country=country,
                method="pickup", payment_method="any", min_weight_kg=0, max_weight_kg=999,
                price=0, price_per_separate_unit=0, cod_fee=0, sort_order=5,
            ),
        ]
        # EuroWare
        rates += [
            ShippingRate(
                supplier_id=suppliers[1].id, name=f"EU Express prepaid ({country})", country=country,
                method="express", payment_method="prepaid", min_weight_kg=0, max_weight_kg=40,
                price=3990, price_per_separate_unit=24990, cod_fee=0, free_above=80000, sort_order=10,
            ),
            ShippingRate(
                supplier_id=suppliers[1].id, name=f"EU Standard COD ({country})", country=country,
                method="courier", payment_method="cod", min_weight_kg=0, max_weight_kg=40,
                price=4490, price_per_separate_unit=26990, cod_fee=1200, sort_order=20,
            ),
            ShippingRate(
                supplier_id=suppliers[1].id, name=f"EU Invoice ({country})", country=country,
                method="courier", payment_method="invoice", min_weight_kg=0, max_weight_kg=40,
                price=4290, price_per_separate_unit=25990, cod_fee=0, sort_order=30,
            ),
        ]
        # Pacific
        rates += [
            ShippingRate(
                supplier_id=suppliers[2].id, name=f"Economy prepaid ({country})", country=country,
                method="courier", payment_method="prepaid", min_weight_kg=0, max_weight_kg=100,
                price=5490, price_per_separate_unit=29990, cod_fee=0, free_above=100000, sort_order=10,
            ),
            ShippingRate(
                supplier_id=suppliers[2].id, name=f"Economy COD ({country})", country=country,
                method="courier", payment_method="cod", min_weight_kg=0, max_weight_kg=100,
                price=6490, price_per_separate_unit=31990, cod_fee=1500, sort_order=20,
            ),
        ]
    db.add_all(rates)

    def cat(path_contains: str) -> Category | None:
        return (
            db.query(Category)
            .filter(Category.full_path.contains(path_contains))
            .order_by(Category.depth.desc())
            .first()
        )

    products_spec = [
        {
            "slug": "wireless-headphones-pro",
            "title": "Wireless Headphones Pro",
            "description": "Zajszűrős vezeték nélküli fejhallgató, 30 órás akkuidő.",
            "brand": "SoundPeak",
            "gtin": "5901234123457",
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80",
            "weight_kg": 0.35,
            "ship_mode": "combinable",
            "category": "Headphones",
            "sold_count": 128,
            "offers": [(0, "BUD-HP-001", 24990, 40, 1), (1, "EU-HP-001", 22990, 80, 4), (2, "CN-HP-001", 18990, 200, 12)],
        },
        {
            "slug": "ultrabook-14",
            "title": "Ultrabook 14\" i5 16GB",
            "description": "Könnyű üzleti laptop, 14\" IPS, 512GB SSD.",
            "brand": "NovaTech",
            "gtin": "5901234123464",
            "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&q=80",
            "weight_kg": 1.4,
            "ship_mode": "combinable",
            "category": "Laptops",
            "sold_count": 54,
            "offers": [(0, "BUD-NB-014", 289990, 8, 2), (1, "EU-NB-014", 274990, 25, 5)],
        },
        {
            "slug": "organic-dog-food-12kg",
            "title": "Organic Dog Food 12kg",
            "description": "Prémium száraz kutyaeledel, gabonamentes.",
            "brand": "PawNature",
            "gtin": "5901234123471",
            "image_url": "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=800&q=80",
            "weight_kg": 12.0,
            "ship_mode": "combinable",
            "category": "Dog Supplies",
            "sold_count": 91,
            "offers": [(0, "BUD-PET-12", 18990, 30, 1), (2, "CN-PET-12", 14990, 100, 14)],
        },
        {
            "slug": "ceramic-cookware-set",
            "title": "Ceramic Cookware Set 8 pcs",
            "description": "Kerámia bevonatú edénykészlet, indukciós.",
            "brand": "KitchenAura",
            "gtin": "5901234123488",
            "image_url": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=800&q=80",
            "weight_kg": 6.5,
            "ship_mode": "combinable",
            "category": "Kitchen",
            "sold_count": 37,
            "offers": [(1, "EU-KIT-08", 45990, 18, 4), (2, "CN-KIT-08", 34990, 60, 16)],
        },
        {
            "slug": "running-shoes-airflex",
            "title": "Running Shoes AirFlex",
            "description": "Könnyű futócipő férfi/női, több szín.",
            "brand": "StrideLab",
            "gtin": "5901234123495",
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80",
            "weight_kg": 0.8,
            "ship_mode": "combinable",
            "category": "Shoes",
            "sold_count": 176,
            "offers": [(0, "BUD-SH-AF", 32990, 22, 1), (1, "EU-SH-AF", 29990, 50, 3), (2, "CN-SH-AF", 24990, 120, 10)],
        },
        {
            "slug": "espresso-machine-compact",
            "title": "Compact Espresso Machine",
            "description": "15 bar, tejhabosító, kompakt kávéfőző.",
            "brand": "BrewHouse",
            "gtin": "5901234123501",
            "image_url": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=800&q=80",
            "weight_kg": 4.2,
            "ship_mode": "combinable",
            "category": "Household Appliances",
            "sold_count": 63,
            "offers": [(0, "BUD-CF-01", 79990, 12, 2), (1, "EU-CF-01", 74990, 20, 5)],
        },
        {
            "slug": "baby-soft-blocks",
            "title": "Baby Soft Blocks Set",
            "description": "Puha építőkockák 6 hónapos kortól.",
            "brand": "TinyPlay",
            "gtin": "5901234123518",
            "image_url": "https://images.unsplash.com/photo-1515488042361-ee00e88238f0?w=800&q=80",
            "weight_kg": 0.6,
            "ship_mode": "combinable",
            "category": "Baby Toys",
            "sold_count": 84,
            "offers": [(0, "BUD-BB-01", 8990, 35, 1), (2, "CN-BB-01", 5990, 200, 12)],
        },
        {
            "slug": "vitamin-c-complex",
            "title": "Vitamin C Complex 90 caps",
            "description": "Napi vitamin C + cink formula.",
            "brand": "VitalDay",
            "gtin": "5901234123525",
            "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&q=80",
            "weight_kg": 0.2,
            "ship_mode": "combinable",
            "category": "Health Care",
            "sold_count": 210,
            "offers": [(0, "BUD-VC-90", 4990, 100, 1), (1, "EU-VC-90", 4490, 150, 3)],
        },
        {
            "slug": "oak-wardrobe-2door",
            "title": "Oak Wardrobe 2-door",
            "description": "Masszív tölgy szekrény – minden darab külön szállítmányként megy (nem csomagolható össze).",
            "brand": "HomeForge",
            "gtin": "5901234123532",
            "image_url": "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=800&q=80",
            "weight_kg": 48.0,
            "ship_mode": "separate",
            "category": "Furniture",
            "sold_count": 12,
            "offers": [(0, "BUD-WR-2D", 129990, 6, 5), (1, "EU-WR-2D", 119990, 10, 8)],
        },
    ]

    for spec in products_spec:
        category = cat(spec["category"])
        product = Product(
            slug=spec["slug"],
            title=spec["title"],
            description=spec["description"],
            brand=spec["brand"],
            gtin=spec["gtin"],
            image_url=spec["image_url"],
            weight_kg=spec["weight_kg"],
            ship_mode=spec["ship_mode"],
            sold_count=spec.get("sold_count", 0),
            category_id=category.id if category else None,
            active=True,
        )
        db.add(product)
        db.flush()
        for supplier_idx, sku, price, stock, lead in spec["offers"]:
            cost = round(price * 0.72, 0)
            db.add(
                Offer(
                    product_id=product.id,
                    supplier_id=suppliers[supplier_idx].id,
                    sku=sku,
                    price=price,
                    cost_price=cost,
                    currency="HUF",
                    stock=stock,
                    lead_days=lead,
                    active=True,
                )
            )

    db.commit()
    _seed_marketing(db)
    _seed_marketplace_ops(db)
    _seed_ux_demos(db)


def _seed_ux_demos(db: Session) -> None:
    """Variáns demo + vásárlói pontok a demo usernek."""
    user = db.query(User).filter(User.email == "vasarlo@whoopy.local").first()
    if user and (user.loyalty_points or 0) < 100:
        user.loyalty_points = 500
        user.loyalty_tier = "silver"

    tee = db.query(Product).filter(Product.slug == "wireless-headphones-pro").first()
    if not tee:
        tee = db.query(Product).order_by(Product.id.asc()).first()
    if tee and not (tee.variant_axes or "").strip():
        tee.variant_axes = "Szín"
        offers = db.query(Offer).filter(Offer.product_id == tee.id).all()
        if offers:
            offers[0].variant_label = "Fekete"
            if len(offers) > 1:
                offers[1].variant_label = "Fehér"
            else:
                # második változat ugyanattól a beszállítótól
                o0 = offers[0]
                db.add(
                    Offer(
                        product_id=tee.id,
                        supplier_id=o0.supplier_id,
                        sku=f"{o0.sku}-W",
                        price=o0.price + 500,
                        cost_price=o0.cost_price,
                        stock=max(5, o0.stock // 2),
                        lead_days=o0.lead_days,
                        active=True,
                        variant_label="Fehér",
                    )
                )
    db.commit()


def _seed_users(db: Session) -> None:
    demo_users = [
        (settings.admin_email, settings.admin_password, "Whoopy Admin", "admin", True),
        ("admin@market.local", "admin1234", "Whoopy Admin", "admin", True),
        ("dolgozo@whoopy.local", "worker123", "Whoopy Dolgozó", "worker", False),
        ("vasarlo@whoopy.local", "vasarlo123", "Minta Vásárló", "customer", False),
    ]
    for email, password, name, role, is_admin in demo_users:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.role = role
            existing.is_admin = is_admin
            continue
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                full_name=name,
                role=role,
                is_admin=is_admin,
                newsletter_opt_in=(role == "customer"),
            )
        )
    db.commit()


def _seed_marketing(db: Session) -> None:
    if db.query(Coupon).count() == 0:
        db.add_all(
            [
                Coupon(code="WELCOME10", coupon_type="percent", value=10, min_order=5000, max_uses=0, description="10% új vásárlóknak"),
                Coupon(code="SAVE2000", coupon_type="fixed", value=2000, min_order=15000, max_uses=100, description="2000 Ft kedvezmény"),
                Coupon(code="FREESHIP", coupon_type="free_shipping", value=0, min_order=0, max_uses=0, description="Ingyenes szállítás"),
            ]
        )
    if db.query(Promotion).count() == 0:
        products = db.query(Product).filter(Product.slug.in_(["wireless-headphones-pro", "running-shoes-airflex"])).all()
        ids = ",".join(str(p.id) for p in products)
        db.add(
            Promotion(
                name="Tavaszi 15% szezon",
                promo_type="percent",
                value=15,
                active=True,
                starts_at=datetime.utcnow() - timedelta(days=1),
                ends_at=datetime.utcnow() + timedelta(days=60),
                product_ids=ids,
            )
        )
    if db.query(Campaign).count() == 0:
        db.add_all(
            [
                Campaign(
                    title="Tavaszi nagykampány",
                    subtitle="Válogatott elektronikára és sportcikkekre extra kedvezmény – kupon: WELCOME10",
                    badge="Kampány",
                    image_url="https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&q=80",
                    link_url="/?q=headphones",
                    placement="hero",
                    sort_order=1,
                    active=True,
                    starts_at=datetime.utcnow() - timedelta(days=1),
                    ends_at=datetime.utcnow() + timedelta(days=30),
                ),
                Campaign(
                    title="Ingyenes szállítás hétvége",
                    subtitle="Használd a FREESHIP kupont a kosárban.",
                    badge="Heti ajánlat",
                    link_url="/cart",
                    placement="strip",
                    sort_order=2,
                    active=True,
                ),
                Campaign(
                    title="Lakberendezés napok",
                    subtitle="Szekrények és konyhai termékek – figyelj a külön szállításra.",
                    badge="Új",
                    link_url="/c/111",
                    placement="tile",
                    sort_order=3,
                    active=True,
                ),
                Campaign(
                    title="Állateledel akció",
                    subtitle="A legnépszerűbb tápok most kedvezőbb áron.",
                    badge="Népszerű",
                    link_url="/c/2",
                    placement="tile",
                    sort_order=4,
                    active=True,
                ),
            ]
        )
    if db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == "demo@whoopy.local").first() is None:
        db.add(NewsletterSubscriber(email="demo@whoopy.local", lang="hu", active=True, source="seed"))
    db.commit()


def _seed_marketplace_ops(db: Session) -> None:
    """Árazás / feed seed — idempotens."""
    if db.query(PricingRule).count() == 0:
        db.add_all(
            [
                PricingRule(
                    name="Alap árrés 25%",
                    rule_type="margin_percent",
                    value=25,
                    min_margin_percent=15,
                    priority=100,
                    active=True,
                ),
                PricingRule(
                    name="Buy-box: legolcsóbb",
                    rule_type="buybox",
                    value=0,
                    buybox_mode="cheapest",
                    priority=10,
                    active=True,
                ),
            ]
        )
    first = db.query(Supplier).order_by(Supplier.id).first()
    if first and db.query(FeedSource).count() == 0:
        db.add(
            FeedSource(
                supplier_id=first.id,
                name="Minta CSV feltöltés",
                source_type="csv",
                url="",
                field_map="",
                active=True,
            )
        )
    db.commit()
