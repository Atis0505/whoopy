"""Marketing feedek: Meta/Facebook katalógus + Árukereső XML."""

from __future__ import annotations

from xml.sax.saxutils import escape

from sqlalchemy.orm import Session

from app.config import settings
from app.services.google_feed import validate_and_collect
from app.services.store_settings import get_store_settings


def build_meta_catalog_xml(db: Session) -> str:
    """Meta (Facebook/Instagram) Commerce — Google-kompatibilis RSS."""
    store = get_store_settings(db)
    base = settings.public_base_url.rstrip("/")
    items, _ = validate_and_collect(db)
    blocks: list[str] = []
    for it in items:
        sale = ""
        if it.get("sale_price"):
            sale = f"\n      <g:sale_price>{escape(it['sale_price'])}</g:sale_price>"
        gtin = f"\n      <g:gtin>{escape(it['gtin'])}</g:gtin>" if it["gtin"] else ""
        blocks.append(
            f"""
    <item>
      <g:id>{escape(it['id'])}</g:id>
      <g:title>{escape(it['title'])}</g:title>
      <g:description>{escape(it['description'])}</g:description>
      <g:link>{escape(it['link'])}</g:link>
      <g:image_link>{escape(it['image_link'])}</g:image_link>
      <g:availability>{it['availability']}</g:availability>
      <g:condition>{it['condition']}</g:condition>
      <g:price>{escape(it['price'])}</g:price>{sale}
      <g:brand>{escape(it['brand'])}</g:brand>{gtin}
      <g:google_product_category>{escape(it['google_product_category'])}</g:google_product_category>
    </item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>{escape(store.store_name)} Meta Catalog</title>
    <link>{escape(base)}</link>
    <description>Whoopy Facebook / Instagram Shop feed</description>
    {''.join(blocks)}
  </channel>
</rss>
"""


def build_arukereso_xml(db: Session) -> str:
    """Árukereső.hu termékfeed (egyszerűsített XML)."""
    store = get_store_settings(db)
    items, _ = validate_and_collect(db)
    blocks: list[str] = []
    for it in items:
        # price "1234.00 HUF" → nettó-ish szám Árukeresőnek (bruttó HUF)
        price_raw = (it.get("sale_price") or it.get("price") or "0").split()[0]
        try:
            price_num = f"{float(price_raw):.0f}"
        except ValueError:
            price_num = "0"
        cat = it.get("product_type") or "Egyéb"
        blocks.append(
            f"""
  <product>
    <identifier>{escape(it['id'])}</identifier>
    <manufacturer>{escape(it['brand'])}</manufacturer>
    <name>{escape(it['title'])}</name>
    <product_url>{escape(it['link'])}</product_url>
    <price>{escape(price_num)}</price>
    <net_price>{escape(price_num)}</net_price>
    <image_url>{escape(it['image_link'])}</image_url>
    <category>{escape(cat)}</category>
    <description>{escape(it['description'][:2000])}</description>
    <delivery_time>2</delivery_time>
    <delivery_cost>990</delivery_cost>
  </product>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<products shop_name="{escape(store.store_name)}" shop_url="{escape(settings.public_base_url.rstrip('/'))}">
{''.join(blocks)}
</products>
"""
