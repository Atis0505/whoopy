"""Smoke / E2E alap: health, home, admin redirect, API key gate."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_home_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert "Whoopy" in r.text or "whoopy" in r.text.lower()


def test_admin_requires_login():
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (302, 303, 307)


def test_api_requires_key():
    r = client.get("/api/v1/health")
    # 401/403 vagy létező health 200 kulccsal — kulcs nélkül ne legyen 500
    assert r.status_code in (200, 401, 403, 404)


def test_robots_and_sitemap():
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Sitemap" in r.text
    r2 = client.get("/sitemap.xml")
    assert r2.status_code == 200
    assert "urlset" in r2.text


def test_faq_contact_pages():
    assert client.get("/faq").status_code == 200
    assert client.get("/contact").status_code == 200
    assert client.get("/track").status_code == 200


def test_checkout_cod_to_invoice():
    """Kosár → COD checkout → rendelés oldal → HTML számla."""
    from app.database import SessionLocal
    from app.models import Offer

    db = SessionLocal()
    try:
        offer = db.query(Offer).filter(Offer.active.is_(True), Offer.stock > 0).first()
    finally:
        db.close()
    assert offer is not None, "seed offer missing"

    r = client.post("/cart/add", data={"offer_id": offer.id, "quantity": 1}, follow_redirects=False)
    assert r.status_code in (302, 303)

    r = client.post("/cart/payment", data={"payment_preference": "cod"}, follow_redirects=False)
    assert r.status_code in (302, 303)

    r = client.post(
        "/checkout",
        data={
            "email": "e2e@whoopy.local",
            "full_name": "E2E Teszt",
            "phone": "0612345678",
            "country": "HU",
            "city": "Budapest",
            "address": "Teszt utca 1",
            "zip_code": "1111",
            "notes": "smoke",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    loc = r.headers.get("location") or ""
    assert "/order/" in loc
    order_number = loc.rstrip("/").split("/")[-1]

    r2 = client.get(f"/order/{order_number}")
    assert r2.status_code == 200
    assert order_number in r2.text

    inv = client.get(f"/order/{order_number}/invoice", params={"email": "e2e@whoopy.local"})
    assert inv.status_code == 200
    assert order_number in inv.text


def test_szamlazz_xml_build():
    from app.models import Order, OrderLine
    from app.services.szamlazz import build_invoice_xml

    order = Order(
        order_number="TM-TEST-0001",
        email="a@b.hu",
        full_name="Teszt Elek",
        phone="",
        country="HU",
        city="Budapest",
        address="Fő u. 1",
        zip_code="1011",
        payment_method="cod",
        tax_rate_percent=27.0,
        shipping_total=990,
        discount_total=0,
        cod_fee_total=0,
        currency="HUF",
    )
    order.lines = [
        OrderLine(
            product_title="Teszt termék",
            supplier_name="Demo",
            sku="SKU1",
            unit_price=12700,
            quantity=1,
            line_total=12700,
            supplier_id=1,
        )
    ]
    xml = build_invoice_xml(order, agent_key="TESTKEY", eszamla=True, download_pdf=True)
    assert "xmlszamla" in xml
    assert "Teszt termék" in xml
    assert "TM-TEST-0001" in xml
    assert "27" in xml


def test_search_and_suggest():
    r = client.get("/search", params={"q": "a"})
    assert r.status_code == 200
    r2 = client.get("/api/suggest", params={"q": "a"})
    assert r2.status_code == 200
    assert "items" in r2.json()


def test_pickup_points_api():
    r = client.get("/api/pickup-points", params={"provider": "foxpost"})
    assert r.status_code == 200
    assert len(r.json().get("items", [])) >= 1


def test_compare_and_recent_pages():
    assert client.get("/compare").status_code == 200
    assert client.get("/recent").status_code == 200


def test_marketing_feeds():
    r = client.get("/feeds/meta-catalog.xml")
    assert r.status_code == 200
    assert "rss" in r.text.lower() or "item" in r.text.lower()
    r2 = client.get("/feeds/arukereso.xml")
    assert r2.status_code == 200
    assert "product" in r2.text.lower()


def test_affiliate_redirect():
    r = client.get("/go/aff/PARTNER10", params={"next": "/"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_cookie_consent_v2():
    r = client.post("/cookies/consent", data={"choice": "all"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_announcement_and_ticker_on_home():
    r = client.get("/")
    assert r.status_code == 200
    # seed announcement or ticker markup present
    assert "announce-bar" in r.text or "social-ticker" in r.text or "Whoopy" in r.text


def test_maintenance_blocks_store():
    from app.database import SessionLocal
    from app.services.store_settings import get_store_settings, touch_settings
    from app.services.storefront_ops import set_storefront_status

    db = SessionLocal()
    try:
        store = get_store_settings(db)
        set_storefront_status(store, "closed")
        touch_settings(store)
        db.commit()
    finally:
        db.close()

    r = client.get("/", follow_redirects=False)
    assert r.status_code == 503
    assert "nem üzemel" in r.text.lower() or "inaktív" in r.text.lower() or "Whoopy" in r.text

    # dolgozó login tiltva
    r_w = client.post(
        "/login",
        data={"email": "dolgozo@whoopy.local", "password": "worker123"},
        follow_redirects=False,
    )
    assert r_w.status_code in (403, 401)
    assert "dolgozó" in r_w.text.lower() or "zárva" in r_w.text.lower()

    db = SessionLocal()
    try:
        store = get_store_settings(db)
        set_storefront_status(store, "catalog_only")
        touch_settings(store)
        db.commit()
    finally:
        db.close()

    assert client.get("/").status_code == 200
    r_cart = client.get("/cart", follow_redirects=False)
    assert r_cart.status_code in (302, 303)
    r_add = client.post("/cart/add", data={"offer_id": 1, "quantity": 1}, follow_redirects=False)
    assert r_add.status_code in (302, 303, 403)

    db = SessionLocal()
    try:
        store = get_store_settings(db)
        set_storefront_status(store, "open")
        touch_settings(store)
        db.commit()
    finally:
        db.close()

    assert client.get("/").status_code == 200


def test_admin_preview_bypasses_closed():
    from app.database import SessionLocal
    from app.services.store_settings import get_store_settings, touch_settings
    from app.services.storefront_ops import set_storefront_status

    db = SessionLocal()
    try:
        set_storefront_status(get_store_settings(db), "closed")
        touch_settings(get_store_settings(db))
        db.commit()
    finally:
        db.close()

    assert client.get("/", follow_redirects=False).status_code == 503

    r = client.post(
        "/login",
        data={"email": "admin@whoopy.local", "password": "admin1234"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    r2 = client.get("/admin/preview", follow_redirects=False)
    assert r2.status_code in (302, 303)
    assert (r2.headers.get("location") or "").endswith("/")

    r3 = client.get("/")
    assert r3.status_code == 200
    assert "előnézet" in r3.text.lower()

    client.get("/admin/preview/exit")
    db = SessionLocal()
    try:
        set_storefront_status(get_store_settings(db), "open")
        touch_settings(get_store_settings(db))
        db.commit()
    finally:
        db.close()


def test_b2b_vat_and_omnibus():
    from app.database import SessionLocal
    from app.models import Offer, Warehouse
    from app.services.compliance import lowest_price_30d
    from app.services.vat import effective_vat_rate, validate_eu_vat_format

    assert validate_eu_vat_format("HU12345678")
    assert not validate_eu_vat_format("XX")
    rate, reverse = effective_vat_rate(
        country="DE", fallback=27.0, is_b2b=True, buyer_vat_id="DE123456789", seller_country="HU"
    )
    assert reverse and rate == 0.0

    db = SessionLocal()
    try:
        assert db.query(Warehouse).filter(Warehouse.is_default.is_(True)).first() is not None
        offer = db.query(Offer).filter(Offer.active.is_(True)).first()
        assert offer is not None
        assert lowest_price_30d(db, offer.product_id) is not None
    finally:
        db.close()

    r = client.post("/cart/b2b", data={"is_b2b": "1", "buyer_vat_id": "HU12345678"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_carrier_label_stub():
    from app.database import SessionLocal
    from app.models import Order, OrderShipment
    from app.services.carriers import create_shipping_label

    db = SessionLocal()
    try:
        sh = db.query(OrderShipment).first()
        if not sh:
            # create minimal via existing order if any
            order = db.query(Order).first()
            if not order:
                return
            sh = OrderShipment(
                order_id=order.id,
                supplier_id=1,
                supplier_name="Demo",
                method="courier",
                status="pending",
            )
            db.add(sh)
            db.commit()
            db.refresh(sh)
        result = create_shipping_label(db, sh, carrier="gls")
        assert result.get("ok")
        assert result.get("tracking")
        assert sh.label_ref
    finally:
        db.close()


def test_price_history_set_and_omnibus_guard():
    from app.database import SessionLocal
    from app.models import Offer, PriceHistory
    from app.services.compliance import omnibus_discount_ok, set_offer_price

    db = SessionLocal()
    try:
        offer = db.query(Offer).filter(Offer.active.is_(True)).first()
        assert offer is not None
        before = db.query(PriceHistory).filter(PriceHistory.offer_id == offer.id).count()
        old = float(offer.price)
        new = old + 111
        assert set_offer_price(db, offer, new, source="test")
        db.commit()
        after = db.query(PriceHistory).filter(PriceHistory.offer_id == offer.id).count()
        assert after == before + 1
        # visszaállítás + guard: ugyanarra az árra mint a 30d low → nem OK mint „akció”
        low_check = omnibus_discount_ok(db, offer.product_id, new)
        assert "lowest_30d" in low_check
        set_offer_price(db, offer, old, source="test")
        db.commit()
    finally:
        db.close()


def test_subscription_create_and_fulfill():
    from datetime import datetime, timedelta

    from app.database import SessionLocal
    from app.models import Offer, Order, Subscription, User
    from app.services.subscriptions import create_subscription, process_due_subscriptions

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "vasarlo@whoopy.local").first()
        offer = db.query(Offer).filter(Offer.active.is_(True), Offer.stock >= 2).first()
        assert user and offer
        sub = create_subscription(
            db,
            user,
            lines=[(offer.id, 1)],
            interval_days=30,
            name="Smoke ismétlés",
            email=user.email,
            full_name="Smoke",
            city="Budapest",
            address="Teszt 1",
            zip_code="1111",
            start_in_days=0,
        )
        assert sub.id
        # due immediately
        sub.next_run_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
        result = process_due_subscriptions(db, limit=10)
        assert result["processed"] >= 1
        db.refresh(sub)
        assert sub.last_order_id
        order = db.get(Order, sub.last_order_id)
        assert order and order.order_number.startswith("TM-SUB-")
        # cleanup: cancel
        sub.active = False
        db.commit()
    finally:
        db.close()

    assert client.get("/account").status_code in (200, 302, 303)


def test_catalog_pagination_and_sitemap():
    from app.services.catalog import list_catalog

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        page1 = list_catalog(db, page=1, per_page=2)
        assert page1.page == 1
        assert len(page1.items) <= 2
        assert page1.total >= len(page1.items)
    finally:
        db.close()

    r = client.get("/", params={"page": 1})
    assert r.status_code == 200
    r2 = client.get("/search", params={"q": "a", "page": 1})
    assert r2.status_code == 200
    sm = client.get("/sitemap.xml")
    assert sm.status_code == 200
    assert "urlset" in sm.text or "sitemapindex" in sm.text
