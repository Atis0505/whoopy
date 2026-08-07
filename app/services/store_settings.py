"""Store settings helper (Shopify Settings analogue)."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.content.legal_pages import LEGAL_CONTENT_VERSION, default_legal_pages
from app.models import CmsPage, StoreSettings

_LEGAL_MARKER_RE = re.compile(r"<!--\s*whoopy-legal:v(\d+)\s*-->")


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


def _body_version(body: str) -> int | None:
    m = _LEGAL_MARKER_RE.search(body or "")
    return int(m.group(1)) if m else None


def _should_refresh_legal(body: str) -> bool:
    """Frissítjük a seed/jogi sablont, ha nincs marker, régi verzió, vagy rövid placeholder."""
    ver = _body_version(body)
    if ver is None:
        return True
    if ver < LEGAL_CONTENT_VERSION:
        return True
    return False


def ensure_default_cms_pages(db: Session, *, force: bool = False) -> int:
    """Létrehozza / frissíti a jogi CMS oldalakat. Vissza: frissített/létrehozott darabszám.

    Ha az admin eltávolítja a ``<!-- whoopy-legal:vN -->`` markert ÉS force=False,
    a tartalom megmarad (egyéni szerkesztés). Marker nélküli régi seed placeholder-eket
    viszont felülírjuk.
    """
    updated = 0
    for slug, title, body in default_legal_pages():
        marked = f"<!-- whoopy-legal:v{LEGAL_CONTENT_VERSION} -->\n{body.strip()}\n"
        row = db.query(CmsPage).filter(CmsPage.slug == slug).first()
        if row is None:
            db.add(CmsPage(slug=slug, title=title, body=marked, published=True))
            updated += 1
            continue
        if force or _should_refresh_legal(row.body or ""):
            # Marker nélküli, de hosszú (valószínűleg kézzel írt) tartalom: ne írjuk felül
            if (
                not force
                and _body_version(row.body or "") is None
                and len((row.body or "").strip()) > 400
                and "minta" not in (row.body or "").lower()
                and "cseréld" not in (row.body or "").lower()
            ):
                continue
            row.title = title
            row.body = marked
            row.published = True
            row.updated_at = datetime.utcnow()
            updated += 1
    if updated:
        db.commit()
    return updated


def render_cms_placeholders(body: str, store: StoreSettings) -> str:
    """{{company_name}} stb. behelyettesítése a CMS HTML-be."""
    mapping = {
        "store_name": store.store_name or settings.app_name,
        "company_name": store.company_name or "Whoopy Kft.",
        "company_address": store.company_address or "— (add meg a Beállításokban)",
        "company_tax_id": store.company_tax_id or "—",
        "company_eu_vat": store.company_eu_vat or "—",
        "support_email": store.support_email or "info@whoopy.hu",
        "support_phone": store.support_phone or "—",
        "business_hours": store.business_hours or "H–P 9:00–17:00",
        "domain": store.domain or settings.app_domain,
    }
    out = body or ""
    for key, val in mapping.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def touch_settings(row: StoreSettings) -> None:
    row.updated_at = datetime.utcnow()
