"""Google Merchant Center product feed (RSS 2.0 / g: namespace).

Products must carry Google Product Taxonomy paths (our Category.full_path)
so Google Shopping can classify and recommend them.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Offer, Product
from app.services.pricing import promo_discount_for_product


def build_google_merchant_xml(db: Session) -> str:
    base = settings.public_base_url.rstrip("/")
    products = (
        db.query(Product)
        .options(joinedload(Product.offers), joinedload(Product.category))
        .filter(Product.active.is_(True))
        .all()
    )

    items: list[str] = []
    for p in products:
        active = [o for o in p.offers if o.active and o.stock > 0]
        if not active:
            continue
        best = min(active, key=lambda o: o.price)
        unit, _ = promo_discount_for_product(db, p, best.price)
        availability = "in_stock"
        google_cat = p.category.full_path if p.category else ""
        link = f"{base}/p/{p.slug}"
        image = p.image_url or f"{base}/static/whoopy-og.png"
        desc = (p.description or p.title).strip()
        items.append(
            f"""
    <item>
      <g:id>{escape(p.slug)}</g:id>
      <g:title>{escape(p.title)}</g:title>
      <g:description>{escape(desc[:5000])}</g:description>
      <g:link>{escape(link)}</g:link>
      <g:image_link>{escape(image)}</g:image_link>
      <g:availability>{availability}</g:availability>
      <g:price>{unit:.2f} HUF</g:price>
      <g:brand>{escape(p.brand or 'Whoopy')}</g:brand>
      <g:condition>new</g:condition>
      <g:google_product_category>{escape(google_cat)}</g:google_product_category>
      <g:product_type>{escape(google_cat)}</g:product_type>
      <g:gtin>{escape(p.gtin)}</g:gtin>
      <g:shipping_weight>{p.weight_kg} kg</g:shipping_weight>
      <g:identifier_exists>{'yes' if p.gtin else 'no'}</g:identifier_exists>
    </item>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>Whoopy – {settings.app_domain}</title>
    <link>{escape(base)}</link>
    <description>Whoopy.hu product feed for Google Merchant Center</description>
    {''.join(items)}
  </channel>
</rss>
"""
