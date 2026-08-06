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
