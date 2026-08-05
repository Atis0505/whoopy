"""Google Merchant Center feed builder + validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Product, ProductImage
from app.services.pricing import promo_discount_for_product
from app.services.store_settings import get_store_settings


@dataclass
class FeedIssue:
    slug: str
    severity: str  # error | warning
    message: str


@dataclass
class FeedReport:
    total_products: int = 0
    included: int = 0
    skipped: int = 0
    errors: list[FeedIssue] = field(default_factory=list)
    warnings: list[FeedIssue] = field(default_factory=list)

    @property
    def ok_for_gmc(self) -> bool:
        return self.included > 0 and len(self.errors) == 0


def _abs_url(base: str, url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{base}{url}"
    return f"{base}/{url}"


def validate_and_collect(db: Session) -> tuple[list[dict], FeedReport]:
    """Build normalized item dicts + validation report."""
    base = settings.public_base_url.rstrip("/")
    store = get_store_settings(db)
    report = FeedReport()
    items: list[dict] = []

    products = (
        db.query(Product)
        .options(
            joinedload(Product.offers),
            joinedload(Product.category),
            joinedload(Product.images),
        )
        .filter(Product.active.is_(True))
        .all()
    )
    report.total_products = len(products)

    for p in products:
        active = [o for o in p.offers if o.active and o.stock > 0]
        if not active:
            report.skipped += 1
            report.warnings.append(FeedIssue(p.slug, "warning", "Nincs aktív készletes ajánlat"))
            continue

        issues: list[FeedIssue] = []
        if not p.category:
            issues.append(FeedIssue(p.slug, "error", "Hiányzik a Google taxonomy kategória"))
        if not (p.image_url or (p.images and any(True for _ in p.images))):
            issues.append(FeedIssue(p.slug, "warning", "Nincs termék kép (placeholder megy a feedbe)"))
        if not p.gtin and not p.brand:
            issues.append(FeedIssue(p.slug, "warning", "Nincs GTIN és márka — identifier_exists=no"))
        if not p.title or len(p.title.strip()) < 3:
            issues.append(FeedIssue(p.slug, "error", "Cím túl rövid / üres"))
        if p.weight_kg <= 0:
            issues.append(FeedIssue(p.slug, "warning", "Súly ≤ 0"))

        for iss in issues:
            if iss.severity == "error":
                report.errors.append(iss)
            else:
                report.warnings.append(iss)

        if any(i.severity == "error" for i in issues):
            report.skipped += 1
            continue

        best = min(active, key=lambda o: o.price)
        unit, promo = promo_discount_for_product(db, p, best.price)
        google_cat_id = str(p.category.google_id) if p.category else ""
        google_cat_path = p.category.full_path if p.category else ""
        link = f"{base}/p/{p.slug}"
        primary_img = p.image_url
        if not primary_img and p.images:
            primary = next((i for i in p.images if i.is_primary), p.images[0])
            primary_img = _abs_url(base, primary.url)
        image = _abs_url(base, primary_img) if primary_img else f"{base}/static/whoopy-og.png"
        extra_imgs = []
        for img in (p.images or [])[:10]:
            u = _abs_url(base, img.url)
            if u and u != image:
                extra_imgs.append(u)

        desc = (p.description or p.title).strip()
        item = {
            "id": p.slug,
            "title": p.title,
            "description": desc[:5000],
            "link": link,
            "image_link": image,
            "additional_image_link": extra_imgs,
            "availability": "in_stock",
            "price": f"{best.price:.2f} HUF",
            "sale_price": f"{unit:.2f} HUF" if unit < best.price - 0.01 else None,
            "brand": p.brand or store.store_name or "Whoopy",
            "condition": "new",
            "google_product_category": google_cat_id,
            "product_type": google_cat_path,
            "gtin": p.gtin or "",
            "shipping_weight": f"{p.weight_kg} kg",
            "identifier_exists": "yes" if p.gtin else "no",
            "item_group_id": p.slug,
            "mpn": (active[0].sku if active and active[0].sku else "") or "",
        }
        items.append(item)
        report.included += 1

    return items, report


def build_google_merchant_xml(db: Session) -> str:
    store = get_store_settings(db)
    if not store.google_feed_enabled:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<rss version=\"2.0\" xmlns:g=\"http://base.google.com/ns/1.0\">"
            "<channel><title>Whoopy feed disabled</title>"
            "<description>google_feed_enabled=false</description></channel></rss>"
        )

    base = settings.public_base_url.rstrip("/")
    items, _report = validate_and_collect(db)
    blocks: list[str] = []
    for it in items:
        extra = "".join(
            f"\n      <g:additional_image_link>{escape(u)}</g:additional_image_link>"
            for u in it["additional_image_link"]
        )
        sale = ""
        if it.get("sale_price"):
            sale = f"\n      <g:sale_price>{escape(it['sale_price'])}</g:sale_price>"
        gtin = f"\n      <g:gtin>{escape(it['gtin'])}</g:gtin>" if it["gtin"] else ""
        mpn = f"\n      <g:mpn>{escape(it['mpn'])}</g:mpn>" if it["mpn"] else ""
        blocks.append(
            f"""
    <item>
      <g:id>{escape(it['id'])}</g:id>
      <g:title>{escape(it['title'])}</g:title>
      <g:description>{escape(it['description'])}</g:description>
      <g:link>{escape(it['link'])}</g:link>
      <g:image_link>{escape(it['image_link'])}</g:image_link>{extra}
      <g:availability>{it['availability']}</g:availability>
      <g:price>{escape(it['price'])}</g:price>{sale}
      <g:brand>{escape(it['brand'])}</g:brand>
      <g:condition>{it['condition']}</g:condition>
      <g:google_product_category>{escape(it['google_product_category'])}</g:google_product_category>
      <g:product_type>{escape(it['product_type'])}</g:product_type>{gtin}{mpn}
      <g:shipping_weight>{escape(it['shipping_weight'])}</g:shipping_weight>
      <g:identifier_exists>{it['identifier_exists']}</g:identifier_exists>
      <g:adult>no</g:adult>
    </item>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>{escape(store.store_name)} – {escape(store.domain)}</title>
    <link>{escape(base)}</link>
    <description>Whoopy.hu Google Merchant Center product feed</description>
    {''.join(blocks)}
  </channel>
</rss>
"""
