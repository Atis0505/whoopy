"""Store settings helper (Shopify Settings analogue)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CmsPage, StoreSettings


def get_store_settings(db: Session) -> StoreSettings:
    row = db.query(StoreSettings).order_by(StoreSettings.id).first()
    if row:
        return row
    row = StoreSettings(
        store_name=settings.app_name,
        domain=settings.app_domain,
        support_email="info@whoopy.hu",
        default_currency=settings.currency,
        default_country=settings.default_country,
        erp_enabled=settings.erp_enabled,
        erp_api_base=settings.erp_api_base,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_default_cms_pages(db: Session) -> None:
    defaults = [
        (
            "aszf",
            "Általános szerződési feltételek",
            "<p>Ez egy minta ÁSZF oldal a Whoopy demóhoz. Cseréld le a saját jogi szövegedre.</p>",
        ),
        (
            "adatvedelem",
            "Adatvédelmi tájékoztató",
            "<p>Minta adatvédelmi oldal. A vásárlói adatok kezeléséről itt tájékoztathatod az ügyfeleket.</p>",
        ),
        (
            "rolunk",
            "Rólunk",
            "<p><strong>Whoopy.hu</strong> – többbeszállítós marketplace demó Google Taxonomy alapokon.</p>",
        ),
    ]
    for slug, title, body in defaults:
        if db.query(CmsPage).filter(CmsPage.slug == slug).first():
            continue
        db.add(CmsPage(slug=slug, title=title, body=body, published=True))
    db.commit()


def touch_settings(row: StoreSettings) -> None:
    row.updated_at = datetime.utcnow()
