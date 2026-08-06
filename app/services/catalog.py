"""Katalógus listázás: pagination + skálázható szűrés (40–80k SKU)."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session, joinedload

from app.models import Category, Offer, Product

DEFAULT_PER_PAGE = 48
ADMIN_PER_PAGE = 50
SITEMAP_CHUNK = 5000
MAX_PER_PAGE = 96


@dataclass
class Page:
    items: list[Any]
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        return max(1, ceil(self.total / self.per_page)) if self.total else 1

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages


def clamp_page(page: int | None, *, default: int = 1) -> int:
    try:
        p = int(page or default)
    except (TypeError, ValueError):
        p = default
    return max(1, p)


def clamp_per_page(per_page: int | None, *, default: int = DEFAULT_PER_PAGE) -> int:
    try:
        n = int(per_page or default)
    except (TypeError, ValueError):
        n = default
    return max(1, min(MAX_PER_PAGE, n))


def paginate(query: Query, *, page: int = 1, per_page: int = DEFAULT_PER_PAGE) -> Page:
    page = clamp_page(page)
    per_page = clamp_per_page(per_page, default=per_page)
    total = query.order_by(None).count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return Page(items=items, page=page, per_page=per_page, total=total)


def pager_query(base_params: dict, page: int) -> str:
    """Query string a lapozó linkekhez (page felülírva)."""
    params = {k: v for k, v in base_params.items() if v not in (None, "", [])}
    params["page"] = page
    return urlencode(params, doseq=True)


def list_brands(db: Session, *, limit: int = 500) -> list[str]:
    rows = (
        db.query(Product.brand)
        .filter(Product.active.is_(True), Product.brand != "")
        .distinct()
        .order_by(Product.brand.asc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows if r[0]]


def _min_offer_subq(db: Session):
    return (
        db.query(Offer.product_id.label("product_id"), func.min(Offer.price).label("min_price"))
        .filter(Offer.active.is_(True), Offer.stock > 0)
        .group_by(Offer.product_id)
        .subquery()
    )


def catalog_query(
    db: Session,
    *,
    q: str = "",
    category_id: int | None = None,
    category_path_prefix: str | None = None,
    brand: str = "",
    in_stock: bool = False,
    sort: str = "newest",
    min_price: float | None = None,
    max_price: float | None = None,
) -> Query:
    """Aktív termékek szűrt/rendezett query-je (még nincs limit)."""
    need_price = in_stock or min_price is not None or max_price is not None or sort in ("price_asc", "price_desc")
    query = db.query(Product).filter(Product.active.is_(True))

    if category_path_prefix:
        query = query.join(Category, Product.category_id == Category.id).filter(
            Category.full_path.startswith(category_path_prefix)
        )
    elif category_id:
        query = query.filter(Product.category_id == category_id)

    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Product.title.ilike(like),
                Product.brand.ilike(like),
                Product.description.ilike(like),
                Product.gtin.ilike(like),
                Product.slug.ilike(like),
            )
        )
    if brand.strip():
        query = query.filter(Product.brand.ilike(brand.strip()))

    min_sub = None
    if need_price:
        min_sub = _min_offer_subq(db)
        query = query.outerjoin(min_sub, Product.id == min_sub.c.product_id)
        if in_stock:
            query = query.filter(min_sub.c.min_price.isnot(None))
        if min_price is not None:
            query = query.filter(min_sub.c.min_price >= float(min_price))
        if max_price is not None:
            query = query.filter(min_sub.c.min_price <= float(max_price))

    if sort == "bestseller":
        query = query.order_by(Product.sold_count.desc(), Product.id.desc())
    elif sort == "title":
        query = query.order_by(Product.title.asc())
    elif sort == "price_asc" and min_sub is not None:
        # SQLite-barát: NULL árak a végére
        query = query.order_by(func.coalesce(min_sub.c.min_price, 1e18).asc(), Product.id.desc())
    elif sort == "price_desc" and min_sub is not None:
        query = query.order_by(func.coalesce(min_sub.c.min_price, -1.0).desc(), Product.id.desc())
    else:
        query = query.order_by(Product.created_at.desc(), Product.id.desc())

    return query.options(
        joinedload(Product.offers).joinedload(Offer.supplier),
        joinedload(Product.category),
    )


def list_catalog(
    db: Session,
    *,
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    **filters,
) -> Page:
    return paginate(catalog_query(db, **filters), page=page, per_page=per_page)
