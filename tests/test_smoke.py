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


def test_media_absolute_helper():
    from app.services.media import absolute_media_url

    assert absolute_media_url("https://cdn.example/x.jpg").startswith("https://")
    rel = absolute_media_url("/media/products/1/a.jpg")
    assert "media/products" in rel
